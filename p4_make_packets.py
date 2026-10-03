"""Phase 4 - build blinded annotation packets.

Emits, per annotator, one packet per blinded rubric label. Records are shuffled
independently per annotator. The packet contains ONLY an opaque slot id, the
prompt, and the response.

Blinding guarantees, enforced by construction:
  - no facet labels (human or LLM)
  - no source_dataset / source_id / model / category / framing / group_id
  - no candidate name (only the blinded RUBRIC_X/Y/Z label)
  - no Phase 3 adjudication conclusion, reason code, or boundary note
  - record order differs per annotator
  - the slot id is a fresh index, not the record_id

The mapping (slot -> record_id) and the rubric-label -> candidate mapping are
written to SEPARATE files that are not part of any packet.
"""
import csv
import json
import random
from pathlib import Path

from p2_lib import D, rd

EXP = D / "rubric_adjudication" / "experiments"
SRC = D / "human_annotations_50.csv"

# Seeded so the experiment is reproducible. Two distinct seeds -> two distinct orders.
SEEDS = {"A": 771401, "B": 339052}

# Blinded rubric labels. The candidate each maps to is NOT recorded in the packet.
BLINDED = ["RUBRIC_X", "RUBRIC_Y", "RUBRIC_Z"]

rows = rd(SRC)
assert len(rows) == 50, len(rows)

# Sanity: the packet must not inherit any label column.
FORBIDDEN = ["f1", "f2", "f3", "f4", "f5", "record_id", "source_dataset", "source_id",
             "model", "framing", "category", "group_id", "original_id", "annotator",
             "annotated_at_utc", "record_index"]

mapping = {
    "blinding": {
        "seed_annotator_A": SEEDS["A"],
        "seed_annotator_B": SEEDS["B"],
        "blinded_labels": BLINDED,
        "packet_columns": ["slot_id", "rubric_label", "prompt", "response"],
        "note": ("Slots are a fresh 1..50 index per annotator. Order is shuffled "
                 "independently per annotator. No packet file contains any label, "
                 "metadata field, candidate name, or adjudication conclusion."),
    },
    "slot_to_record": {"annotator_A": {}, "annotator_B": {}},
    "rubric_to_candidate": {"annotator_A": {}, "annotator_B": {}},
    "candidate_rubric_file": {},
    "records_included": len(rows),
    "source_file_sha256_note": "prompts and responses copied byte-for-byte from "
                               "human_annotations_50.csv; no normalization applied",
}

CANDS = ["A", "B", "C"]

for ann in ("A", "B"):
    rng = random.Random(SEEDS[ann])
    order = list(rows)
    rng.shuffle(order)
    slot_to_rec = {}
    for slot, r in enumerate(order, 1):
        slot_to_rec[f"S{slot:02d}"] = r["record_id"]
    mapping["slot_to_record"][f"annotator_{ann}"] = slot_to_rec

    # Counterbalance the rubric->candidate mapping across annotators so neither
    # annotator systematically sees candidates in the same labelled position.
    if ann == "A":
        perm = {"RUBRIC_X": "A", "RUBRIC_Y": "B", "RUBRIC_Z": "C"}
    else:
        perm = {"RUBRIC_X": "C", "RUBRIC_Y": "A", "RUBRIC_Z": "B"}
    mapping["rubric_to_candidate"][f"annotator_{ann}"] = perm

    for label in BLINDED:
        cand = perm[label]
        mapping["candidate_rubric_file"][cand] = str(
            EXP / f"F2_CANDIDATE_{cand}.md").replace(str(D.parent.parent) + "\\", "")

        out = EXP / f"packet_annotator_{ann}_{label}.csv"
        with out.open("w", encoding="utf-8", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["slot_id", "rubric_label", "prompt", "response"])
            for slot, r in enumerate(order, 1):
                w.writerow([f"S{slot:02d}", label, r["prompt"], r["response"]])
        print(f"wrote {out.name}: 50 records, blinded as {label}")

# Verify no forbidden token appears in any packet column value.
print()
leaks = []
for ann in ("A", "B"):
    for label in BLINDED:
        p = EXP / f"packet_annotator_{ann}_{label}.csv"
        with p.open(encoding="utf-8", newline="") as fh:
            rr = list(csv.DictReader(fh))
        assert len(rr) == 50, (p, len(rr))
        cols = set(rr[0].keys())
        assert not (cols & set(FORBIDDEN)), (p, cols & set(FORBIDDEN))
        for row in rr:
            for col, v in row.items():
                if col in ("prompt", "response"):
                    continue
                if any(f in v for f in FORBIDDEN):
                    leaks.append((p.name, col, v))
                if "Candidate" in v or "candidate" in v:
                    leaks.append((p.name, col, v))
print("packet columns:", sorted(rr[0].keys()))
print("leaks found:", leaks or "none")

# Confirm orders actually differ between annotators.
def record_order(ann, label):
    """Presentation order as the annotator sees it, resolved via the mapping file."""
    m = json.loads((EXP / "annotator_mapping.json").read_text(encoding="utf-8")) \
        if (EXP / "annotator_mapping.json").exists() else None
    with (EXP / f"packet_annotator_{ann}_{label}.csv").open(encoding="utf-8", newline="") as fh:
        slots = [r["slot_id"] for r in csv.DictReader(fh)]
    if m:
        s2r = m["slot_to_record"][f"annotator_{ann}"]
        return [s2r[s] for s in slots]
    return slots

oa = record_order("A", "RUBRIC_X")
ob = record_order("B", "RUBRIC_X")
print("A sees first 6 records:", oa[:6])
print("B sees first 6 records:", ob[:6])
print("presentation order identical across annotators:", oa == ob)
print("same record set:", set(oa) == set(ob))
print("overlap in first 10 positions:", len(set(oa[:10]) & set(ob[:10])), "/ 10")

(EXP / "annotator_mapping.json").write_text(
    json.dumps(mapping, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print()
print(f"wrote {(EXP / 'annotator_mapping.json').name}")
