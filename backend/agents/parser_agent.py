"""
Agent 1 — Variant Parser Agent
Uses Groq LLaMA 3.1 70B to parse raw HGVS notation into structured fields.
Falls back to a robust regex parser when the LLM fails.
The hgvs library is used in parse-only mode (no UTA database required).
"""
import os
import re
import json
import logging
from typing import Optional
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
from state import GenomeGuideState, ParsedVariant

logger = logging.getLogger(__name__)

# Genes with well-established loss-of-function disease mechanism
# Used by the ACMG PVS1 criterion in the classifier
LOF_GENES = {
    "BRCA1", "BRCA2", "MLH1", "MSH2", "MSH6", "PMS2",
    "CFTR", "APC", "TP53", "PTEN", "RB1", "NF1", "NF2",
    "VHL", "STK11", "CDH1", "PALB2", "ATM", "CHEK2",
    "RAD51C", "RAD51D", "BRIP1"
}

SUPPORTED_GENES = {"BRCA1", "BRCA2", "CFTR", "MLH1", "MSH2", "MSH6", "PMS2", "TP53", "PALB2", "ATM", "CHEK2"}

SYSTEM_PROMPT = """You are a clinical bioinformatics expert specialising in HGVS nomenclature.
Extract structured fields from the raw variant input and return ONLY valid JSON.

Return exactly this JSON structure:
{
  "gene": "<gene symbol>",
  "hgvs_c": "<coding sequence notation, e.g. c.68_69delAG>",
  "hgvs_p": "<protein notation if present, else null>",
  "variant_type": "<one of: deletion | insertion | duplication | substitution | frameshift | nonsense | indel | splice>"
}

Rules:
- gene must be the HGNC official symbol (uppercase)
- hgvs_c must start with "c."
- variant_type classification:
  * frameshift: any deletion/insertion that shifts reading frame (indel not divisible by 3)
  * nonsense: substitution creating a stop codon (p.*Ter or p.Trp*)
  * deletion: in-frame deletion or simple del notation
  * insertion: ins notation
  * duplication: dup notation
  * substitution: single nucleotide change (SNV)
  * indel: combined del+ins
  * splice: affects splice site (within 2bp of exon boundary)
- If input already has protein notation (p.), include it verbatim
- Return ONLY the JSON object, no markdown, no explanation."""


def regex_parse_hgvs(raw: str) -> Optional[ParsedVariant]:
    """
    Robust regex-based HGVS parser as fallback.
    Handles the most common notation patterns seen in clinical reports.
    """
    # Normalise whitespace
    raw = raw.strip()

    # Gene:c. notation e.g. BRCA1:c.68_69delAG or BRCA1 c.68_69delAG
    gene_match = re.search(r'\b([A-Z][A-Z0-9]+)\s*[:\s]\s*(c\.[^\s,]+)', raw, re.IGNORECASE)
    if not gene_match:
        # Try NM_ format: NM_007294.4(BRCA1):c.68_69delAG
        gene_match = re.search(r'NM_\d+\.\d+\s*\(([A-Z][A-Z0-9]+)\)\s*:\s*(c\.[^\s,]+)', raw, re.IGNORECASE)

    if not gene_match:
        return None

    gene = gene_match.group(1).upper()
    hgvs_c = gene_match.group(2)

    # Protein notation
    p_match = re.search(r'(p\.\(?[A-Za-z]+\d+[A-Za-z*]+\)?)', raw)
    hgvs_p = p_match.group(1) if p_match else None

    # Determine variant type from hgvs_c
    variant_type = _classify_variant_type(hgvs_c, hgvs_p)

    return ParsedVariant(
        gene=gene,
        hgvs_c=hgvs_c,
        hgvs_p=hgvs_p,
        variant_type=variant_type
    )


def _classify_variant_type(hgvs_c: str, hgvs_p: Optional[str]) -> str:
    """Classify variant type from HGVS notation."""
    c = hgvs_c.lower()

    # Check for splice site pattern first
    if re.search(r'[+-]\d+[actg]', c) or re.search(r'\d+[+-]\d+', c):
        return "splice"

    if "delins" in c or "del" in c and "ins" in c:
        m = re.search(r'(\d+)_(\d+)delins([a-z]+)', c)
        if m:
            del_len = int(m.group(2)) - int(m.group(1)) + 1
            ins_len = len(m.group(3))
            if abs(ins_len - del_len) % 3 != 0:
                return "frameshift"
        return "indel"

    if "dup" in c:
        m = re.search(r'(\d+)_(\d+)dup', c)
        if m:
            length = int(m.group(2)) - int(m.group(1)) + 1
            if length % 3 != 0:
                return "frameshift"
        if re.search(r'c\.\d+dup', c):
            return "frameshift"
        m_seq = re.search(r'dup([a-z]+)', c)
        if m_seq and len(m_seq.group(1)) % 3 != 0:
            return "frameshift"
        return "duplication"

    if "ins" in c and "del" not in c:
        m = re.search(r'ins([a-z]+)', c)
        if m and len(m.group(1)) % 3 != 0:
            return "frameshift"
        return "insertion"

    if "del" in c:
        # Check if likely frameshift (deletion of non-multiple-of-3 bases)
        m = re.search(r'(\d+)_(\d+)del', c)
        if m:
            length = int(m.group(2)) - int(m.group(1)) + 1
            if length % 3 != 0:
                return "frameshift"
        # Single base deletion is also frameshift
        if re.search(r'c\.\d+del[acgt]?$', c):
            return "frameshift"
        return "deletion"

    if re.search(r'[actg]>[actg]', c) or re.search(r'\d+[actg]>[actg]', c):
        # Nonsense check from protein notation
        if hgvs_p and ("ter" in hgvs_p.lower() or "*" in hgvs_p):
            return "nonsense"
        return "substitution"

    return "substitution"  # default


def parser_node(state: GenomeGuideState) -> dict:
    """
    LangGraph node: parse raw variant input into structured fields.
    Tries Groq LLaMA first; falls back to regex parser.
    """
    raw = state["raw_variant_input"]
    logger.info(f"[Parser] Processing: {raw!r}")

    # --- Try LLM parser first ---
    try:
        groq_api_key = os.getenv("GROQ_API_KEY")
        if not groq_api_key:
            raise ValueError("GROQ_API_KEY not set")

        groq_model = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
        llm = ChatGroq(
            model=groq_model,
            temperature=0,
            max_tokens=300,
            api_key=groq_api_key,
        )

        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=f"Parse this variant: {raw}")
        ]
        response = llm.invoke(messages)
        content = response.content.strip()

        # Robust JSON extraction
        json_match = re.search(r"(\{[\s\S]*\})", content)
        if json_match:
            parsed_data = json.loads(json_match.group(1))
        else:
            parsed_data = json.loads(content)
        parsed = ParsedVariant(
            gene=parsed_data["gene"].upper(),
            hgvs_c=parsed_data["hgvs_c"],
            hgvs_p=parsed_data.get("hgvs_p"),
            variant_type=parsed_data["variant_type"]
        )
        logger.info(f"[Parser] LLM parsed: {parsed}")
        return {"parsed": parsed, "parse_error": None}

    except Exception as e:
        logger.warning(f"[Parser] LLM failed ({e}), falling back to regex")

    # --- Regex fallback ---
    parsed = regex_parse_hgvs(raw)
    if parsed:
        logger.info(f"[Parser] Regex parsed: {parsed}")
        return {"parsed": parsed, "parse_error": None}

    # --- Both failed ---
    error_msg = (
        f"Could not parse variant notation: {raw!r}. "
        "Please use HGVS format, e.g. 'BRCA1 c.68_69delAG' or 'CFTR c.1521_1523delCTT'."
    )
    logger.error(f"[Parser] {error_msg}")
    return {"parsed": None, "parse_error": error_msg}
