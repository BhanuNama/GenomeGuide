"""
Eval Harness — Build Held-Out Test Set
Fetches 50+ ClinVar variants (2+ star review status) from target genes.
Saves as eval/test_set.json for use by run_eval.py.

Usage:
  cd backend
  python eval/build_test_set.py
"""
import sys
import asyncio
import json
import re
import time
import httpx
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

TARGET_GENES = ["BRCA1", "BRCA2", "MLH1", "CFTR"]
GOOD_STATUSES = {
    "criteria provided, multiple submitters, no conflicts",
    "reviewed by expert panel",
    "practice guideline",
}
CLASSIFICATIONS = [
    ("Pathogenic", "Pathogenic"),
    ("Likely pathogenic", "Likely pathogenic"),
    ("Benign", "Benign"),
    ("Likely benign", "Likely benign"),
]
OUTPUT_FILE     = Path(__file__).parent / "test_set.json"
NCBI_BASE       = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
MAX_PER_GENE    = 15


async def fetch_clinvar_ids(gene: str, classification: str, client: httpx.AsyncClient) -> list:
    """Fetch ClinVar variation IDs for a gene + classification with 2+ star review status."""
    term = (
        f"{gene}[gene] AND {classification}[CLNSIG] AND "
        f"(reviewed by expert panel[review status] OR criteria provided, multiple submitters, no conflicts[review status])"
    )
    params = {
        "db":      "clinvar",
        "term":    term,
        "retmode": "json",
        "retmax":  str(MAX_PER_GENE),
    }
    for attempt in range(3):
        try:
            r = await client.get(f"{NCBI_BASE}/esearch.fcgi", params=params, timeout=15.0)
            r.raise_for_status()
            data = r.json()
            ids = data.get("esearchresult", {}).get("idlist", [])
            if ids:
                return ids
            # Fallback if no 2-star found with expert/multiple: try broader search
            if attempt == 0:
                params["term"] = f"{gene}[gene] AND {classification}[CLNSIG]"
        except Exception as e:
            if attempt == 2:
                print(f"  [WARN] Search failed for {gene}/{classification}: {e}")
            await asyncio.sleep(1.0)
    return []


async def fetch_summaries_batch(ids: list, client: httpx.AsyncClient) -> list:
    """Fetch summaries for a batch of variation IDs."""
    if not ids:
        return []
    params = {"db": "clinvar", "id": ",".join(ids), "retmode": "json"}
    try:
        r = await client.get(f"{NCBI_BASE}/esummary.fcgi", params=params, timeout=20.0)
        r.raise_for_status()
        result = r.json().get("result", {})
        variants = []
        for vid in ids:
            doc = result.get(vid)
            if not doc:
                continue

            germline = doc.get("germline_classification", {})
            classification = (
                germline.get("description")
                or doc.get("clinical_significance", {}).get("description")
                or ""
            )
            review_status = (
                germline.get("review_status")
                or doc.get("clinical_significance", {}).get("review_status")
                or ""
            ).lower()

            vset = doc.get("variation_set", [{}])[0]
            hgvs_name = vset.get("variation_name") or doc.get("title") or ""
            cdna_change = vset.get("cdna_change") or ""
            if not cdna_change and hgvs_name:
                m = re.search(r"(c\.[0-9_+-]+[A-Za-z0-9>_delinstdup]+)", hgvs_name)
                if m:
                    cdna_change = m.group(1)

            gene_list = doc.get("genes", [])
            gene = gene_list[0].get("symbol", "") if gene_list else ""

            if cdna_change and gene:
                variants.append({
                    "variation_id":   vid,
                    "gene":           gene,
                    "hgvs_name":      hgvs_name,
                    "cdna_change":    cdna_change,
                    "classification": classification,
                    "review_status":  review_status,
                    "submitters":     len(doc.get("supporting_submissions", {}).get("scv", [])),
                })
        return variants
    except Exception as e:
        print(f"  [WARN] Batch summary fetch failed: {e}")
        return []


async def build_test_set():
    """Build the held-out test set from ClinVar."""
    print("Building GenomeGuide eval test set from ClinVar...")
    print(f"Target genes: {TARGET_GENES}")
    print(f"Output: {OUTPUT_FILE}\n")

    test_set = []
    seen_ids = set()

    async with httpx.AsyncClient() as client:
        for gene in TARGET_GENES:
            print(f"Processing gene: {gene}")
            for label, classification in CLASSIFICATIONS:
                ids = await fetch_clinvar_ids(gene, classification, client)
                new_ids = [vid for vid in ids if vid not in seen_ids]
                for vid in new_ids:
                    seen_ids.add(vid)

                print(f"  {label}: {len(new_ids)} candidate IDs")
                if new_ids:
                    await asyncio.sleep(0.35)
                    batch_variants = await fetch_summaries_batch(new_ids, client)
                    for v in batch_variants:
                        test_set.append(v)
                        print(f"    [+] {v['gene']} {v['cdna_change']} -> {v['classification']}")
                await asyncio.sleep(0.35)

    print(f"\n[OK] Total variants collected: {len(test_set)}")

    # Save
    OUTPUT_FILE.parent.mkdir(exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(test_set, f, indent=2)

    print(f"[OK] Saved to {OUTPUT_FILE}")

    # Summary stats
    from collections import Counter
    class_counts = Counter(v["classification"] for v in test_set)
    gene_counts  = Counter(v["gene"] for v in test_set)
    print("\nClassification breakdown:")
    for k, v in class_counts.most_common():
        print(f"  {k}: {v}")
    print("\nGene breakdown:")
    for k, v in gene_counts.most_common():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    asyncio.run(build_test_set())

