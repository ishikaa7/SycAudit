"""FINAL AUTOMATED INTEGRITY CHECK for the human-annotation data pipeline.

Requirement 11: for every selected record,
    original prompt  == selected prompt
    original response == selected response
compared as actual strings (exact codepoint equality), never visually.

Stages:
  A. combined_evaluator_dataset.csv  ->  human_evaluation_50.csv      (selection)
  B. human_evaluation_50.csv         ->  Annotator in-memory records   (load)
  C. Annotator save() round-trip     ->  temp CSV -> re-read           (storage)
  D. combined                        ->  temp CSV                     (storage vs original)

Writes ONLY to a temporary directory. Never creates or modifies
human_annotations_50.csv, and never modifies the source datasets.
"""
import csv
import hashlib
import io
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "annotation-tool"))
sys.stdout.reconfigure(encoding="utf-8")

COMBINED = ROOT / "dataset" / "combined" / "combined_evaluator_dataset.csv"
SAMPLE = ROOT / "dataset" / "combined" / "human_evaluation_50.csv"

SHA_COMBINED_BEFORE = hashlib.sha256(COMBINED.read_bytes()).hexdigest()
SHA_SAMPLE_BEFORE = hashlib.sha256(SAMPLE.read_bytes()).hexdigest()


def strict_read(path):
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        rdr = csv.reader(fh, delimiter=",", quotechar='"', doublequote=True,
                         strict=True, quoting=csv.QUOTE_MINIMAL)
        rows = list(rdr)
    return rows[0], rows[1:]


def strict_dicts(path):
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh, delimiter=",", quotechar='"',
                                   doublequote=True, strict=True))


ch, crows = strict_read(COMBINED)
sh, srows = strict_read(SAMPLE)
orig = {r[ch.index("id")]: r for r in crows}
ci = {n: i for i, n in enumerate(ch)}
si = {n: i for i, n in enumerate(sh)}

print("=" * 78)
print("  STAGE A - SELECTION: combined -> human_evaluation_50.csv")
print("=" * 78)
fails_a = 0
for r in srows:
    rid = r[si["id"]]
    o = orig[rid]
    for f in ("prompt", "response"):
        if o[ci[f]] != r[si[f]]:
            fails_a += 1
            print(f"  FAIL {rid} {f}: orig {len(o[ci[f]])}ch vs sel {len(r[si[f]])}ch")
print(f"  records            : {len(srows)}")
print(f"  prompt mismatches  : {sum(1 for r in srows if orig[r[si['id']]][ci['prompt']] != r[si['prompt']])}")
print(f"  response mismatches: {sum(1 for r in srows if orig[r[si['id']]][ci['response']] != r[si['response']])}")
print(f"  ragged rows        : {sum(1 for r in srows if len(r) != len(sh))}")
print(f"  RESULT             : {'PASS' if fails_a == 0 else 'FAIL'}")

print("\n" + "=" * 78)
print("  STAGE B - LOAD: human_evaluation_50.csv -> Annotator")
print("=" * 78)
import server as ann_server  # noqa: E402

ann = ann_server.Annotator(SAMPLE, Path(tempfile.gettempdir()) / "unused_never_written.csv")
fails_b = 0
for rec in ann.records:
    o = orig[rec["record_id"]]
    if rec["prompt"] != o[ci["prompt"]]:
        fails_b += 1
        print(f"  FAIL {rec['record_id']} prompt altered in load")
    if rec["response"] != o[ci["response"]]:
        fails_b += 1
        print(f"  FAIL {rec['record_id']} response altered in load")
print(f"  records loaded     : {len(ann.records)}")
print(f"  prompt/response altered : {fails_b}")
print(f"  RESULT             : {'PASS' if fails_b == 0 else 'FAIL'}")

print("\n" + "=" * 78)
print("  STAGE C/D - STORAGE ROUND-TRIP (temporary file, real output untouched)")
print("=" * 78)
tmpdir = Path(tempfile.mkdtemp(prefix="anncheck_"))
tmp_ann = tmpdir / "human_annotations_50.csv"
ann2 = ann_server.Annotator(SAMPLE, tmp_ann)

# Exercise every save() branch: new row, then overwrite of an existing row.
for rec in ann.records:
    ann2.save(rec["record_id"], {"f1": "0", "f2": "1", "f3": "2", "f4": "0", "f5": "1"})
ann2.save(ann.records[0]["record_id"], {"f1": "2", "f2": "2", "f3": "0", "f4": "1", "f5": "0"})

written = strict_dicts(tmp_ann)
whead = list(written[0].keys())
print(f"  rows written       : {len(written)}")
print(f"  columns            : {whead}")

# Structural validity of the produced CSV
th, trows = strict_read(tmp_ann)
print(f"  re-parse ragged    : {sum(1 for r in trows if len(r) != len(th))}")
raw = tmp_ann.read_bytes()
print(f"  CSV well-formed    : strict RFC4180 parse OK ({len(raw):,} bytes)")

fails_cd = 0
seen = set()
for row in written:
    rid = row["record_id"]
    seen.add(rid)
    o = orig[rid]
    for f in ("prompt", "response"):
        if row[f] != o[ci[f]]:
            fails_cd += 1
            print(f"  FAIL {rid} {f}: orig {len(o[ci[f]])}ch vs stored {len(row[f])}ch")
print(f"  distinct ids stored: {len(seen)} / {len(ann.records)}")
print(f"  prompt/response mismatches vs ORIGINAL : {fails_cd}")
print(f"  upsert preserved 50 rows (no data loss) : {len(written) == len(ann.records)}")
print(f"  RESULT             : {'PASS' if fails_cd == 0 and len(written) == len(ann.records) else 'FAIL'}")

print("\n" + "=" * 78)
print("  PER-RECORD VERDICT TABLE (prompt / response vs original)")
print("=" * 78)
print(f"  {'record_id':44s} {'p_orig':>7s} {'p_ok':>5s} {'r_orig':>7s} {'r_ok':>5s} {'quotes':>7s} {'nls':>5s} {'commas':>7s}")
stored_by_id = {r["record_id"]: r for r in written}
allok = 0
for r in srows:
    rid = r[si["id"]]
    o = orig[rid]
    s = stored_by_id.get(rid)
    pok = (r[si["prompt"]] == o[ci["prompt"]]) and (s and s["prompt"] == o[ci["prompt"]])
    rok = (r[si["response"]] == o[ci["response"]]) and (s and s["response"] == o[ci["response"]])
    blob = r[si["prompt"]] + r[si["response"]]
    if pok and rok:
        allok += 1
    print(f"  {rid:44s} {len(o[ci['prompt']]):7d} {'OK' if pok else 'BAD':>5s} "
          f"{len(o[ci['response']]):7d} {'OK' if rok else 'BAD':>5s} "
          f"{blob.count(chr(34)):7d} {blob.count(chr(10)):5d} {blob.count(','):7d}")
print(f"\n  fully intact records: {allok}/{len(srows)}")

print("\n" + "=" * 78)
print("  SOURCE DATASET IMMUTABILITY")
print("=" * 78)
sha_c_after = hashlib.sha256(COMBINED.read_bytes()).hexdigest()
sha_s_after = hashlib.sha256(SAMPLE.read_bytes()).hexdigest()
print(f"  combined_evaluator_dataset.csv unchanged : {SHA_COMBINED_BEFORE == sha_c_after}  ({sha_c_after[:32]})")
print(f"  human_evaluation_50.csv        unchanged : {SHA_SAMPLE_BEFORE == sha_s_after}  ({sha_s_after[:32]})")
real_ann = ROOT / "dataset" / "combined" / "human_annotations_50.csv"
print(f"  human_annotations_50.csv exists (must be False): {real_ann.exists()}")
print(f"  real annotations file untouched : {not real_ann.exists()}")

# tidy temp
import shutil
shutil.rmtree(tmpdir, ignore_errors=True)

total_fail = fails_a + fails_b + fails_cd
print("\n" + "=" * 78)
print(f"  OVERALL: {total_fail} integrity failure(s) across {len(srows)} records")
print("=" * 78)
sys.exit(1 if total_fail else 0)