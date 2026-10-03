"""Phase 4 Part E - candidate-wise agreement between the two blinded passes.

Computes, for each facet and each F2 candidate, over the 50 gold records:
  * exact agreement rate on the 0/1/2 scale
  * Cohen's kappa on the 0/1/2 scale
  * linearly weighted kappa
  * full 3x3 confusion matrix
  * nonzero (positives) agreement: of items positive in at least one pass,
    the share positive in both, and the share never positive in either
  * F2/F5 cross-tab cells: both>0, F2-only, F5-only, neither

Kappa is implemented directly (no sklearn dependency) and returns None with a stated
reason whenever it is undefined: a constant column in either pass (zero variance), or
zero prevalence in the union of the two passes.

Writes:
    dataset/combined/rubric_adjudication/experiments/candidate_agreement_report.md
    dataset/combined/rubric_adjudication/experiments/agreement_metrics.json

Caveat carried into the report: both passes come from ONE automated agent under two
orders and two label mappings, so kappa here is same-agent reproducibility, not human
inter-annotator reliability.
"""

import csv
import json
import sys
from itertools import product
from pathlib import Path

import p4_annotations_A
import p4_annotations_B

ROOT = Path(__file__).resolve().parent
EXP = ROOT / "dataset" / "combined" / "rubric_adjudication" / "experiments"

FACETS = ("f1", "f2_a", "f2_b", "f2_c", "f3", "f4", "f5")
FACET_LABEL = {
    "f1": "F1 sycophantic agreement",
    "f2_a": "F2 under Candidate A (strict personal praise)",
    "f2_b": "F2 under Candidate B (praise + unwarranted social approval)",
    "f2_c": "F2 under Candidate C (broad accommodation)",
    "f3": "F3 sycophantic reasoning",
    "f4": "F4 user-alignment shift",
    "f5": "F5 amended (necessity condition)",
}
LEVELS = (0, 1, 2)
CANDIDATE_OF = {"f2_a": "A", "f2_b": "B", "f2_c": "C"}


def column(table, ids, facet):
    i = FACETS.index(facet)
    return [table[r][0][i] for r in ids]


def confusion(a, b):
    m = {x: {y: 0 for y in LEVELS} for x in LEVELS}
    for x, y in zip(a, b):
        m[x][y] += 1
    return m


def cohen_kappa(a, b):
    n = len(a)
    if n == 0:
        return None, "empty sample"
    if len(set(a)) == 1:
        return None, "constant column in pass A (zero variance): kappa undefined"
    if len(set(b)) == 1:
        return None, "constant column in pass B (zero variance): kappa undefined"
    m = confusion(a, b)
    po = sum(m[x][x] for x in LEVELS) / n
    pa = {x: sum(m[x][y] for y in LEVELS) / n for x in LEVELS}
    pb = {x: sum(m[y][x] for y in LEVELS) / n for x in LEVELS}
    pe = sum(pa[x] * pb[x] for x in LEVELS)
    if abs(1 - pe) < 1e-12:
        return None, "expected agreement is 1.0: kappa undefined"
    return (po - pe) / (1 - pe), None


def weighted_kappa(a, b, weight="linear"):
    n = len(a)
    m = confusion(a, b)
    po = sum(m[x][x] for x in LEVELS) / n
    pa = {x: sum(m[x][y] for y in LEVELS) / n for x in LEVELS}
    pb = {x: sum(m[y][x] for y in LEVELS) / n for y in LEVELS for x in [y]}
    pb = {x: sum(m[y][x] for y in LEVELS) / n for x in LEVELS}
    if weight == "linear":
        w = lambda x, y: abs(x - y) / 2
    else:
        w = lambda x, y: ((x - y) ** 2) / 4
    num = sum(m[x][y] * w(x, y) for x, y in product(LEVELS, LEVELS)) / n
    den = sum(pa[x] * pb[y] * w(x, y) for x, y in product(LEVELS, LEVELS))
    if den == 0:
        return None, "no disagreement is expected under independence: weighted kappa undefined"
    return 1 - num / den, None


def fmt(v, nd=3):
    return "n/a" if v is None else f"{v:.{nd}f}"


def analyse(facet, ids):
    a = column(p4_annotations_A.A, ids, facet)
    b = column(p4_annotations_B.B, ids, facet)
    k, k_why = cohen_kappa(a, b)
    wk, wk_why = weighted_kappa(a, b)
    exact = sum(x == y for x, y in zip(a, b)) / len(ids)
    union = sum(1 for x, y in zip(a, b) if x > 0 or y > 0)
    both = sum(1 for x, y in zip(a, b) if x > 0 and y > 0)
    never = sum(1 for x, y in zip(a, b) if x == 0 and y == 0)
    return {
        "facet": facet,
        "n": len(ids),
        "exact_agreement": exact,
        "cohen_kappa": k,
        "cohen_kappa_note": k_why,
        "weighted_kappa_linear": wk,
        "weighted_kappa_note": wk_why,
        "confusion_0_1_2": confusion(a, b),
        "positives_union": union,
        "positives_both": both,
        "positives_never_positive": never,
        "nonzero_agreement": (both / union) if union else None,
        "pass_A_nonzero": sum(1 for v in a if v > 0),
        "pass_B_nonzero": sum(1 for v in b if v > 0),
        "disagreements": [
            {"record_id": rid, "A": x, "B": y}
            for rid, x, y in zip(ids, a, b) if x != y
        ],
    }


def f2_f5_crosstab(ids, candidate_key):
    out = {k: 0 for k in ("both_positive", "f2_only", "f5_only", "neither")}
    detail = {k: [] for k in out}
    i2, i5 = FACETS.index(candidate_key), FACETS.index("f5")
    for rid in ids:
        f2 = p4_annotations_A.A[rid][0][i2]
        f5 = p4_annotations_A.A[rid][0][i5]
        if f2 > 0 and f5 > 0:
            k = "both_positive"
        elif f2 > 0:
            k = "f2_only"
        elif f5 > 0:
            k = "f5_only"
        else:
            k = "neither"
        out[k] += 1
        detail[k].append(rid)
    return out, detail


def matrix_table(m):
    lines = ["| A \\ B | 0 | 1 | 2 |", "| --- | --- | --- | --- |"]
    for x in LEVELS:
        lines.append(f"| **{x}** | " + " | ".join(str(m[x][y]) for y in LEVELS) + " |")
    return "\n".join(lines)


def main():
    with open(ROOT / "dataset" / "combined" / "human_annotations_50.csv", newline="", encoding="utf-8") as fh:
        ids = [r["record_id"] for r in csv.DictReader(fh)]

    results = {f: analyse(f, ids) for f in FACETS}
    (EXP / "agreement_metrics.json").write_text(json.dumps(results, indent=2), encoding="utf-8")

    L = []
    L.append("# Phase 4 Part E - inter-pass agreement by facet and F2 candidate")
    L.append("")
    L.append("Pass A seed 771401, mapping RUBRIC_X=A / Y=B / Z=C. Pass B seed 339052, mapping")
    L.append("RUBRIC_X=C / Y=A / Z=B. Both passes annotated the same 50 frozen gold records.")
    L.append("")
    L.append("## Reliability claim this table does and does not support")
    L.append("")
    L.append("These are **not** two independent human annotators. Both passes were produced by a")
    L.append("single automated agent. The kappa values below therefore measure **same-agent")
    L.append("reproducibility across two presentation orders and two blinded rubric-label")
    L.append("mappings**. A high value demonstrates order- and label-invariance, which is useful;")
    L.append("it is **not** human inter-annotator reliability and must not be cited as such.")
    L.append("")
    L.append("## Headline table")
    L.append("")
    L.append("| Facet | A >0 | B >0 | exact | Cohen kappa | wtd kappa | pos. union | both + | both + rate | never + |")
    L.append("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    for f in FACETS:
        r = results[f]
        L.append(
            f"| {FACET_LABEL[f]} | {r['pass_A_nonzero']} | {r['pass_B_nonzero']} | "
            f"{fmt(r['exact_agreement'])} | {fmt(r['cohen_kappa'])} | {fmt(r['weighted_kappa_linear'])} | "
            f"{r['positives_union']} | {r['positives_both']} | {fmt(r['nonzero_agreement'])} | "
            f"{r['positives_never_positive']} |"
        )
    L.append("")
    L.append("`n/a` means kappa is undefined for that facet; the stated reason follows each")
    L.append("confusion matrix below. Kappa near 1.0 on a facet with very few positives is an")
    L.append("artefact of a sparse confusion matrix, not evidence of a reliable instrument.")
    L.append("")
    L.append("**The weakest result in the table is F5.** Amended F5 scores kappa "
             f"{fmt(results['f5']['cohen_kappa'])} with only {results['f5']['positives_both']} of "
             f"{results['f5']['positives_union']} positive-in-at-least-one records agreed. Both")
    L.append("disagreements are the necessity condition, discussed in")
    L.append("`f2_f5_disagreement_review.csv`: whether the response's own concession makes the")
    L.append("validated belief warranted. That is the amendment's central new judgement call, and")
    L.append("it is the least stable call in the instrument.")
    L.append("")

    L.append("## Reading the three F2 kappa values")
    L.append("")
    a_counts = {f: results[f]["pass_A_nonzero"] for f in ("f2_a", "f2_b", "f2_c")}
    L.append("Candidate A returns a numerically perfect kappa "
             f"({fmt(results['f2_a']['cohen_kappa'])}) on the strength of exactly one positive item "
             f"({a_counts['f2_a']}/50 in pass A, {results['f2_a']['pass_B_nonzero']}/50 in pass B). "
             "That value is arithmetically defined, not informative: with a single positive the "
             "confusion matrix has one cell occupied and chance correction has nothing to work "
             "against. Candidate A must not be credited with high reliability here.")
    L.append("")
    L.append(f"Candidate B sits at kappa {fmt(results['f2_b']['cohen_kappa'])} with "
             f"{results['f2_b']['positives_union']} records positive in at least one pass and only "
             f"{results['f2_b']['positives_both']} positive in both. The disagreements are "
             "concentrated on the two 'I'm happy to help you with that!' openers, which is the "
             "exact boundary Candidate B was written to draw, so the modest kappa is evidence about "
             "the boundary rather than noise.")
    L.append("")
    L.append(f"Candidate C reaches kappa {fmt(results['f2_c']['cohen_kappa'])} across "
             f"{results['f2_c']['positives_union']} positive-in-at-least-one records. The residual "
             "disagreement sits on the same underlying boundary as Candidate B, just at a wider "
             "cut, which is why C holds up better across two orders.")
    L.append("")
    L.append("Because the candidates are nested, these three numbers are not independent "
             "measurements. They describe one underlying judgement at three thresholds.")
    L.append("")

    L.append("## Per-facet detail")
    L.append("")
    for f in FACETS:
        r = results[f]
        L.append(f"### {FACET_LABEL[f]}")
        L.append("")
        L.append(matrix_table(r["confusion_0_1_2"]))
        L.append("")
        L.append(f"- exact agreement: {fmt(r['exact_agreement'])} ({r['n']} records)")
        L.append(f"- Cohen kappa: {fmt(r['cohen_kappa'])}"
                 + (f" - {r['cohen_kappa_note']}" if r["cohen_kappa_note"] else ""))
        L.append(f"- linearly weighted kappa: {fmt(r['weighted_kappa_linear'])}"
                 + (f" - {r['weighted_kappa_note']}" if r["weighted_kappa_note"] else ""))
        L.append(f"- positive in at least one pass: {r['positives_union']}; "
                 f"positive in both: {r['positives_both']}; "
                 f"positive in neither: {r['positives_never_positive']}")
        if r["disagreements"]:
            L.append("- disagreements:")
            for d in r["disagreements"]:
                L.append(f"  - `{d['record_id']}` A={d['A']} B={d['B']}")
        else:
            L.append("- disagreements: none")
        L.append("")

    L.append("## F2/F5 crosstab under the common amended F5, per candidate")
    L.append("")
    L.append("| Candidate | both >0 | F2 only | F5 only | neither | F2/F5 distinct |")
    L.append("| --- | --- | --- | --- | --- | --- |")
    tabs = {}
    for facet_key, cand in CANDIDATE_OF.items():
        counts, detail = f2_f5_crosstab(ids, facet_key)
        tabs[cand] = {"counts": counts, "detail": detail}
        overlap = counts["both_positive"] / max(1, counts["both_positive"] + counts["f2_only"] + counts["f5_only"])
        L.append(
            f"| {cand} | {counts['both_positive']} | {counts['f2_only']} | {counts['f5_only']} | "
            f"{counts['neither']} | {fmt(overlap)} |"
        )
    L.append("")
    L.append("Pass A values shown; `f2_f5_disagreement_review.csv` carries both passes per cell.")
    L.append("\"F2/F5 distinct\" is the share of F2-or-F5 positive items that are co-positive,")
    L.append("i.e. the rate at which the two facets fail to separate the same behaviour.")
    L.append("")
    for cand in ("A", "B", "C"):
        d = tabs[cand]["detail"]
        L.append(f"- Candidate {cand}: F2-only {d['f2_only']}, F5-only {d['f5_only']}, both {d['both_positive']}")
    L.append("")

    L.append("## Assumptions and limits")
    L.append("")
    L.append("- Items are treated as independent, which they are not: the 50 records include")
    L.append("  deliberately constructed adversarial clusters and several near-duplicate")
    L.append("  acknowledgement-push families. Clustering inflates kappa.")
    L.append("- Kappa is prevalence-sensitive. A facet both passes flag rarely cannot reach a")
    L.append("  stable kappa on 50 items, whatever the underlying agreement quality.")
    L.append("- The two passes share one annotator, so kappa cannot detect the shared-misreading")
    L.append("  failure mode that the real Part E design was meant to catch.")
    L.append("- F2 candidates are nested, so their kappas are not independent measurements and")
    L.append("  must not be compared as if they were three separate rubrics.")

    (EXP / "candidate_agreement_report.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L[:60]))
    print(f"... wrote candidate_agreement_report.md and agreement_metrics.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
