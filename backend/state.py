"""
GenomeGuide Shared State Schema
TypedDict that flows through the entire LangGraph pipeline.
Each agent reads upstream fields and appends its own output.
Nothing downstream can be computed without upstream evidence being present.
"""
from typing import TypedDict, Optional


class ParsedVariant(TypedDict):
    gene: str
    hgvs_c: str
    hgvs_p: Optional[str]
    variant_type: str  # deletion | substitution | duplication | frameshift | nonsense | indel


class ClinVarResult(TypedDict):
    found: bool
    variation_id: Optional[str]
    classification: Optional[str]   # Pathogenic | Likely pathogenic | VUS | Likely benign | Benign
    review_status: Optional[str]    # e.g. "criteria provided, multiple submitters, no conflicts"
    star_rating: int                # 0-4
    submitters: int
    conflicting: bool


class GnomADResult(TypedDict):
    found: bool
    allele_frequency: Optional[float]
    allele_count: Optional[int]
    allele_number: Optional[int]
    dataset: str                    # gnomad_r4


class ACMGEvidence(TypedDict):
    triggered_criteria: list        # e.g. ["PVS1", "PM2"]
    criteria_details: dict          # criterion -> reason string
    classification: str             # Pathogenic | Likely Pathogenic | VUS | Likely Benign | Benign
    confidence: str                 # High | Moderate | Low


class CriticVerdict(TypedDict):
    passed: bool
    unsupported_claims: list        # list of claim strings rejected
    retry_count: int


class GenomeGuideState(TypedDict):
    # Input
    raw_variant_input: str

    # Agent 1 output
    parsed: Optional[ParsedVariant]
    parse_error: Optional[str]

    # Agent 2 output (Database + Literature RAG)
    clinvar_result: Optional[ClinVarResult]
    gnomad_result: Optional[GnomADResult]
    literature_evidence: Optional[list]  # list of PubMed papers [{pmid, title, journal, authors, url}]

    # Agent 3 output (deterministic — no LLM)
    acmg_evidence: Optional[ACMGEvidence]

    # Agent 4 output
    draft_explanation: Optional[str]
    explainer_retry_count: int

    # Agent 5 output
    critic_verdict: Optional[CriticVerdict]

    # Execution telemetry & traces
    traces: Optional[list]  # [{stage, agent, duration_ms, status, details}]

    # Final
    final_output: Optional[str]
    pipeline_error: Optional[str]

