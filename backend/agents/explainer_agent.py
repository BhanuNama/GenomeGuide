"""
Agent 4 — Explainer Agent
Uses Groq LLaMA 3.1 70B to write a plain-English patient summary.
The LLM is strictly constrained to summarise an ALREADY-MADE classification —
it cannot change the classification or introduce unsupported facts.
"""
import os
import logging
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
from state import GenomeGuideState

logger = logging.getLogger(__name__)

DISCLAIMER = (
    "\n\n---\n"
    "⚠️ **Important Medical Disclaimer**: This report is an educational tool and is "
    "NOT a substitute for professional genetic counselling. The classification above "
    "is based on a simplified 5-criterion subset of the ACMG/AMP framework — not the full "
    "28-criterion clinical-grade evaluation. Please discuss these results with a certified "
    "genetic counsellor or your physician before making any medical decisions."
)

SYSTEM_PROMPT = """You are a compassionate genetic counsellor writing a plain-English summary for a patient.
Your job is ONLY to explain the provided classification and evidence — you must NOT introduce any facts, 
statistics, percentages, or risk estimates that are not explicitly present in the evidence fields given to you.

Guidelines:
- Write in clear, warm, patient-friendly language (avoid jargon — if you use a term, immediately define it)
- Structure: (1) What this variant is, (2) What the classification means, (3) What the evidence shows, (4) Next steps
- For VUS: be explicit that "Uncertain Significance does NOT mean confirmed risk — it means there is not yet enough evidence to classify this variant"
- For Pathogenic/Likely Pathogenic: acknowledge the finding honestly but calmly; recommend specialist follow-up
- For Benign/Likely Benign: provide reassurance
- Length: 250-350 words
- Do NOT invent risk percentages, penetrance figures, or statistics unless they appear in the evidence
- Do NOT change or soften the classification — state it exactly as given"""


def _build_evidence_prompt(state: GenomeGuideState) -> str:
    parsed   = state["parsed"]
    clinvar  = state["clinvar_result"]
    gnomad   = state["gnomad_result"]
    acmg     = state["acmg_evidence"]
    retry    = state.get("explainer_retry_count", 0)
    rejected = state.get("critic_verdict", {})

    lines = [
        f"VARIANT: {state['raw_variant_input']}",
        f"GENE: {parsed['gene']}",
        f"NOTATION: {parsed['hgvs_c']}" + (f" / {parsed['hgvs_p']}" if parsed.get('hgvs_p') else ""),
        f"VARIANT TYPE: {parsed['variant_type']}",
        "",
        "=== CLASSIFICATION (AUTHORITATIVE — DO NOT CHANGE) ===",
        f"Classification: {acmg['classification']}",
        f"Confidence: {acmg['confidence']}",
        f"ACMG Criteria triggered: {', '.join(acmg['triggered_criteria']) or 'None'}",
        "",
        "=== ACMG CRITERIA DETAILS ===",
    ]
    for crit, detail in acmg.get("criteria_details", {}).items():
        lines.append(f"  {crit}: {detail}")

    lines.append("")
    lines.append("=== CLINVAR EVIDENCE ===")
    if clinvar and clinvar.get("found"):
        lines.append(f"  ClinVar found: YES")
        lines.append(f"  Classification: {clinvar.get('classification', 'N/A')}")
        lines.append(f"  Review status: {clinvar.get('review_status', 'N/A')} ({clinvar.get('star_rating', 0)}★)")
        lines.append(f"  Submitters: {clinvar.get('submitters', 0)}")
        lines.append(f"  Conflicting submissions: {clinvar.get('conflicting', False)}")
    else:
        lines.append("  ClinVar found: NO — this variant has not been previously submitted to ClinVar")

    lines.append("")
    lines.append("=== GNOMAD POPULATION FREQUENCY ===")
    if gnomad and gnomad.get("found"):
        af = gnomad.get("allele_frequency", 0)
        lines.append(f"  Found in gnomAD: YES")
        lines.append(f"  Allele frequency: {af:.6f} ({af*100:.4f}%)")
        lines.append(f"  Allele count: {gnomad.get('allele_count', 'N/A')} / {gnomad.get('allele_number', 'N/A')}")
    else:
        lines.append("  Found in gnomAD: NO — absent from 125,748+ individuals")

    literature = state.get("literature_evidence") or []
    if literature:
        lines.append("")
        lines.append("=== PEER-REVIEWED SCIENTIFIC LITERATURE (PUBMED) ===")
        for art in literature[:3]:
            lines.append(f"  - PMID {art['pmid']}: \"{art['title']}\" ({art['journal']}, {art.get('pubdate', '')})")
        lines.append("  Guidance: You may mention that published studies exist for this variant and cite them with [PMID: ...].")

    if retry > 0 and rejected:
        lines.append("")
        lines.append("=== CRITIC FEEDBACK (previous draft rejected) ===")
        for claim in rejected.get("unsupported_claims", []):
            lines.append(f"  REJECTED CLAIM: {claim}")
        lines.append("  → Remove ALL rejected claims from your new draft. Do not include any claim not in the evidence above.")


    return "\n".join(lines)


def explainer_node(state: GenomeGuideState) -> dict:
    """LangGraph node: generate plain-English explanation via Groq LLaMA."""
    if state.get("parse_error") or not state.get("acmg_evidence"):
        return {"draft_explanation": None}

    evidence_prompt = _build_evidence_prompt(state)
    retry_count = state.get("explainer_retry_count", 0)

    logger.info(f"[Explainer] Generating explanation (attempt {retry_count + 1})")

    try:
        groq_api_key = os.getenv("GROQ_API_KEY")
        if not groq_api_key:
            raise ValueError("GROQ_API_KEY not set")

        groq_model = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
        llm = ChatGroq(
            model=groq_model,
            temperature=0.3,
            max_tokens=600,
            api_key=groq_api_key,
        )

        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=f"Write the patient summary for this variant:\n\n{evidence_prompt}")
        ]
        response = llm.invoke(messages)
        draft = response.content.strip() + DISCLAIMER

        logger.info(f"[Explainer] Draft generated ({len(draft)} chars)")
        return {
            "draft_explanation": draft,
            "explainer_retry_count": retry_count + 1,
        }

    except Exception as e:
        logger.error(f"[Explainer] LLM error: {e}")
        # Structured fallback explanation
        acmg = state["acmg_evidence"]
        fallback = _build_fallback_explanation(state, acmg) + DISCLAIMER
        return {
            "draft_explanation": fallback,
            "explainer_retry_count": retry_count + 1,
        }


def _build_fallback_explanation(state: GenomeGuideState, acmg: dict) -> str:
    """Rule-based fallback explanation if LLM is unavailable."""
    parsed  = state["parsed"]
    clinvar = state.get("clinvar_result", {})
    gnomad  = state.get("gnomad_result", {})

    classification = acmg["classification"]
    gene = parsed["gene"]
    hgvs_c = parsed["hgvs_c"]
    criteria = ", ".join(acmg["triggered_criteria"]) or "none"

    af_text = "absent from gnomAD population databases"
    if gnomad and gnomad.get("found"):
        af = gnomad.get("allele_frequency", 0)
        af_text = f"present at {af*100:.4f}% frequency in gnomAD"

    cv_text = "not found in ClinVar"
    if clinvar and clinvar.get("found"):
        cv_text = f"classified as {clinvar.get('classification')} in ClinVar ({clinvar.get('star_rating', 0)}★ review status)"

    return (
        f"## Variant Report: {gene} {hgvs_c}\n\n"
        f"**Classification: {classification}**\n\n"
        f"Your genetic test identified the variant {gene} {hgvs_c}. "
        f"Using a simplified 5-criterion ACMG/AMP scoring framework, this variant has been "
        f"classified as **{classification}**.\n\n"
        f"**Evidence Summary:**\n"
        f"- ACMG criteria triggered: {criteria}\n"
        f"- Population frequency: {af_text}\n"
        f"- Database status: {cv_text}\n\n"
        f"Please discuss this result with a qualified genetic counsellor."
    )
