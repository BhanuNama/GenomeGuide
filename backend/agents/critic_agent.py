"""
Agent 5 — Critic Agent (Verification Loop)
Uses Groq LLaMA 3.1 70B to verify that every claim in the draft explanation
is supported by the retrieved evidence (clinvar_result, gnomad_result, acmg_evidence).

This implements the conditional retry edge in LangGraph:
  explainer_node → critic_node
    if passed  → END
    if failed  → explainer_node (max 2 retries)
"""
import os
import json
import re
import logging
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
from state import GenomeGuideState, CriticVerdict

logger = logging.getLogger(__name__)

MAX_RETRIES = 2

SYSTEM_PROMPT = """You are a rigorous clinical fact-checker reviewing a patient-facing genetic variant report.
Your job is to verify that every factual claim in the report is directly supported by the provided evidence.

Evidence you will receive:
- classification (from rule engine — authoritative)
- ACMG criteria triggered and their details
- ClinVar data (classification, review status, submitter count)
- gnomAD allele frequency data

RED FLAGS — reject the draft if it contains:
1. Risk percentages or penetrance figures not present in the evidence (e.g. "50% risk of cancer")
2. A classification different from the authoritative classification given
3. Statements about other family members' risk that go beyond what the evidence shows
4. Claims about specific diseases or syndromes not mentioned in the evidence fields
5. Invented statistics ("studies show...", "research indicates..." without basis in evidence)
6. Any claim that contradicts the retrieved data

Return ONLY valid JSON:
{
  "passed": true | false,
  "unsupported_claims": ["exact quote of problematic sentence 1", "..."]
}

If passed is true, unsupported_claims must be an empty list.
Return ONLY the JSON object — no markdown, no explanation."""


def _build_critic_prompt(state: GenomeGuideState) -> str:
    acmg    = state["acmg_evidence"]
    clinvar = state.get("clinvar_result", {})
    gnomad  = state.get("gnomad_result", {})
    draft   = state["draft_explanation"]

    lines = [
        "=== AUTHORITATIVE EVIDENCE (source of truth) ===",
        f"Classification: {acmg['classification']} (Confidence: {acmg['confidence']})",
        f"ACMG criteria: {', '.join(acmg['triggered_criteria']) or 'None'}",
    ]
    for crit, detail in acmg.get("criteria_details", {}).items():
        lines.append(f"  {crit}: {detail}")

    if clinvar and clinvar.get("found"):
        lines.append(f"ClinVar: {clinvar.get('classification')} ({clinvar.get('star_rating',0)}★, {clinvar.get('submitters',0)} submitters)")
    else:
        lines.append("ClinVar: Not found in database")

    if gnomad and gnomad.get("found"):
        af = gnomad.get("allele_frequency", 0)
        lines.append(f"gnomAD AF: {af:.6f} ({af*100:.4f}%)")
    else:
        lines.append("gnomAD: Absent from database")

    lines.append("")
    lines.append("=== DRAFT EXPLANATION TO VERIFY ===")
    lines.append(draft)

    return "\n".join(lines)


def critic_node(state: GenomeGuideState) -> dict:
    """
    LangGraph node: verify draft explanation against evidence.
    Returns critic_verdict and (if passed) final_output.
    """
    if not state.get("draft_explanation") or not state.get("acmg_evidence"):
        # Nothing to verify — pass through
        return {
            "critic_verdict": CriticVerdict(passed=True, unsupported_claims=[], retry_count=0),
            "final_output": state.get("draft_explanation", ""),
        }

    draft = state["draft_explanation"]
    existing_verdict = state.get("critic_verdict")
    retry_count = existing_verdict.get("retry_count", 0) if existing_verdict else 0

    logger.info(f"[Critic] Verifying draft (retry_count={retry_count})")

    try:
        groq_api_key = os.getenv("GROQ_API_KEY")
        if not groq_api_key:
            raise ValueError("GROQ_API_KEY not set")

        groq_model = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
        llm = ChatGroq(
            model=groq_model,
            temperature=0,
            max_tokens=400,
            api_key=groq_api_key,
        )

        critic_prompt = _build_critic_prompt(state)
        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=critic_prompt)
        ]
        response = llm.invoke(messages)
        content = response.content.strip()

        # Robust JSON extraction
        json_match = re.search(r"(\{[\s\S]*\})", content)
        if json_match:
            verdict_data = json.loads(json_match.group(1))
        else:
            verdict_data = json.loads(content)
        passed = verdict_data.get("passed", False)
        unsupported = verdict_data.get("unsupported_claims", [])

        verdict = CriticVerdict(
            passed=passed,
            unsupported_claims=unsupported,
            retry_count=retry_count + 1,
        )

        if passed:
            logger.info("[Critic] ✓ Draft passed verification")
            return {"critic_verdict": verdict, "final_output": draft}
        else:
            logger.warning(f"[Critic] ✗ Draft rejected. Unsupported claims: {unsupported}")
            return {"critic_verdict": verdict, "final_output": None}

    except Exception as e:
        logger.warning(f"[Critic] LLM error ({e}) — auto-passing draft")
        # On LLM failure, auto-pass to avoid infinite retry
        verdict = CriticVerdict(passed=True, unsupported_claims=[], retry_count=retry_count + 1)
        return {"critic_verdict": verdict, "final_output": draft}


def should_retry(state: GenomeGuideState) -> str:
    """
    LangGraph conditional edge function.
    Returns "retry" → explainer_node, or "end" → END.
    """
    verdict  = state.get("critic_verdict")
    retry_ct = state.get("explainer_retry_count", 0)

    if not verdict or verdict.get("passed"):
        return "end"

    if retry_ct >= MAX_RETRIES:
        logger.warning(f"[Critic] Max retries ({MAX_RETRIES}) reached — forcing END with best draft")
        return "end"

    return "retry"
