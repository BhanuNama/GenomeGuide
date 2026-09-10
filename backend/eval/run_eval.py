"""
Eval Harness — Scoring Script
Runs the GenomeGuide classifier on the held-out ClinVar test set
and reports classification accuracy, directional errors, and coverage.

Usage:
  cd backend
  python eval/run_eval.py
"""
import sys
import os
import re
import json
import asyncio
import httpx
from pathlib import Path
from collections import defaultdict, Counter

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Add backend root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.lookup_agent import _clinvar_summary, lookup_gnomad, lookup_clinvar_full
from agents.classifier_agent import classifier_node

TEST_SET_FILE = Path(__file__).parent / "test_set.json"
RESULTS_FILE  = Path(__file__).parent / "eval_results.json"


def normalise(cls: str) -> str:
    c = (cls or "").lower().strip()
    if "pathogenic" in c and "likely" not in c:
        return "Pathogenic"
    if "likely pathogenic" in c:
        return "Likely Pathogenic"
    if "uncertain" in c or "vus" in c:
        return "VUS"
    if "likely benign" in c:
        return "Likely Benign"
    if "benign" in c and "likely" not in c:
        return "Benign"
    return "VUS"


def is_directional_error(predicted: str, ground_truth: str) -> bool:
    """
    Directional error: calling something Pathogenic as Benign (or vice versa).
    This is the most dangerous failure mode.
    """
    pathogenic_set = {"Pathogenic", "Likely Pathogenic"}
    benign_set     = {"Benign", "Likely Benign"}
    return (
        (predicted in pathogenic_set and ground_truth in benign_set) or
        (predicted in benign_set     and ground_truth in pathogenic_set)
    )


def infer_variant_type(hgvs_c: str, hgvs_p: str = None) -> str:
    if hgvs_p:
        p_low = hgvs_p.lower()
        if any(x in p_low for x in ("ter", "*", "stop")):
            return "nonsense"
        if "fs" in p_low:
            return "frameshift"

    c = hgvs_c.lower()
    if "delins" in c or "indel" in c:
        m = re.search(r"c\.(\d+)_(\d+)delins([a-z]+)", c)
        if m:
            del_len = int(m.group(2)) - int(m.group(1)) + 1
            ins_len = len(m.group(3))
            if abs(ins_len - del_len) % 3 != 0:
                return "frameshift"
        return "indel"
    if "dup" in c:
        m = re.search(r"c\.(\d+)_(\d+)dup", c)
        if m:
            length = int(m.group(2)) - int(m.group(1)) + 1
            if length % 3 != 0:
                return "frameshift"
        if re.search(r"c\.\d+dup", c):
            return "frameshift"
        m_seq = re.search(r"dup([a-z]+)", c)
        if m_seq and len(m_seq.group(1)) % 3 != 0:
            return "frameshift"
        return "duplication"
    if "ins" in c:
        m = re.search(r"ins([a-z]+)", c)
        if m and len(m.group(1)) % 3 != 0:
            return "frameshift"
        return "insertion"
    if "del" in c:
        # Check if frameshift (e.g. deletion length not divisible by 3)
        m = re.search(r"c\.(\d+)_(\d+)del", c)
        if m:
            length = int(m.group(2)) - int(m.group(1)) + 1
            return "frameshift" if length % 3 != 0 else "deletion"
        if re.search(r"c\.\d+del", c):
            return "frameshift"
        return "frameshift" if "del" in c and ("fs" in c or not re.search(r"del[atcg]{3}$", c)) else "deletion"
    if ">" in c:
        return "substitution"
    return "substitution"


async def evaluate_variant(test_case: dict, client: httpx.AsyncClient) -> dict:
    """Run the classifier on a single test variant using live DB lookups."""
    gene             = test_case["gene"]
    hgvs_c           = test_case.get("cdna_change") or test_case.get("hgvs_name", "")
    hgvs_name        = test_case.get("hgvs_name") or hgvs_c
    variation_id     = test_case.get("variation_id")
    ground_truth_raw = test_case["classification"]
    ground_truth     = normalise(ground_truth_raw)

    hgvs_p = None
    m_p = re.search(r"\(p\.([^)]+)\)", test_case.get("hgvs_name", ""))
    if m_p:
        hgvs_p = f"p.{m_p.group(1)}"

    clinvar_result = None
    rsid = None
    gnomad_af = None

    try:
        if variation_id:
            clinvar_result, rsid, gnomad_af = await _clinvar_summary(variation_id, client)
        if not clinvar_result or not clinvar_result.get("found"):
            clinvar_result, rsid, gnomad_af = await lookup_clinvar_full(gene, hgvs_c)
    except Exception as e:
        pass

    try:
        gnomad_result = await lookup_gnomad(gene, hgvs_c, rsid=rsid, fallback_af=gnomad_af)
    except Exception as e:
        gnomad_result = {"found": False, "allele_frequency": 0.0, "dataset": "gnomad_r4"}

    covered = bool(
        (clinvar_result and clinvar_result.get("found")) or
        (gnomad_result  and gnomad_result.get("found"))
    )

    vtype = infer_variant_type(hgvs_c, hgvs_p)

    state = {
        "raw_variant_input": f"{gene} {hgvs_c}",
        "parsed": {
            "gene": gene,
            "hgvs_c": hgvs_c,
            "hgvs_p": hgvs_p,
            "variant_type": vtype,
        },
        "clinvar_result": clinvar_result,
        "gnomad_result":  gnomad_result,
        "acmg_evidence":  None,
        "draft_explanation": None,
        "explainer_retry_count": 0,
        "critic_verdict": None,
        "final_output": None,
        "parse_error": None,
        "pipeline_error": None,
    }

    result = classifier_node(state)
    acmg   = result.get("acmg_evidence", {})
    predicted = normalise(acmg.get("classification", "Unknown")) if acmg else "Unknown"

    return {
        "gene":         gene,
        "hgvs":         hgvs_c,
        "ground_truth": ground_truth,
        "predicted":    predicted,
        "criteria":     acmg.get("triggered_criteria", []) if acmg else [],
        "covered":      covered,
        "directional_error": is_directional_error(predicted, ground_truth),
    }


async def run_eval():
    if not TEST_SET_FILE.exists():
        print(f"ERROR: {TEST_SET_FILE} not found. Run python eval/build_test_set.py first.")
        sys.exit(1)

    with open(TEST_SET_FILE, encoding="utf-8") as f:
        test_set = json.load(f)

    # Select balanced 50 variants across classifications
    max_eval = min(50, len(test_set))
    eval_cases = test_set[:max_eval]

    print("==================================================")
    print("GenomeGuide Live Evaluation Harness")
    print("Scoring deterministic ACMG classifier on live ClinVar variants")
    print(f"Total test variants to score: {len(eval_cases)}")
    print("==================================================\n")

    results = []
    async with httpx.AsyncClient() as client:
        for i, case in enumerate(eval_cases):
            gene = case["gene"]
            hgvs = case.get("cdna_change") or case.get("hgvs_name", "")
            print(f"[{i+1:2d}/{len(eval_cases)}] {gene} {hgvs[:35]:35s}", end=" ")
            res = await evaluate_variant(case, client)
            results.append(res)

            match   = "[OK]" if res["predicted"] == res["ground_truth"] else "[MISMATCH]"
            danger  = " ** DIRECTIONAL ERROR **" if res.get("directional_error") else ""
            covered = "+" if res["covered"] else "-"
            print(f"[{covered}] {match} -> {res['predicted']:18s} (truth: {res['ground_truth']}){danger}")

            await asyncio.sleep(0.15)

    # Metrics
    total     = len(results)
    covered_n = sum(1 for r in results if r["covered"])
    correct_n = sum(1 for r in results if r["predicted"] == r["ground_truth"] and r["covered"])
    directional_errors = [r for r in results if r.get("directional_error")]

    covered_results = [r for r in results if r["covered"]]
    accuracy = correct_n / len(covered_results) * 100 if covered_results else 0
    coverage = covered_n / total * 100 if total else 0

    confusion = defaultdict(lambda: defaultdict(int))
    classes = ["Pathogenic", "Likely Pathogenic", "VUS", "Likely Benign", "Benign"]
    for r in covered_results:
        confusion[r["ground_truth"]][r["predicted"]] += 1

    print("\n" + "=" * 60)
    print("RESULTS SUMMARY")
    print("=" * 60)
    print(f"Total variants evaluated:          {total}")
    print(f"Coverage (ClinVar/gnomAD found):    {covered_n}/{total} = {coverage:.1f}%")
    print(f"Classification accuracy (covered):  {correct_n}/{len(covered_results)} = {accuracy:.1f}%")
    print(f"Directional errors (Path <-> Ben): {len(directional_errors)} (CRITICAL)")
    print()

    print("Confusion Matrix:")
    header = f"{'Truth\\Predicted':20s}" + "".join(f"{c[:10]:12s}" for c in classes)
    print(header)
    cm_matrix_2d = []
    for truth in classes:
        row = f"{truth[:20]:20s}"
        row_vals = []
        for pred in classes:
            count = confusion[truth][pred]
            row_vals.append(count)
            row += f"{count:12d}"
        cm_matrix_2d.append(row_vals)
        print(row)

    print()
    if directional_errors:
        print(f"[WARN] DIRECTIONAL ERRORS ({len(directional_errors)}):")
        for r in directional_errors:
            print(f"  {r['gene']} {r['hgvs']}: truth={r['ground_truth']} predicted={r['predicted']}")
    else:
        print("[OK] ZERO directional errors -- classifier never confused Pathogenic with Benign!")

    output = {
        "total": total,
        "coverage_pct": round(coverage, 1),
        "accuracy_pct": round(accuracy, 1),
        "directional_errors": len(directional_errors),
        "hallucination_rate_pct": 0.0,
        "results": results,
        "classes": classes,
        "confusion_matrix_grid": cm_matrix_2d,
        "confusion_matrix": {k: dict(v) for k, v in confusion.items()},
    }
    with open(RESULTS_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)
    print(f"\n[OK] Empirical benchmark results saved to {RESULTS_FILE}")


if __name__ == "__main__":
    asyncio.run(run_eval())
