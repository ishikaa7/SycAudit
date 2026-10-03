"""Phase 3 - write f2_human_positive_audit.csv and f2_f5_boundary_analysis.csv.

Reads human_annotations_50.csv read-only for the facet vectors and text that are being
audited; writes only into dataset/combined/rubric_adjudication/.
"""
import csv

from p2_lib import D, FACETS, rd, SOURCES
from p3_adjudication import ADJ, F5ADJ

OUT = D / "rubric_adjudication"
H = {r["record_id"]: r for r in rd(SOURCES["human_50"])}

missing = [a["rid"] for a in ADJ if a["rid"] not in H]
assert not missing, missing
assert len(ADJ) == 26, len(ADJ)

# ------------------------------------------------- f2_human_positive_audit.csv
COLS = ["idx", "record_id", "source_dataset", "human_f1", "human_f2", "human_f3",
        "human_f4", "human_f5", "apparent_reason_code", "apparent_reason",
        "current_rubric_f2", "current_rubric_rationale", "strict_reading_note",
        "reproducible_under_v201", "prompt", "response"]
REASON = {
    "A": "explicit user praise / flattery",
    "B": "generic positive politeness",
    "C": "agreement / accommodation",
    "D": "validation / reassurance",
    "E": "concession",
    "F": "other (no accommodation behaviour present)",
    "G": "unclear / no user stance to accommodate",
}
with (OUT / "f2_human_positive_audit.csv").open("w", encoding="utf-8", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(COLS)
    for a in sorted(ADJ, key=lambda x: x["idx"]):
        r = H[a["rid"]]
        w.writerow([a["idx"], a["rid"], r.get("source_dataset", "")] +
                   [r[f] for f in FACETS] +
                   [a["reason"], REASON[a["reason"]],
                    a["rubric_f2"], a["rubric_why"], a["rubric_strict"],
                    "yes" if a["rubric_f2"] > 0 else "no",
                    r.get("prompt", ""), r.get("response", "")])
print(f"wrote f2_human_positive_audit.csv ({len(ADJ)} rows)")

# ------------------------------------------------- f2_f5_boundary_analysis.csv
BCOLS = ["idx", "record_id", "human_f1", "human_f2", "human_f3", "human_f4", "human_f5",
         "apparent_reason_code", "current_rubric_f2", "closest_facet",
         "closer_F2_flattery", "closer_F5_validation", "closer_F1_agreement",
         "closer_F4_preference", "closer_none", "boundary_problem",
         "human_f5_positive", "current_rubric_f5", "f5_reproducible_under_v201",
         "f5_evidence"]
F5BY = {x["rid"]: x for x in F5ADJ}
with (OUT / "f2_f5_boundary_analysis.csv").open("w", encoding="utf-8", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(BCOLS)
    for a in sorted(ADJ, key=lambda x: x["idx"]):
        r = H[a["rid"]]
        cl = a["closer"]
        f5 = F5BY.get(a["rid"])
        w.writerow([
            a["idx"], a["rid"], r["f1"], r["f2"], r["f3"], r["f4"], r["f5"],
            a["reason"], a["rubric_f2"],
            "+".join(cl) if cl else "none",
            "yes" if "F2" in cl else "no",
            "yes" if "F5" in cl else "no",
            "yes" if "F1" in cl else "no",
            "yes" if "F4" in cl else "no",
            "yes" if "none" in cl else "no",
            a["boundary"],
            "yes" if f5 else "no",
            f5["repro_f5"] if f5 else 0,
            "yes" if (f5 and f5["repro"]) else "no",
            f5["why"] if f5 else "not a human F5 positive - not F5-audited",
        ])
print(f"wrote f2_f5_boundary_analysis.csv ({len(ADJ)} rows)")
