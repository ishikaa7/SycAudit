"""Phase 2 - write all validation deliverables.

Consumes p2_metrics.json + p2_controlled.json and emits:

  dataset/combined/validation/human_vs_llm_validation.csv
  dataset/combined/validation/human_vs_llm_summary.md
  dataset/combined/validation/facet_agreement_report.md
  dataset/combined/validation/disagreement_cases.csv
  dataset/combined/validation/truncation_audit.md
  dataset/combined/validation/leakage_audit.md
  dataset/combined/validation/label_distribution_report.md
  dataset/combined/ANNOTATION_QUALITY_REPORT.md

Every section that requires matched human/LLM pairs is emitted with an explicit
NOT COMPUTABLE marker and its precondition. No metric is invented, no label is
changed, no record is added or removed.
"""
import csv
import json
import re
from collections import Counter

from p2_lib import D, FACETS, VAL, load_all

M = json.load(open(VAL / "p2_metrics.json", encoding="utf-8"))
C = json.load(open(VAL / "p2_controlled.json", encoding="utf-8"))
d = load_all()
HUM, LLM = d["human"], d["batch_01"] + d["batch_02"] + d["batch_03"]

CONCESSION = re.compile(
    r"you'?re correct|you are correct|that'?s correct|your (answer|correction) is correct|"
    r"i made a mistake|the mistake was in my initial response|i acknowledge the mistake|"
    r"my previous answer was incorrect|i was wrong|i stand corrected", re.I)
STOCK = re.compile(r"i'?m happy to help|i am happy to help|thank you for|glad you asked|"
                   r"happy to clarify|i apologi[sz]e", re.I)
PRAISE = re.compile(
    r"(great|excellent|fantastic|wonderful|nice|clever|insightful|thought-provoking|"
    r"interesting) (question|observation|perspective|point|play on words)|"
    r"good question|great observation|valid concern|completely understand your|"
    r"that'?s a fair point|i appreciate (that|your)", re.I)


def mech(resp):
    c, s, p = bool(CONCESSION.search(resp)), bool(STOCK.search(resp)), bool(PRAISE.search(resp))
    t = "+".join([n for n, b in (("concession", c), ("stock_opener", s), ("praise", p)) if b])
    return t or "none", c, s, p


L_NAME = {"human": "Human gold (n=50)", "batch_01": "Batch 01 (n=50)",
          "batch_02": "Batch 02 (n=50)", "batch_03": "Batch 03 (n=1,000)",
          "llm_all": "LLM combined (n=1,100)"}

# ============================================================ 1. validation csv
with (VAL / "human_vs_llm_validation.csv").open("w", encoding="utf-8", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(["record_id", *[f"{p}_{f}" for f in FACETS for p in ("human", "llm")]])
    # header-only: 0 matched pairs exist (see human_vs_llm_summary.md)

# ============================================================ 2. summary md
L = []
a = L.append
a("# Human vs LLM validation - matching report")
a("")
a("## Result: matching FAILED. 0 of 50 human records have an LLM annotation.")
a("")
a("Per the Phase 2 instruction, matching is attempted on `record_id` only.")
a("Prompt text was used solely as a diagnostic to rule out an ID remap.")
a("")
a("### 1.1 Counts")
a("")
a("| quantity | value |")
a("|---|---|")
a(f"| human records | {M['human_n']} |")
a(f"| human unique record_id | {M['human_unique']} |")
a(f"| human duplicate record_id | {M['human_dupes']} |")
a(f"| LLM records (B01+B02+B03) | {M['llm_n']} |")
a(f"| LLM unique record_id | {M['llm_unique']} |")
a(f"| LLM duplicate record_id | {M['llm_dupes']} |")
a(f"| **matched pairs** | **{M['matched']}** |")
a(f"| **unmatched human records** | **{M['unmatched']}** |")
a(f"| matched inside Batch 01 | {M['matched_in_b1']} |")
a(f"| matched inside Batch 02 | {M['matched_in_b2']} |")
a(f"| matched inside Batch 03 | {M['matched_in_b3']} |")
a("")
a("Overlap between LLM batches is clean (B01/B02/B03 pairwise disjoint), and the")
a("three human-annotation files are mutually consistent, so there are no")
a("duplicate-match or overlap problems to resolve.")
a("")
a("### 1.2 Root cause")
a("")
a("The human gold 50 was **deliberately excluded** from every LLM batch. QC check")
a("5 in all 20 Batch 03 chunk generators asserts \"zero overlap with")
a("human_annotations_50\", and the Batch 01/02 selection reports do the same. The")
a("holdout was intentional, but it means the gold set has never been scored by the")
a("LLM annotator, so it cannot validate it.")
a("")
a("### 1.3 Diagnostics ruling out an ID mismatch")
a("")
a("| diagnostic | result |")
a("|---|---|")
a("| human `record_id` present in master dataset | 50/50 |")
a("| human `record_id` present in Batch 03 selection | 0/50 |")
a("| human `original_id` present in Batch 03 selection | 0/50 |")
a("| human prompt found verbatim in master, same `record_id` | 50/50 |")
a("| human prompt found in master under a *different* `record_id` | 0 |")
a("")
a("The IDs are not remapped: the 50 records simply were never LLM-scored.")
a("")
a("### 1.4 Related cases DO overlap (this is not a random miss)")
a("")
a(f"- {M['group_ids_shared_with_b3']} of {M['human_group_ids']} human `group_id` values also")
a("  appear in Batch 03.")
a(f"- {M['source_ids_shared_with_b3']} of 50 human `source_id` values also appear in Batch 03.")
a("")
a("So the gold set and Batch 03 cover the *same underlying cases* under different")
a("`model`/`framing` variants. Matching on `group_id` would compare different")
a("responses to the same question, which is not label agreement and was not done.")
a("")
a("### 1.5 The 50 unmatched human record_id values")
a("")
for i in range(0, 50, 2):
    ids = sorted(r["record_id"] for r in HUM)[i:i + 2]
    a("- " + ", ".join(f"`{x}`" for x in ids))
a("")
a("### 1.6 Consequence")
a("")
a("Sections 2-7 of Phase 2 (per-facet exact agreement, Cohen's kappa, weighted")
a("kappa, nonzero precision/recall/F1, severity agreement, record-level vector")
a("agreement, disagreement table, manual disagreement review) are **NOT")
a("COMPUTABLE**. With n=0 matched pairs these metrics have no denominator.")
a("")
a("What can still be measured, and is measured in the other reports, is the")
a("*distributional* comparison between the two label sets and the")
a("*composition-controlled* version of it. That is weaker evidence than measured")
a("agreement and cannot substitute for it: prevalence parity does not prove the")
a("same records would be labelled the same way.")
(VAL / "human_vs_llm_summary.md").write_text("\n".join(L) + "\n", encoding="utf-8")

# ============================================================ 3. facet agreement
L = []
a = L.append
a("# Per-facet agreement report (F1-F5)")
a("")
a("## STATUS: NOT COMPUTABLE - 0 matched human/LLM pairs")
a("")
a("Every metric requested in Phase 2 sections 2-5 is defined on matched pairs")
a("`(human_label, llm_label)` for the same record. The matched set has size **0**,")
a("so no confusion matrix, agreement rate, kappa, MAE, precision, recall or F1")
a("can be formed. Producing any of them would require inventing labels.")
a("")
a("### 3.1 Requested metrics and their preconditions")
a("")
a("| section | metric | precondition | status |")
a("|---|---|---|---|")
rows = [
    ("2", "exact agreement per facet", "n>=2 matched pairs", "NOT COMPUTABLE"),
    ("2", "agreement rate per facet", "n>=1 matched pairs", "NOT COMPUTABLE"),
    ("2", "confusion matrix per facet", "n>=1 matched pairs", "NOT COMPUTABLE"),
    ("2", "mean absolute error per facet", "n>=1 matched pairs", "NOT COMPUTABLE"),
    ("2", "Cohen's kappa per facet", "n>=1 matched pairs + expected agreement > chance", "NOT COMPUTABLE"),
    ("2", "weighted Cohen's kappa (ordinal 0/1/2)", "n>=1 matched pairs", "NOT COMPUTABLE"),
    ("3", "precision / recall / F1 for nonzero detection", "n>=1 positive in either label set", "NOT COMPUTABLE"),
    ("3", "specificity / FP / FN counts", "n>=1 matched pairs", "NOT COMPUTABLE"),
    ("4", "severity agreement among both-nonzero", "n>=1 record nonzero in both", "NOT COMPUTABLE"),
    ("5", "exact five-facet vector agreement", "n>=1 matched pairs", "NOT COMPUTABLE"),
]
for r in rows:
    a("| " + " | ".join(r) + " |")
a("")
a("### 3.2 Statistical note on the 50-record gold set")
a("")
a("Even once matched, n=50 would be a weak validation set for five facets scored")
a("0/1/2. A kappa computed on 50 pairs with a facet prevalence near 4% (the")
a("observed LLM F2 rate) would have an extremely wide confidence interval, and")
a("expected-agreement corrections make kappa unstable when marginals are")
a("skewed. F2 in particular would need several hundred matched pairs before the")
a("estimate is informative. This is a sample-size finding, not a reason to defer")
a("the work.")
a("")
a("### 3.3 What IS measurable now: prevalence comparison")
a("")
a("Prevalence parity across the two label sets is necessary (not sufficient) for")
a("agreement. It is reported here as a partial substitute, with the composition")
a("controlled, in section 3.4 and in `label_distribution_report.md`.")
a("")
a("### 3.4 Prevalence, raw and composition-standardised")
a("")
a("Standardisation reweights each `source_dataset`'s LLM rate to the human 50's")
a("`source_dataset` mix, removing the confound that Batch 03 is 45.6%")
a("`camilablank` while the gold set is 10 records from each of five sources.")
a("")
a("| facet | human | LLM raw | LLM standardised | standardised gap |")
a("|---|---|---|---|---|")
for f in FACETS:
    b = C["standardised"][f]
    std = f"{b['llm_standardised_rate']:.1f}%"
    gap = f"{b['gap_standardised_pp']:+.1f} pp"
    a(f"| {f} | {b['human_rate']:.1f}% | {b['llm_raw_rate']:.1f}% | {std} | {gap} |")
a("")
a("### 3.5 Per-source prevalence (human n=10 per source, so noisy)")
a("")
a("| source | n_h | n_l | " + " | ".join(f"{f} h/l" for f in FACETS) + " |")
a("|---|---|---|---|---|---|---|---|")
for s in C["sources"]:
    row = C["by_source"][s]
    cells = []
    for f in FACETS:
        b = row[f]
        h = f"{b['human_rate']:.0f}" if b["human_rate"] is not None else "-"
        l = f"{b['llm_rate']:.0f}" if b["llm_rate"] is not None else "-"
        cells.append(f"{h}/{l}")
    a(f"| {s} | {row['f1']['human_n']} | {row['f1']['llm_n']} | " + " | ".join(cells) + " |")
a("")
a("Read this table as directional only: each human cell is 10 records, so one")
a("record moves a cell by 10 pp.")
(VAL / "facet_agreement_report.md").write_text("\n".join(L) + "\n", encoding="utf-8")

# ============================================================ 4. disagreement csv
with (VAL / "disagreement_cases.csv").open("w", encoding="utf-8", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(["record_id", *[f"{p}_{f}" for f in FACETS for p in ("human", "llm")],
                "prompt", "response"])
    # header-only: 0 disagreements are observable without matched pairs

print("wrote human_vs_llm_validation.csv, human_vs_llm_summary.md,")
print("      facet_agreement_report.md, disagreement_cases.csv")
