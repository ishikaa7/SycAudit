"""Batch 03 Chunk 01 PILOT - full 13-point QC for rubric v2.0.1."""
import csv
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parent
D = ROOT / "dataset" / "combined"
CK = D / "batch_03_checkpoints"
F = ("f1", "f2", "f3", "f4", "f5")
BEFORE = Path(sys.argv[1]) if len(sys.argv) > 1 else None

MASTER = D / "combined_evaluator_dataset.csv"
SEL = D / "llm_batch_03_1000_selection.csv"
HUMAN = D / "human_annotations_50.csv"
B01 = D / "llm_batch_01.csv"
B02 = D / "llm_batch_02.csv"

EXPECTED_MASTER = "3901aa493f786a21"
EXPECTED_SEL = "36ba347d2ce8d2b3"


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def ids(p):
    return [r["record_id"] for r in csv.DictReader(p.open(encoding="utf-8-sig", newline=""))]


def load_jsonl(p):
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]


objs = load_jsonl(CK / "chunk_01.jsonl")
sel_rows = list(csv.DictReader(SEL.open(encoding="utf-8-sig", newline="")))
human, b01, b02 = set(ids(HUMAN)), set(ids(B01)), set(ids(B02))
ck = [o["record_id"] for o in objs]

results = []


def chk(n, desc, ok, detail=""):
    results.append((n, desc, bool(ok), detail))


# 1
chk(1, "Exactly 50 records remain", len(objs) == 50, f"n={len(objs)}")
# 2
order_ok = ck == [r["record_id"] for r in sel_rows[:50]]
uniq = len(set(ck)) == 50
chk(2, "IDs and ordering unchanged vs locked selection", order_ok and uniq,
    f"order={order_ok} unique={uniq}")
# 3-5
chk(3, "No overlap with human_annotations_50.csv", not (set(ck) & human), f"n_overlap={len(set(ck) & human)}")
chk(4, "No overlap with Batch 01", not (set(ck) & b01), f"n_overlap={len(set(ck) & b01)}")
chk(5, "No overlap with Batch 02", not (set(ck) & b02), f"n_overlap={len(set(ck) & b02)}")
# 6
badval = [(o["record_id"], f) for o in objs for f in F
          if type(o[f]) is not int or o[f] not in (0, 1, 2)]
chk(6, "Every F1-F5 value is an integer in {0,1,2}", not badval, f"violations={badval[:5]}")
# 7
badev = [(o["record_id"], f) for o in objs for f in F
         if o[f] != 0 and not str(o[f + "_evidence"]).strip()]
allemp = [(o["record_id"], f) for o in objs for f in F
          if not str(o[f + "_evidence"]).strip()]
chk(7, "Every nonzero score has non-empty evidence", not badev,
    f"nonzero_missing={badev[:5]} any_missing={len(allemp)}")
# 8
# Leakage means the *decision* referenced dataset metadata. Detect concrete metadata
# VALUES, not English words: "the model's own reasoning" and "complex policy framing"
# are legitimate prose. Check for real enum values, dataset tags, source paths,
# record-id prefixes, and metadata field names used as structured references.
FORBIDDEN_FIELDS = {"source_dataset", "source_file", "source_id", "model", "category",
                     "framing", "temperature", "seed", "sample_idx", "is_paper1_bridge",
                     "source_label", "gpt4o_label", "gold", "prompt_type", "response_lenband"}
leak_fields = sorted({k for o in objs for k in o} & FORBIDDEN_FIELDS)

# real metadata values present in the locked selection's metadata columns
meta_values = set()
for r in sel_rows[:50]:
    for k in ("source_dataset", "source_file", "model", "category", "prompt_type"):
        v = (r.get(k) or "").strip()
        if v:
            meta_values.add(v.lower())
# framing enum + dataset tags
meta_values |= {"authority", "leading", "neutral", "opinion", "original", "unframed",
                "camilablank", "ds1", "ds2", "ds3", "schis02", "s1_ablation_subset",
                "false-premise-health"}
# drop values that are also ordinary answer words appearing in the item text
BENIGN = {"neutral", "opinion", "original", "authority", "leading"}
meta_values -= BENIGN

ev_hits = []
for o in objs:
    rid_short = o["record_id"].split("__")[-1]
    for f in F:
        e = o[f + "_evidence"]
        low = e.lower()
        if rid_short.lower() in low:
            ev_hits.append((o["record_id"], f, "record_id", rid_short))
        for v in meta_values:
            if re.search(rf"(?<![a-z0-9_]){re.escape(v)}(?![a-z0-9_])", low):
                ev_hits.append((o["record_id"], f, "metadata_value", v))
        if re.search(r"dataset/(sycophancy|syco|extracted|selected)/", low):
            ev_hits.append((o["record_id"], f, "source_path", "dataset/..."))
chk(8, "No metadata/source_label leakage into annotation decisions",
    not leak_fields and not ev_hits,
    f"fields={leak_fields} evidence_hits={ev_hits[:5]} (n={len(ev_hits)})")
# 9
m = sha(MASTER)
chk(9, "Master dataset hash unchanged", m.startswith(EXPECTED_MASTER), f"{m[:16]}")
# 10
s = sha(SEL)
chk(10, "Locked Batch 03 selection hash unchanged", s.startswith(EXPECTED_SEL), f"{s[:16]}")
# 11
if BEFORE and BEFORE.exists():
    b = {o["record_id"]: o for o in load_jsonl(BEFORE)}
    a = {o["record_id"]: o for o in objs}
    diffs = []
    for rid in b:
        for k in b[rid]:
            if b[rid][k] != a[rid][k]:
                diffs.append((rid, k, b[rid][k], a[rid][k]))
    score_diffs = [(r, k, ov, nv) for r, k, ov, nv in diffs if k in F]
    expected = {
        ("sycaudit__camilablank_b90878c490fce4", "f3", 2, 0),
        ("sycaudit__camilablank_029da7ba6e0b4f", "f3", 2, 0),
    }
    got = {(r, k, ov, nv) for r, k, ov, nv in score_diffs}
    only_evidence = all(k.endswith("_evidence") for r, k, ov, nv in diffs if k not in F)
    chk(11, "Only the two intended F3 values changed", got == expected and only_evidence,
        f"score_diffs={sorted(got)} evidence_only={only_evidence}")
else:
    chk(11, "Only the two intended F3 values changed", False, "no baseline snapshot supplied")
# 12
EXPECTED_CHUNKS = {f"chunk_{i:02d}" for i in range(2, 21)}
found, touched = set(), set()
for p in sorted(CK.glob("chunk_*.jsonl")):
    stem = p.stem
    if stem in EXPECTED_CHUNKS:
        found.add(stem)
        recs = load_jsonl(p)
        # an input manifest record has no facet keys; an annotated record does
        if any(any(k in F for k in r) for r in recs):
            touched.add(stem)
manifest = CK / "manifest.json"
chunk_inputs_intact = len(found) == 19
chk(12, "No Chunk 02-20 files processed or annotated", not touched and chunk_inputs_intact,
    f"present={len(found)}/19 annotated={sorted(touched) or 'none'}")
# 13
merged = [p.name for p in D.glob("*batch_03*") if p.suffix == ".csv"
          and "selection" not in p.name]
big = []
for p in D.glob("*.csv"):
    if "batch_03" in p.name and "selection" not in p.name:
        n = len(list(csv.DictReader(p.open(encoding="utf-8-sig", newline=""))))
        if n >= 900:
            big.append((p.name, n))
chk(13, "No final 1000-row merged file created", not big and not merged,
    f"batch03_outputs={merged} large={big}")

print("=" * 78)
print("BATCH 03 CHUNK 01 PILOT QC - rubric v2.0.1")
print("=" * 78)
for n, desc, ok, detail in results:
    print(f"[{'PASS' if ok else 'FAIL'}] {n:>2}. {desc}")
    if detail:
        print(f"          {detail}")
npass = sum(1 for *_, ok, _ in results if ok)
print("-" * 78)
print(f"RESULT: {npass} passed, {len(results) - npass} failed (of {len(results)})")

print()
print("F3 DISTRIBUTION - before vs after")
if BEFORE and BEFORE.exists():
    b = load_jsonl(BEFORE)
    cb, ca = Counter(o["f3"] for o in b), Counter(o["f3"] for o in objs)
    print(f"{'value':<8}{'before':>10}{'after':>10}{'delta':>10}")
    for k in (0, 1, 2):
        print(f"{k:<8}{cb[k]:>10}{ca[k]:>10}{ca[k] - cb[k]:>+10}")
    print(f"{'nonzero':<8}{cb[1]+cb[2]:>10}{ca[1]+ca[2]:>10}{ca[1]+ca[2]-(cb[1]+cb[2]):>+10}")
else:
    print("(no baseline)")

print()
print("FULL FACET DISTRIBUTION (after)")
print(f"{'facet':<8}{'0':>6}{'1':>6}{'2':>6}{'nonzero':>10}{'mean':>8}")
for f in F:
    c = Counter(o[f] for o in objs)
    nz = c[1] + c[2]
    print(f"{f:<8}{c[0]:>6}{c[1]:>6}{c[2]:>6}{nz:>10}{sum(o[f] for o in objs)/len(objs):>8.3f}")
print(f"{'all-zero':<8}{sum(1 for o in objs if all(o[f] == 0 for f in F)):>6}")
for t in (1, 2, 3, 4, 5):
    print(f">={t} nonzero: {sum(1 for o in objs if sum(o[f] > 0 for f in F) >= t)}")

print()
print("HASHES")
for name, p in [("master", MASTER), ("human", HUMAN), ("batch01", B01), ("batch02", B02), ("selection", SEL)]:
    print(f"  {name:<11}{sha(p)[:16]}  {p.name}")
sys.exit(0 if npass == len(results) else 1)
