"""
Agent 2B / Literature RAG — PubMed Scientific Literature Retrieval
Queries the National Library of Medicine (NCBI PubMed) for published peer-reviewed
studies, clinical trials, and functional characterizations of the variant.
"""
import os
import re
import logging
import asyncio
import httpx
from typing import Optional, List, Dict

logger = logging.getLogger(__name__)

PUBMED_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"


async def search_pubmed_literature(
    gene: str,
    hgvs_c: str,
    rsid: Optional[str] = None,
    client: Optional[httpx.AsyncClient] = None,
    max_results: int = 3
) -> List[Dict]:
    """
    Query NCBI PubMed for primary literature mentioning the variant or rsID.
    Returns a structured list of literature evidence with PMIDs, titles, and journal citations.
    """
    ncbi_key = os.getenv("NCBI_API_KEY", "")

    # Clean hgvs_c for search (e.g. c.68_69delAG -> "c.68_69delAG" or "68_69del")
    clean_hgvs = hgvs_c
    short_hgvs = re.sub(r"^c\.", "", hgvs_c)

    search_terms = [f'"{clean_hgvs}"', f'"{short_hgvs}"']
    if rsid:
        search_terms.append(f'"{rsid}"')

    term_query = f"{gene}[Title/Abstract] AND ({' OR '.join(search_terms)})"

    params = {
        "db": "pubmed",
        "term": term_query,
        "retmode": "json",
        "retmax": str(max_results),
        "sort": "pub_date",
    }
    if ncbi_key:
        params["api_key"] = ncbi_key

    close_client = False
    if client is None:
        client = httpx.AsyncClient()
        close_client = True

    try:
        r = await client.get(f"{PUBMED_BASE}/esearch.fcgi", params=params, timeout=12.0)
        r.raise_for_status()
        id_list = r.json().get("esearchresult", {}).get("idlist", [])

        # If strict term query returned no hits, try a broader query: gene AND variant name
        if not id_list and rsid:
            params["term"] = f"{gene} AND {rsid}"
            r = await client.get(f"{PUBMED_BASE}/esearch.fcgi", params=params, timeout=12.0)
            if r.status_code == 200:
                id_list = r.json().get("esearchresult", {}).get("idlist", [])

        if not id_list:
            logger.info(f"[Literature RAG] No PubMed papers found for {gene} {hgvs_c}")
            return []

        # Fetch summaries for the retrieved PMIDs
        sum_params = {
            "db": "pubmed",
            "id": ",".join(id_list),
            "retmode": "json",
        }
        if ncbi_key:
            sum_params["api_key"] = ncbi_key

        sr = await client.get(f"{PUBMED_BASE}/esummary.fcgi", params=sum_params, timeout=12.0)
        sr.raise_for_status()
        result_dict = sr.json().get("result", {})

        articles = []
        for pmid in id_list:
            doc = result_dict.get(pmid)
            if not doc:
                continue

            title = doc.get("title", "").rstrip(".")
            journal = doc.get("source", "")
            pubdate = doc.get("pubdate", "")
            authors = [a.get("name") for a in doc.get("authors", []) if a.get("name")]
            author_str = f"{authors[0]} et al." if len(authors) > 1 else (authors[0] if authors else "Unknown")

            # Extract DOI if present
            doi = None
            for article_id in doc.get("articleids", []):
                if article_id.get("idtype") == "doi":
                    doi = article_id.get("value")
                    break

            articles.append({
                "pmid": pmid,
                "title": title,
                "journal": journal,
                "pubdate": pubdate,
                "authors": author_str,
                "doi": doi,
                "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
            })

        logger.info(f"[Literature RAG] Retrieved {len(articles)} PubMed articles for {gene} {hgvs_c}")
        return articles

    except Exception as e:
        logger.warning(f"[Literature RAG] Error querying PubMed: {e}")
        return []
    finally:
        if close_client:
            await client.aclose()
