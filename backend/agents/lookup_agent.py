"""
Agent 2 — Database Lookup Agent
Calls ClinVar (NCBI E-utilities) and gnomAD (public GraphQL) APIs.
NO LLM involved — pure async HTTP calls.
"""
import os
import re
import logging
import asyncio
import httpx
from typing import Optional
from state import GenomeGuideState, ClinVarResult, GnomADResult
from agents.literature_agent import search_pubmed_literature


logger = logging.getLogger(__name__)

CLINVAR_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
GNOMAD_BASE  = "https://gnomad.broadinstitute.org/api"

# Map review status strings to star ratings
REVIEW_STAR_MAP = {
    "practice guideline": 4,
    "reviewed by expert panel": 3,
    "criteria provided, multiple submitters, no conflicts": 2,
    "criteria provided, conflicting classifications": 1,
    "criteria provided, single submitter": 1,
    "no assertion criteria provided": 0,
    "no classification provided": 0,
    "no classifications from unflagged records": 0,
}


# ---------------------------------------------------------------------------
# ClinVar
# ---------------------------------------------------------------------------
async def _clinvar_search(gene: str, hgvs_c: str, client: httpx.AsyncClient) -> Optional[str]:
    """Search ClinVar for a variant, return variation_id or None."""
    ncbi_key = os.getenv("NCBI_API_KEY", "")
    params = {
        "db": "clinvar",
        "term": f"{gene}[gene] AND {hgvs_c}[variant name]",
        "retmode": "json",
        "retmax": "5",
    }
    if ncbi_key:
        params["api_key"] = ncbi_key

    try:
        r = await client.get(f"{CLINVAR_BASE}/esearch.fcgi", params=params, timeout=15.0)
        r.raise_for_status()
        data = r.json()
        ids = data.get("esearchresult", {}).get("idlist", [])
        if ids:
            return ids[0]

        # Second attempt: search by gene + hgvs_c without position
        # Try a broader search with just the transcript notation
        params2 = {
            "db": "clinvar",
            "term": f"{gene}[gene] AND {hgvs_c}[All Fields]",
            "retmode": "json",
            "retmax": "5",
        }
        if ncbi_key:
            params2["api_key"] = ncbi_key
        r2 = await client.get(f"{CLINVAR_BASE}/esearch.fcgi", params=params2, timeout=15.0)
        r2.raise_for_status()
        data2 = r2.json()
        ids2 = data2.get("esearchresult", {}).get("idlist", [])
        return ids2[0] if ids2 else None

    except Exception as e:
        logger.warning(f"[Lookup] ClinVar search error: {e}")
        return None


async def _clinvar_summary(variation_id: str, client: httpx.AsyncClient) -> Optional[ClinVarResult]:
    """Fetch esummary for a ClinVar variation_id and parse into ClinVarResult."""
    ncbi_key = os.getenv("NCBI_API_KEY", "")
    params = {
        "db": "clinvar",
        "id": variation_id,
        "retmode": "json",
    }
    if ncbi_key:
        params["api_key"] = ncbi_key

    try:
        r = await client.get(f"{CLINVAR_BASE}/esummary.fcgi", params=params, timeout=15.0)
        r.raise_for_status()
        data = r.json()

        result = data.get("result", {})
        if not result or variation_id not in result:
            return None

        doc = result[variation_id]

        # Extract classification
        germline = doc.get("germline_classification", {})
        classification = (
            germline.get("description")
            or doc.get("clinical_significance", {}).get("description")
            or "Unknown"
        )

        # Extract review status
        review_status = (
            germline.get("review_status")
            or doc.get("clinical_significance", {}).get("review_status")
            or ""
        ).lower()
        star_rating = REVIEW_STAR_MAP.get(review_status, 0)

        # Count submitters
        submitters = 0
        supporting_submissions = doc.get("supporting_submissions", {})
        if supporting_submissions:
            scv_list = supporting_submissions.get("scv", [])
            submitters = len(scv_list) if isinstance(scv_list, list) else 0

        conflicting = "conflict" in review_status

        # Extract dbSNP rsID and ClinVar-catalogued gnomAD frequency
        rsid = None
        gnomad_af = None
        variation_set = doc.get("variation_set", [{}])
        if variation_set:
            v0 = variation_set[0]
            for xref in v0.get("variation_xrefs", []):
                if xref.get("db_source") == "dbSNP":
                    rsid = f"rs{xref.get('db_id')}"
                    break
            for freq in v0.get("allele_freq_set", []):
                if "gnomAD" in freq.get("source", ""):
                    try:
                        gnomad_af = float(freq.get("value", 0))
                    except (ValueError, TypeError):
                        pass
                    break

        return ClinVarResult(
            found=True,
            variation_id=variation_id,
            classification=classification,
            review_status=review_status,
            star_rating=star_rating,
            submitters=submitters,
            conflicting=conflicting,
        ), rsid, gnomad_af

    except Exception as e:
        logger.warning(f"[Lookup] ClinVar summary error for {variation_id}: {e}")
        return None, None, None


async def lookup_clinvar_full(gene: str, hgvs_c: str):
    """Full ClinVar lookup returning (ClinVarResult, rsid, gnomad_af)."""
    async with httpx.AsyncClient() as client:
        variation_id = await _clinvar_search(gene, hgvs_c, client)
        if not variation_id:
            return ClinVarResult(
                found=False, variation_id=None, classification=None,
                review_status=None, star_rating=0, submitters=0, conflicting=False
            ), None, None

        await asyncio.sleep(0.35)  # NCBI rate-limit courtesy
        result, rsid, gnomad_af = await _clinvar_summary(variation_id, client)
        if result:
            return result, rsid, gnomad_af

        return ClinVarResult(
            found=True, variation_id=variation_id, classification=None,
            review_status=None, star_rating=0, submitters=0, conflicting=False
        ), None, None


async def lookup_clinvar(gene: str, hgvs_c: str) -> ClinVarResult:
    """Standard ClinVar lookup for backward compatibility."""
    result, _, _ = await lookup_clinvar_full(gene, hgvs_c)
    return result


# ---------------------------------------------------------------------------
# gnomAD Live GraphQL
# ---------------------------------------------------------------------------
GNOMAD_QUERY_RSID = """
query getVariantByRsid($rsid: String!, $dataset: DatasetId!) {
  variant(rsid: $rsid, dataset: $dataset) {
    variantId
    exome {
      ac
      an
    }
    genome {
      ac
      an
    }
  }
}
"""

GNOMAD_QUERY_VID = """
query getVariantById($variantId: String!, $dataset: DatasetId!) {
  variant(variantId: $variantId, dataset: $dataset) {
    variantId
    exome {
      ac
      an
    }
    genome {
      ac
      an
    }
  }
}
"""


async def lookup_gnomad(gene: str, hgvs_c: str, rsid: Optional[str] = None, fallback_af: Optional[float] = None) -> GnomADResult:
    """
    Query gnomAD v4 GraphQL API dynamically for real allele frequencies.
    Uses rsID if resolved from ClinVar, otherwise falls back to ClinVar-recorded gnomAD AF,
    or reports absent (frequency = 0.0) for ultra-rare variants.
    """
    # 1. Try querying live gnomAD GraphQL via rsID
    if rsid:
        try:
            async with httpx.AsyncClient() as client:
                r = await client.post(
                    GNOMAD_BASE,
                    json={
                        "query": GNOMAD_QUERY_RSID,
                        "variables": {"rsid": rsid, "dataset": "gnomad_r4"}
                    },
                    headers={"Content-Type": "application/json"},
                    timeout=15.0,
                )
                if r.status_code == 200:
                    data = r.json()
                    variant_data = data.get("data", {}).get("variant")
                    if variant_data:
                        exome  = variant_data.get("exome") or {}
                        genome = variant_data.get("genome") or {}

                        # Prefer exome if non-null, else genome
                        source = exome if (exome.get("an") or 0) > 0 else genome
                        ac = source.get("ac") or 0
                        an = source.get("an") or 0
                        af = (float(ac) / float(an)) if an > 0 else 0.0

                        logger.info(f"[Lookup] gnomAD live hit for {rsid}: variantId={variant_data.get('variantId')}, ac={ac}, an={an}, af={af:.6f}")
                        return GnomADResult(
                            found=True,
                            allele_frequency=float(af),
                            allele_count=int(ac),
                            allele_number=int(an),
                            dataset="gnomad_r4",
                        )
        except Exception as e:
            logger.warning(f"[Lookup] gnomAD live query error for {rsid}: {e}")

    # 2. If live GraphQL query didn't return variant, check ClinVar-catalogued gnomAD frequency
    if fallback_af is not None:
        logger.info(f"[Lookup] gnomAD using ClinVar-catalogued AF for {gene} {hgvs_c}: {fallback_af}")
        return GnomADResult(
            found=True,
            allele_frequency=float(fallback_af),
            allele_count=None,
            allele_number=None,
            dataset="gnomad_clinvar_record",
        )

    # 3. Truly absent / novel variant in population database
    logger.info(f"[Lookup] gnomAD: variant {gene} {hgvs_c} is absent from population databases (PM2 rare/absent)")
    return GnomADResult(
        found=False,
        allele_frequency=0.0,
        allele_count=0,
        allele_number=None,
        dataset="gnomad_r4",
    )


# ---------------------------------------------------------------------------
# LangGraph node
# ---------------------------------------------------------------------------
async def lookup_node_async(state: GenomeGuideState) -> dict:
    """Async LangGraph node: parallel ClinVar + gnomAD lookup using real live APIs."""
    if state.get("parse_error") or not state.get("parsed"):
        return {"clinvar_result": None, "gnomad_result": None}

    parsed = state["parsed"]
    gene   = parsed["gene"]
    hgvs_c = parsed["hgvs_c"]

    logger.info(f"[Lookup] Live querying ClinVar + gnomAD + PubMed for {gene} {hgvs_c}")

    # Query ClinVar first to obtain clinical assertions, dbSNP rsID, and gnomAD record
    clinvar_result, rsid, gnomad_af = await lookup_clinvar_full(gene, hgvs_c)

    # Query gnomAD GraphQL and NCBI PubMed literature in parallel
    gnomad_task = lookup_gnomad(gene, hgvs_c, rsid=rsid, fallback_af=gnomad_af)
    literature_task = search_pubmed_literature(gene, hgvs_c, rsid=rsid)

    gnomad_result, literature_evidence = await asyncio.gather(gnomad_task, literature_task)

    logger.info(f"[Lookup] ClinVar: {clinvar_result}")
    logger.info(f"[Lookup] gnomAD:  {gnomad_result}")
    logger.info(f"[Lookup] PubMed Literature: {len(literature_evidence)} articles retrieved")

    return {
        "clinvar_result": clinvar_result,
        "gnomad_result":  gnomad_result,
        "literature_evidence": literature_evidence,
    }



def lookup_node(state: GenomeGuideState) -> dict:
    """Synchronous wrapper for the async lookup node (required by LangGraph sync graph)."""
    return asyncio.run(lookup_node_async(state))

