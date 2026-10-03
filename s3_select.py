"""TEST BATCH 01 selection.

Deterministic. seed=42. Excludes the 50 human-annotated record_ids.
NEVER reads or uses f1..f5, source_label, or any existing label for selection.
Diversity comes from stratification over source_dataset x framing x model and
from de-duplicating normalised prompts.

Writes: dataset/combined/llm_batch_01_selection.json  (the selected id list)
"""
import csv
import hashlib
import json
import random
import re
import sys
from collections import Counter, OrderedDict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.stdout.reconfigure(encoding="utf-8")

COMB = ROOT / "dataset" / "combined" / "combined_evaluator_dataset.csv"
HUM = ROOT / "dataset" / "combined" / "human_annotations_50.csv"
OUT_JSON = ROOT / "dataset" / "combined" / "llm_batch_01_selection.json"

SEED = 42
TARGET = 50
PER_SOURCE = 10
FACETS = ("f1", "f2", "f3", "f4", "f5")

# Columns that must never influence selection.
FORBIDDEN = set(FACETS) | {"source_label"}


def strict(p):
    with p.open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh, strict=True))


def norm_prompt(s):
    s = (s or "").lower()
    s = re.sub(r"\s+", " ", s)
    return s.strip()


comb = strict(COMB)
hum = strict(HUM)

print("=" * 78)
print("  TEST BATCH 01 SELECTION")
print("=" * 78)
print(f"  combined rows            : {len(comb)}")
print(f"  human-annotated rows     : {len(hum)}")
print(f"  seed                     : {SEED}")

human_ids = {r["record_id"] for r in hum}
human_prompts = {norm_prompt(r["prompt"]) for r in hum}

# Candidate pool. Deliberately only these fields are read for selection.
pool = []
for r in comb:
    if r["id"] in human_ids:
        continue
    rec = {
        "id": r["id"],
        "source_dataset": r["source_dataset"],
        "source_file": r["source_file"],
        "source_id": r["source_id"],
        "model": r["model"],
        "framing": r["framing"],
        "category": r["category"],
        "prompt": r["prompt"],
        "response": r["response"],
    }
    assert not (set(rec) & FORBIDDEN), "forbidden label column reached selection"
    pool.append(rec)
print(f"  candidate pool           : {len(pool)}  (human ids removed)")
print(f"  forbidden label columns  : {sorted(FORBIDDEN)} - never read")

# Stratify by source_dataset, then round-robin over framing buckets inside each
# source so that framing variety is maximised without any label awareness.
rng = random.Random(SEED)
by_source = OrderedDict()
for s in sorted({r["source_dataset"] for r in pool}):
    rows = [r for r in pool if r["source_dataset"] == s]
    # stable canonical ordering before any shuffle
    rows.sort(key=lambda r: r["id"])
    rng.shuffle(rows)
    buckets = OrderedDict()
    for r in rows:
        buckets.setdefault(r["framing"] or "(none)", []).append(r)
    by_source[s] = buckets

used_prompts = set(human_prompts)   # prefer prompts never seen in the human 50
selected = []
report = {"seed": SEED, "target": TARGET, "sources": {}, "relaxations": []}

for s, buckets in by_source.items():
    got = []
    # round-robin across framing buckets
    order = list(buckets)
    exhausted_all = False
    for allow_seen_prompt in (False, True):
        if len(got) >= PER_SOURCE:
            break
        while len(got) < PER_SOURCE:
            progressed = False
            for fr in order:
                b = buckets[fr]
                while b:
                    cand = b.pop(0)
                    np_ = norm_prompt(cand["prompt"])
                    if np_ in used_prompts and not allow_seen_prompt:
                        continue          # skip: keeps prompts unique/unseen
                    used_prompts.add(np_)
                    got.append(cand)
                    progressed = True
                    break
                if len(got) >= PER_SOURCE:
                    break
            if not progressed:
                exhausted_all = True
                break
        if allow_seen_prompt and len(got) < PER_SOURCE:
            report["relaxations"].append(
                f"{s}: filled {len(got)}/{PER_SOURCE} only after allowing prompts "
                f"already seen in the human 50")
    selected.extend(got)
    report["sources"][s] = {
        "target": PER_SOURCE, "selected": len(got),
        "framing": dict(Counter(r["framing"] or "(none)" for r in got)),
        "models": dict(Counter(r["model"] for r in got)),
        "categories": dict(Counter(r["category"] or "(none)" for r in got)),
    }

# top up / trim to exactly 50, deterministically
if len(selected) > TARGET:
    selected = selected[:TARGET]
elif len(selected) < TARGET:
    have = {r["id"] for r in selected}
    extra = [r for r in pool if r["id"] not in have and r["id"] not in human_ids]
    extra.sort(key=lambda r: r["id"])
    rng.shuffle(extra)
    for r in extra:
        if len(selected) >= TARGET:
            break
        np_ = norm_prompt(r["prompt"])
        if np_ in used_prompts:
            continue
        used_prompts.add(np_)
        selected.append(r)
    report["relaxations"].append(f"topped up from {len(extra)} remaining candidates")

print(f"\n  selected                : {len(selected)}")

# ------------------------------------------------------------------- validation
sel_ids = [r["id"] for r in selected]
assert len(sel_ids) == TARGET, f"expected {TARGET}, got {len(sel_ids)}"
assert len(set(sel_ids)) == TARGET, "duplicate ids"
assert not (set(sel_ids) & human_ids), "overlap with human annotations"
dupes = [p for p, n in Counter(norm_prompt(r["prompt"]) for r in selected).items() if n > 1]
print(f"  duplicate ids           : {len(sel_ids) - len(set(sel_ids))}")
print(f"  overlap with human 50   : {len(set(sel_ids) & human_ids)}")
print(f"  distinct prompts in batch: {len({norm_prompt(r['prompt']) for r in selected})}")
print(f"  intra-batch dup prompts : {len(dupes)}")
seen_human = sum(1 for r in selected if norm_prompt(r["prompt"]) in human_prompts)
print(f"  prompts also in human 50: {seen_human}")

# text fidelity vs the original combined file
comb_by_id = {r["id"]: r for r in comb}
mm = 0
for r in selected:
    o = comb_by_id[r["id"]]
    if r["prompt"] != o["prompt"] or r["response"] != o["response"]:
        mm += 1
print(f"  prompt/response drift   : {mm}")

print("\n  composition:")
for s, info in report["sources"].items():
    print(f"    {s:14s} {info['selected']:2d}/{info['target']}  framing={info['framing']}")
print(f"    models covered        : {len({r['model'] for r in selected})}")
print(f"    categories            : {dict(Counter(r['category'] or '(none)' for r in selected))}")
if report["relaxations"]:
    print("\n  relaxations:")
    for x in report["relaxations"]:
        print(f"    - {x}")

report["ids"] = sel_ids
report["prompts_distinct"] = len({norm_prompt(r["prompt"]) for r in selected})
report["models"] = sorted({r["model"] for r in selected})
OUT_JSON.write_text(json.dumps(report, indent=2), encoding="utf-8")
print(f"\n  wrote {OUT_JSON.relative_to(ROOT)}")
print(f"  combined sha256 unchanged: "
      f"{hashlib.sha256(COMB.read_bytes()).hexdigest()[:32]}")
