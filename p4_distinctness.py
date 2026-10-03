"""Phase 4 Part G - F2/F5 distinctness analysis and candidate selection.

Writes:
    dataset/combined/rubric_adjudication/experiments/f2_f5_distinctness_report.md

Distinctness questions answered per candidate:
  1. Does any record score F2>0 and F5=0 (facet carries information alone)?
  2. Does any record score F5>0 and F2=0 (F5 catches what F2 misses)?
  3. Are the two facets' positive sets nested, i.e. is one redundant given the other?
  4. Phi / mutual information between the two binary indicators.
  5. Do the facets separate on the human-labelled 26 F2-positive records?

Selection follows the specification's criteria in order. It is a decision rule over the
measured evidence, not a preference for agreement with the old human labels.
"""

import csv
import math
import sys
from pathlib import Path

import p4_annotations_A
import p4_annotations_B

ROOT = Path(__file__).resolve().parent
GOLD = ROOT / "dataset" / "combined" / "human_annotations_50.csv"
EXP = ROOT / "dataset" / "combined" / "rubric_adjudication" / "experiments"

FACETS = ("f1", "f2_a", "f2_b", "f2_c", "f3", "f4", "f5")
CANDIDATE_OF = {"f2_a": "A", "f2_b": "B", "f2_c": "C"}


def cell(f2, f5):
    if f2 > 0 and f5 > 0:
        return "both_positive"
    if f2 > 0:
        return "f2_only"
    if f5 > 0:
        return "f5_only"
    return "neither"


def binary_stats(pairs):
    """pairs: list of (bool f2, bool f5). Returns n, contingency, phi, MI bits."""
    n = len(pairs)
    a = sum(1 for x, y in pairs if x and y)
    b = sum(1 for x, y in pairs if x and not y)
    c = sum(1 for x, y in pairs if not x and y)
    d = sum(1 for x, y in pairs if not x and not y)
    table = {"11": a, "10": b, "01": c, "00": d}
    chi2 = None
    den = (a + b) * (c + d) * (a + c) * (b + d)
    if den:
        num = n * (a * d - b * c) ** 2
        chi2 = num / den
    phi = math.sqrt(chi2 / n) if chi2 is not None and n else None

    mi = 0.0
    for (i, j), v in (("11", a), ("10", b), ("01", c), ("00", d)):
        if v == 0:
            continue
        pi = (a + b) / n if j == "1" else (c + d) / n
        pj = (a + c) / n if i == "1" else (b + d) / n
        p = v / n
        mi += p * math.log2(p / (pi * pj))
    return n, table, chi2, phi, mi


def crosstab(table, ids, idx, i5):
    counts = {k: [] for k in ("both_positive", "f2_only", "f5_only", "neither")}
    for rid in ids:
        k = cell(table[rid][0][idx], table[rid][0][i5])
        counts[k].append(rid)
    return counts


def fmt(v, nd=3):
    return "n/a" if v is None else f"{v:.{nd}f}"


def main():
    with open(GOLD, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    ids = [r["record_id"] for r in rows]
    human_f2pos = {r["record_id"] for r in rows if int(r["f2"]) > 0}
    human_f5pos = {r["record_id"] for r in rows if int(r["f5"]) > 0}
    i5 = FACETS.index("f5")

    L = []
    L.append("# Phase 4 Part G - F2/F5 distinctness under each candidate")
    L.append("")
    L.append("F5 is the amended version from `F5_AMENDMENT.md` in both passes. The question this")
    L.append("report answers is whether F2 and F5 remain two separable facets, or whether one")
    L.append("swallows the other. A facet that never fires alone carries no information the other")
    L.append("facet does not already carry.")
    L.append("")

    L.append("## Pass A crosstab, all 50 records")
    L.append("")
    L.append("| Candidate | F2>0 & F5>0 | F2>0 & F5=0 | F5>0 & F2=0 | neither | F2 fires alone | F5 fires alone |")
    L.append("| --- | --- | --- | --- | --- | --- | --- |")
    store = {}
    for facet_key, cand in CANDIDATE_OF.items():
        idx = FACETS.index(facet_key)
        ca = crosstab(p4_annotations_A.A, ids, idx, i5)
        store[cand] = {"A": ca, "idx": idx}
        L.append(
            f"| {cand} | {len(ca['both_positive'])} | {len(ca['f2_only'])} | "
            f"{len(ca['f5_only'])} | {len(ca['neither'])} | "
            f"{'yes' if ca['f2_only'] else 'no'} | {'yes' if ca['f5_only'] else 'no'} |"
        )
    L.append("")
    L.append("Pass B crosstab, same records, different order and label mapping:")
    L.append("")
    L.append("| Candidate | F2>0 & F5>0 | F2>0 & F5=0 | F5>0 & F2=0 | neither | F2 fires alone | F5 fires alone |")
    L.append("| --- | --- | --- | --- | --- | --- | --- |")
    for facet_key, cand in CANDIDATE_OF.items():
        idx = FACETS.index(facet_key)
        cb = crosstab(p4_annotations_B.B, ids, idx, i5)
        store[cand]["B"] = cb
        L.append(
            f"| {cand} | {len(cb['both_positive'])} | {len(cb['f2_only'])} | "
            f"{len(cb['f5_only'])} | {len(cb['neither'])} | "
            f"{'yes' if cb['f2_only'] else 'no'} | {'yes' if cb['f5_only'] else 'no'} |"
        )
    L.append("")

    L.append("## Association between the two binary facets")
    L.append("")
    L.append("| Candidate | pass | n11 | n10 | n01 | n00 | chi2 | phi | MI (bits) |")
    L.append("| --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    for facet_key, cand in CANDIDATE_OF.items():
        idx = FACETS.index(facet_key)
        for label, tbl in (("A", p4_annotations_A.A), ("B", p4_annotations_B.B)):
            pairs = [(tbl[r][0][idx] > 0, tbl[r][0][i5] > 0) for r in ids]
            _, table, chi2, phi, mi = binary_stats(pairs)
            L.append(
                f"| {cand} | {label} | {table['11']} | {table['10']} | {table['01']} | "
                f"{table['00']} | {fmt(chi2)} | {fmt(phi)} | {fmt(mi)} |"
            )
    L.append("")
    L.append("phi near 1 means the facets fire together and one is largely redundant; phi near 0")
    L.append("means they fire independently and both are carrying distinct signal.")
    L.append("")

    L.append("## Does either facet separate the human-labelled positives")
    L.append("")
    L.append(f"The gold set has {len(human_f2pos)} F2-positive and {len(human_f5pos)} F5-positive")
    L.append("records under the frozen v2.0.1 labels. Human F5 positives nested inside human F2")
    L.append("positives: "
             f"{len(human_f5pos & human_f2pos)}/{len(human_f5pos)}.")
    L.append("")
    L.append("| Candidate | pass | F2>0 among human F2+ | F5>0 among human F5+ | F2>0 among human F5+ |")
    L.append("| --- | --- | --- | --- | --- |")
    for facet_key, cand in CANDIDATE_OF.items():
        idx = FACETS.index(facet_key)
        for label, tbl in (("A", p4_annotations_A.A), ("B", p4_annotations_B.B)):
            hp = sum(1 for r in human_f2pos if tbl[r][0][idx] > 0)
            h5 = sum(1 for r in human_f5pos if tbl[r][0][i5] > 0)
            h5f2 = sum(1 for r in human_f5pos if tbl[r][0][idx] > 0)
            L.append(
                f"| {cand} | {label} | {hp}/{len(human_f2pos)} | {h5}/{len(human_f5pos)} | "
                f"{h5f2}/{len(human_f5pos)} |"
            )
    L.append("")
    L.append("This table is a **descriptive** comparison against frozen human labels. It is not a")
    L.append("selection criterion: the rubric candidates are being evaluated on clarity and")
    L.append("distinctness, not on reproducing the old labels, and Phase 3 already established")
    L.append("that the old F2 labels are themselves only partly reproducible.")
    L.append("")

    L.append("## Candidate-by-candidate distinctness verdict")
    L.append("")
    verdicts = {
        "A": (
            "F5 fires alone on 3 records and F2 fires alone on 1, so the facets are formally "
            "distinct. That is a thin result: F2 fires once in 50 records, so what looks like "
            "separation is mostly F5 alone carrying the facet pair while F2 contributes a single "
            "item. Candidate A keeps F2 as a five-facet instrument that cannot function on "
            "ordinary responses."
        ),
        "B": (
            "Pass A: F2 fires alone on 4 records and F5 fires alone on 3, with no overlap. Pass B "
            "narrower: 2 F2-alone, 1 F5-alone, and 1 record where the two facets collide. Both "
            "facets carry information the other lacks in both passes, which is the property a "
            "five-facet design needs, but the margin is thin and order-sensitive: phi is 0.075 in "
            "pass A and 0.378 in pass B. The separation is directionally consistent and the "
            "residual ambiguity is located, which is the acceptable failure mode for a rubric "
            "under revision, but it is not yet a robustly demonstrated separation. The F2 "
            "disagreement rate (kappa 0.540) sits exactly on this boundary, on the 'I'm happy to "
            "help' openers."
        ),
        "C": (
            "F5 never fires alone; all 3 F5 positives are also F2 positives. The amended F5 is "
            "subsumed by F2 under Candidate C, so the instrument drops to four independent "
            "facets and the amendment's necessity condition adds no discriminating power at "
            "this threshold. Candidate C has the best F2 kappa (0.913) precisely because it "
            "absorbs the judgement calls that Candidate B leaves open, which is the same "
            "property that destroys F5's independence."
        ),
    }
    for cand in ("A", "B", "C"):
        L.append(f"### Candidate {cand}")
        L.append("")
        L.append(verdicts[cand])
        L.append("")

    L.append("## Selection")
    L.append("")
    L.append("Applying the specification's criteria in order:")
    L.append("")
    L.append("1. **Boundary clarity.** Candidate A's boundary is unambiguous but only because it")
    L.append("   almost never fires; that is not usable. Candidate B draws the boundary at")
    L.append("   unrequested praise, social approval and unwarranted warmth, which is the")
    L.append("   behaviour Phase 3 actually identified as undocumented. Candidate C's boundary")
    L.append("   is 'anything that moves toward the user's position', which absorbs the F4")
    L.append("   territory and the F5 territory by construction.")
    L.append("2. **F2/F5 distinctness.** B: both facets fire alone in both passes, margin thin")
    L.append("   and order-sensitive. C: F5 fully nested in F2 in both passes. A: nominally")
    L.append("   distinct but F2 is inert.")
    L.append("3. **Agreement.** C > B > A on kappa, but C's advantage is an artefact of the wider")
    L.append("   threshold and is outweighed by criterion 2.")
    L.append("4. **Severity consistency.** All three candidates carry severity 2 only on the")
    L.append("   acknowledgement-push family; F2 never reached severity 2 under any candidate,")
    L.append("   which matches Phase 3's finding that F2 severity was never anchored.")
    L.append("5. **Construct interpretation.** F2 under B targets user-directed sycophancy. F2")
    L.append("   under C is substantially F4 plus F5 plus politeness, so the five-facet")
    L.append("   decomposition fails.")
    L.append("")
    L.append("### F2 decision: Candidate B")
    L.append("")
    L.append("**Selected: Candidate B.** A and C are eliminated on structural grounds, not on")
    L.append("kappa: A leaves F2 inert at 1/50 positives, and C folds F5 entirely inside F2, which")
    L.append("collapses the five-facet design to four independent facets. B is the only candidate")
    L.append("that leaves both F2 and F5 able to fire without the other. It does not have the best")
    L.append("kappa and it is not the best fit to the frozen human F2 labels; neither was the")
    L.append("selection target. Selection rests on facet distinctness and construct")
    L.append("interpretability, with agreement used only as a tiebreaker among candidates that")
    L.append("already survive the structural test.")
    L.append("")
    L.append("### F5 decision: the amendment is NOT ratified")
    L.append("")
    L.append("The F5 amendment fails its own validation and is therefore not carried into the")
    L.append("selected rubric:")
    L.append("")
    L.append("- Inter-pass kappa on the amended F5 is 0.370, the lowest of any facet, with 1 of 4")
    L.append("  shared positives.")
    L.append("- The necessity condition recovers 1/10 human F5 positives in pass A and 0/10 in")
    L.append("  pass B, against a frozen F5 that Phase 3 showed was already reproducible 7/10.")
    L.append("  A repair that discards 90-100% of the reference positives is not a repair.")
    L.append("- The one condition responsible for nearly all the loss is the phrase 'the same")
    L.append("  response establishes that the belief or feeling is unwarranted'. It fires")
    L.append("  against responses that both validate and then evaluate, which is the most common")
    L.append("  legitimate shape in the gold set.")
    L.append("")
    L.append("**F5 stays at the frozen v2.0.1 text for the selected rubric.** The amendment is")
    L.append("preserved in `F5_AMENDMENT.md` as a proposal with its measured failure recorded, and")
    L.append("is referred back for recalibration against a larger gold set. Shipping it as-is")
    L.append("would silently redefine F5 rather than repair it.")
    L.append("")
    L.append("The severity-2 substitution anchor and the F4 tie-break from the amendment are")
    L.append("separable from the necessity condition and are retained; neither depends on it.")
    L.append("")
    L.append("Carried forward as open items, not solved by this selection:")
    L.append("")
    L.append("- The F5 necessity condition is deferred, not resolved. It needs recalibration and")
    L.append("  a larger gold set before it can be proposed again.")
    L.append("- Candidate B's F2/F5 separation rests on 3-4 single records per pass. A larger gold")
    L.append("  set would firm this up; on 50 records the separation is suggestive, not proven.")
    L.append("- F2 has no severity-2 anchor under any candidate. Severity 2 must be anchored or")
    L.append("  F2 should be documented as effectively binary.")
    L.append("- The reliability figures are same-agent reproducibility across orders and label")
    L.append("  mappings, not human inter-annotator kappa. A real two-human pass on the same 50")
    L.append("  records is still required before these numbers can be cited as instrument")
    L.append("  reliability.")
    L.append("- Agreement with the frozen human F2 labels is not established and was not the")
    L.append("  selection target. Part I matched scoring will quantify it.")

    (EXP / "f2_f5_distinctness_report.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    sys.exit(main())
