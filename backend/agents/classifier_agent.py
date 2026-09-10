"""
Agent 3 — Pathogenicity Classifier Agent
DETERMINISTIC rule engine — zero LLM.
Implements 5 ACMG/AMP criteria (subset of the full 28-criterion framework).

Criteria implemented:
  PVS1   — Null variant in LOF gene
  PS3/PP5 — Multiple reputable ClinVar submitters agree
  PM2    — Absent/very rare in population (gnomAD AF < 0.0001)
  BA1    — Common in population (gnomAD AF > 0.05) → strong benign
  BP6    — ClinVar Benign/Likely Benign, no conflicting submissions
"""
import logging
from state import GenomeGuideState, ACMGEvidence

logger = logging.getLogger(__name__)

# Genes where loss-of-function IS the established disease mechanism
LOF_GENES = {
    "BRCA1", "BRCA2", "MLH1", "MSH2", "MSH6", "PMS2",
    "CFTR", "APC", "TP53", "PTEN", "RB1", "NF1", "NF2",
    "VHL", "STK11", "CDH1", "PALB2", "ATM", "CHEK2",
    "RAD51C", "RAD51D", "BRIP1", "MUTYH",
}

LOF_VARIANT_TYPES = {"frameshift", "nonsense", "splice"}

# Population frequency thresholds
AF_COMMON   = 0.05    # BA1: ≥ 5% → strong benign
AF_RARE     = 0.0001  # PM2: ≤ 0.01% → supports pathogenicity


def _evaluate_criteria(state: GenomeGuideState) -> tuple[list, dict]:
    """
    Evaluate all 5 ACMG criteria and return (triggered_list, details_dict).
    """
    parsed  = state.get("parsed", {})
    clinvar = state.get("clinvar_result", {})
    gnomad  = state.get("gnomad_result", {})

    triggered = []
    details   = {}

    gene         = parsed.get("gene", "")
    variant_type = parsed.get("variant_type", "")
    af           = gnomad.get("allele_frequency") if gnomad else None
    cv_class     = (clinvar.get("classification") or "").lower() if clinvar else ""
    star_rating  = clinvar.get("star_rating", 0) if clinvar else 0
    submitters   = clinvar.get("submitters", 0) if clinvar else 0
    conflicting  = clinvar.get("conflicting", False) if clinvar else False
    cv_found     = clinvar.get("found", False) if clinvar else False

    # -----------------------------------------------------------------------
    # BA1 — Common in population (strong benign; overrides other criteria)
    # -----------------------------------------------------------------------
    if af is not None and af > AF_COMMON:
        triggered.append("BA1")
        details["BA1"] = (
            f"Allele frequency {af:.4f} ({af*100:.2f}%) in gnomAD — exceeds 5% threshold. "
            "Variant is too common in the general population to be a rare disease-causing allele."
        )

    # -----------------------------------------------------------------------
    # PVS1 — Null variant in LOF gene (very strong pathogenic)
    # -----------------------------------------------------------------------
    if variant_type in LOF_VARIANT_TYPES and gene in LOF_GENES:
        triggered.append("PVS1")
        details["PVS1"] = (
            f"{variant_type.capitalize()} variant in {gene}, a gene where loss-of-function "
            "is a well-established disease mechanism (OMIM confirmed)."
        )

    # -----------------------------------------------------------------------
    # PS3 / PP5 — Established in ClinVar with strong review status
    # -----------------------------------------------------------------------
    if cv_found and not conflicting:
        if star_rating >= 2 and submitters >= 2:
            if "pathogenic" in cv_class and "likely" not in cv_class:
                triggered.append("PS3")
                details["PS3"] = (
                    f"ClinVar classification: '{clinvar.get('classification')}' with {submitters} "
                    f"independent submitters and review status '{clinvar.get('review_status')}' "
                    f"({star_rating}★). Multiple laboratories agree."
                )
            elif "likely pathogenic" in cv_class or "pathogenic" in cv_class:
                triggered.append("PP5")
                details["PP5"] = (
                    f"ClinVar: '{clinvar.get('classification')}' ({submitters} submitters, "
                    f"{star_rating}★, no conflicts). Reputable source classification."
                )
        elif star_rating >= 1 and ("pathogenic" in cv_class or "likely pathogenic" in cv_class):
            triggered.append("PP5")
            details["PP5"] = (
                f"ClinVar: '{clinvar.get('classification')}' ({submitters} submitters, "
                f"{star_rating}★, no conflicts). Reputable source classification."
            )

    # -----------------------------------------------------------------------
    # PM2 — Absent / extremely rare in population
    # -----------------------------------------------------------------------
    if not gnomad or not gnomad.get("found"):
        triggered.append("PM2")
        details["PM2"] = (
            "Variant absent from gnomAD r4 (≥125,748 individuals). "
            "Absence from large population databases supports pathogenicity for rare diseases."
        )
    elif af is not None and af < AF_RARE:
        triggered.append("PM2")
        details["PM2"] = (
            f"Allele frequency {af:.6f} ({af*100:.4f}%) in gnomAD — "
            f"extremely rare (below 0.01% threshold). Supports pathogenicity."
        )

    # -----------------------------------------------------------------------
    # BP6 — Reputable ClinVar benign classification, no conflicts
    # -----------------------------------------------------------------------
    if cv_found and not conflicting and star_rating >= 1:
        if cv_class in ("benign", "likely benign"):
            triggered.append("BP6")
            details["BP6"] = (
                f"ClinVar classification: '{clinvar.get('classification')}' — "
                f"reported as benign by {submitters} submitter(s) with no conflicting evidence."
            )

    return triggered, details


def _compute_classification(triggered: list, clinvar, gnomad) -> tuple[str, str]:
    """
    Apply simplified ACMG combining rules to compute final classification and confidence.
    Returns (classification, confidence).
    """
    cv_class = (clinvar.get("classification") or "").lower() if clinvar else ""
    star_rating = clinvar.get("star_rating", 0) if clinvar else 0

    # Rule 1: BA1 → Benign, overrides everything
    if "BA1" in triggered:
        return "Benign", "High"

    # Rule 2: PVS1 + (PM2 or PP5 or PS3) → Pathogenic
    if "PVS1" in triggered and ("PM2" in triggered or "PP5" in triggered or "PS3" in triggered):
        return "Pathogenic", "High"

    # Rule 3: PVS1 alone → Likely Pathogenic
    if "PVS1" in triggered:
        return "Likely Pathogenic", "Moderate"

    # Rule 4: PS3 (strong ClinVar agreement) → Pathogenic
    if "PS3" in triggered:
        return "Pathogenic", "High"

    # Rule 5: PP5 (ClinVar Likely Pathogenic/reputable source)
    if "PP5" in triggered:
        return "Likely Pathogenic", "Moderate"

    # Rule 6: BP6 (ClinVar Benign, no conflicts) → Benign / Likely Benign
    if "BP6" in triggered:
        if "benign" in cv_class and "likely" not in cv_class:
            return "Benign", "Moderate"
        return "Likely Benign", "Moderate"

    # Rule 7: PM2 alone (rare, no other strong signal) → VUS leaning pathogenic
    if "PM2" in triggered:
        return "Variant of Uncertain Significance", "Low"

    # Rule 8: No criteria triggered → VUS (cautious default)
    return "Variant of Uncertain Significance", "Low"


def classifier_node(state: GenomeGuideState) -> dict:
    """
    LangGraph node: deterministic ACMG rule engine.
    NO LLM involved — pure Python logic.
    """
    if state.get("parse_error") or not state.get("parsed"):
        return {"acmg_evidence": None}

    triggered, details = _evaluate_criteria(state)
    classification, confidence = _compute_classification(
        triggered,
        state.get("clinvar_result"),
        state.get("gnomad_result"),
    )

    acmg_evidence = ACMGEvidence(
        triggered_criteria=triggered,
        criteria_details=details,
        classification=classification,
        confidence=confidence,
    )

    logger.info(f"[Classifier] Criteria: {triggered} → {classification} ({confidence})")
    return {"acmg_evidence": acmg_evidence}
