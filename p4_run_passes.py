"""Phase 4 - emit and validate the two blinded annotation passes.

Reads the manual annotation tables p4_annotations_A.py (pass A) and p4_annotations_B.py
(pass B), validates both against the 50 frozen gold record ids, and writes:

    dataset/combined/rubric_adjudication/experiments/annotator_A_results.csv
    dataset/combined/rubric_adjudication/experiments/annotator_B_results.csv

Each table entry is ((f1, f2_a, f2_b, f2_c, f3, f4, f5), notes) where notes maps either a
facet name to required positive evidence, or "zero_note:<facet>" to a rationale for a score
of 0 that the disagreement review needs.

Validation performed (fails loudly, writes nothing, on any violation):
  * exactly the 50 frozen record_ids from human_annotations_50.csv, no extras, no dupes
  * every score an int in {0,1,2}
  * an evidence string for every nonzero score, and no facet evidence for a zero score
  * evidence text long enough to quote a span (>= 20 chars)

Frozen inputs are never modified.
"""

import csv
import sys
from pathlib import Path

import p4_annotations_A
import p4_annotations_B

ROOT = Path(__file__).resolve().parent
GOLD = ROOT / "dataset" / "combined" / "human_annotations_50.csv"
EXP = ROOT / "dataset" / "combined" / "rubric_adjudication" / "experiments"

FACETS = ("f1", "f2_a", "f2_b", "f2_c", "f3", "f4", "f5")
ZERO = "zero_note:"


def split_notes(notes):
    ev = {k: v for k, v in notes.items() if not k.startswith(ZERO)}
    zn = {k[len(ZERO):]: v for k, v in notes.items() if k.startswith(ZERO)}
    return ev, zn


def gold_ids():
    with open(GOLD, newline="", encoding="utf-8") as fh:
        return [r["record_id"] for r in csv.DictReader(fh)]


def validate(name, table, ids):
    errs = []
    keys = list(table)
    if len(keys) != len(set(keys)):
        errs.append(f"{name}: duplicate record_id keys")
    missing = [i for i in ids if i not in table]
    extra = [k for k in keys if k not in set(ids)]
    if missing:
        errs.append(f"{name}: missing {len(missing)} record(s): {missing}")
    if extra:
        errs.append(f"{name}: {len(extra)} unknown record(s): {extra}")
    for rid in ids:
        if rid not in table:
            continue
        scores, notes = table[rid]
        ev, zn = split_notes(notes)
        if len(scores) != len(FACETS):
            errs.append(f"{name}/{rid}: expected {len(FACETS)} scores, got {len(scores)}")
            continue
        for facet, value in zip(FACETS, scores):
            if value not in (0, 1, 2):
                errs.append(f"{name}/{rid}/{facet}: score {value!r} not in {{0,1,2}}")
            if value > 0 and len(ev.get(facet, "").strip()) < 20:
                errs.append(f"{name}/{rid}/{facet}: nonzero without usable evidence")
            if value == 0 and ev.get(facet, "").strip():
                errs.append(f"{name}/{rid}/{facet}: evidence recorded for a zero score")
            if zn.get(facet, "").strip() and value != 0:
                errs.append(f"{name}/{rid}/{facet}: zero note recorded for a nonzero score")
        if set(ev) - set(FACETS):
            errs.append(f"{name}/{rid}: evidence for unknown facet(s) {sorted(set(ev) - set(FACETS))}")
        if set(zn) - set(FACETS):
            errs.append(f"{name}/{rid}: zero note for unknown facet(s) {sorted(set(zn) - set(FACETS))}")
    return errs


def write_results(path, table, ids):
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(
            ["record_id"] + list(FACETS)
            + [f"{f}_evidence" for f in FACETS]
            + [f"{f}_zero_note" for f in FACETS]
        )
        for rid in ids:
            scores, notes = table[rid]
            ev, zn = split_notes(notes)
            w.writerow(
                [rid] + list(scores)
                + [ev.get(f, "") for f in FACETS]
                + [zn.get(f, "") for f in FACETS]
            )


def main():
    ids = gold_ids()
    if len(ids) != 50:
        raise SystemExit(f"gold set is {len(ids)} rows, expected 50")
    errs = validate("A", p4_annotations_A.A, ids) + validate("B", p4_annotations_B.B, ids)
    if errs:
        print("VALIDATION FAILED")
        for e in errs:
            print("  -", e)
        return 1
    write_results(EXP / "annotator_A_results.csv", p4_annotations_A.A, ids)
    write_results(EXP / "annotator_B_results.csv", p4_annotations_B.B, ids)
    for name, table in (("A", p4_annotations_A.A), ("B", p4_annotations_B.B)):
        counts = {f: sum(table[rid][0][i] > 0 for rid in ids) for i, f in enumerate(FACETS)}
        sev2 = {f: sum(table[rid][0][i] == 2 for rid in ids) for i, f in enumerate(FACETS)}
        print(f"pass {name}: 50 records")
        print(f"  nonzero {counts}")
        print(f"  severity2 {sev2}")
    print("wrote annotator_A_results.csv, annotator_B_results.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main())
