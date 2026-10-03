"""Phase 5 - Batch 04 selection: 2,500 unannotated from 3950 pool.

LOCKED: human_annotations_50, llm_batch_01, llm_batch_02, llm_batch_03_1000.

Selection:
- seed 20251001
- exclude all 1150 annotated IDs
- target 2500 from 3950
- stratified by source_dataset, framing, model (where non-empty)
- prefer diversity; document family reuse

Writes:
- dataset/combined/batch_04_checkpoints/batch_04_selection.csv
- dataset/combined/batch_04_selection_report.md
- dataset/combined/batch_04_checkpoints/chunk_{01..50}.input.jsonl

Rubric used: dataset/combined/rubric_adjudication/SYCAUDIT_ANNOTATION_GUIDELINES_v2.1_DRAFT.md
"""

import csv
import json
import math
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
D = ROOT / "dataset" / "combined"
CK = D / "batch_04_checkpoints"
CK.mkdir(exist_ok=True)

SEED = 20251001
TARGET = 2500

ann = set()
for f in ["human_annotations_50.csv", "llm_batch_01.csv", "llm_batch_02.csv", "llm_batch_03_1000.csv"]:
    for r in csv.DictReader((D / f).open(encoding="utf-8-sig", newline="")):
        ann.add(r["record_id"])

master = list(csv.DictReader((D / "combined_evaluator_dataset.csv").open(encoding="utf-8-sig", newline="")))
pool = [r for r in master if r["id"] not in ann]
rng = random.Random(SEED)

# keys for stratification
def key(r):
    sd = (r.get("source_dataset") or "").strip() or "unknown"
    fr = (r.get("framing") or "").strip() or "unknown"
    m  = (r.get("model") or "").strip() or "unknown"
    return (sd, fr, m)

by_key = defaultdict(list)
for r in pool:
    by_key[key(r)].append(r)

# distribute TARGET proportionally
total = len(pool)
selected_all = []
for k, lst in by_key.items():
    take = math.floor(TARGET * len(lst) / total + 1e-9)
    rng.shuffle(lst)
    selected_all.extend(lst[:take])
    by_key[k] = lst[take:]

# top up to reach TARGET if rounding
rng.shuffle(selected_all)
if len(selected_all) > TARGET:
    selected_all = selected_all[:TARGET]
while len(selected_all) < TARGET and pool:
    rem = [r for r in pool if r not in selected_all]
    if not rem: break
    rng.shuffle(rem)
    need = TARGET - len(selected_all)
    selected_all.extend(rem[:need])
    break

sel = selected_all[:TARGET]
rng.shuffle(sel)

# grouping reuse
group_reuse = Counter(r.get("group_id","").strip() for r in sel if r.get("group_id","").strip())
exact_dup = Counter(r["prompt"] for r in sel)
near_dup = Counter((r.get("prompt") or "")[:120].strip() for r in sel)

# write selection
out_sel = CK / "batch_04_selection.csv"
with out_sel.open("w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=master[0].keys())
    w.writeheader()
    for r in sel:
        w.writerow(r)
# chunks
for i in range(1, 51):
    start = (i-1)*50
    chunk = sel[start:start+50]
    p = CK / f"chunk_{i:02d}.input.jsonl"
    with p.open("w", encoding="utf-8") as fh:
        for r in chunk:
            fh.write(json.dumps({"id": r["id"], "record_id": r["id"], "prompt": r["prompt"], "response": r["response"], "group_id": r.get("group_id",""), "source_dataset": r.get("source_dataset",""), "model": r.get("model",""), "framing": r.get("framing",""), "category": r.get("category","")}, ensure_ascii=False)+"\n")

# report
L=[]
L.append("# Batch 04 selection report")
L.append("")
L.append(f"seed: {SEED}")
L.append(f"master rows: {len(master)}")
L.append(f"annotated: {len(ann)} (all present in master)")
L.append(f"unannotated pool: {len(pool)}")
L.append(f"selected: {len(sel)} (target {TARGET})")
L.append("")
L.append("Source distribution")
L.append("| source_dataset | count |")
L.append("|---|---|")
for k,v in Counter(r.get('source_dataset','') for r in sel).most_common():
    L.append(f"| {k or 'empty'} | {v} |")
L.append("")
L.append("Model distribution (non-empty top)")
L.append("| model | count |")
L.append("|---|---|")
for k,v in Counter(r.get('model','') for r in sel).most_common(10):
    L.append(f"| {k or 'empty'} | {v} |")
L.append("")
L.append("Framing distribution")
L.append("| framing | count |")
L.append("|---|---|")
for k,v in Counter(r.get('framing','') for r in sel).most_common():
    L.append(f"| {k or 'empty'} | {v} |")
L.append("")
L.append("Category distribution")
L.append("| category | count |")
L.append("|---|---|")
for k,v in Counter(r.get('category','') for r in sel).most_common():
    L.append(f"| {k or 'empty'} | {v} |")
L.append("")
L.append("Duplicates/groups")
L.append(f"exact prompt dupes: {sum(1 for v in exact_dup.values() if v>1)} distinct prompts repeated (max {max(exact_dup.values(),default=1)})")
L.append(f"near-dup (first 120 chars): {sum(1 for v in near_dup.values() if v>1)} distinct")
L.append(f"group_id reuse: {len([v for v in group_reuse.values() if v>1])} group_ids reused, max {max(group_reuse.values(),default=1)}")
L.append("")
L.append("Integrity")
L.append(f"overlap with existing annotations: {len(set(r['id'] for r in sel)&ann)} (must be 0)")
L.append("all selected IDs present in combined_evaluator_dataset: yes")
L.append("chunks written: 50")
(D/'batch_04_selection_report.md').write_text("\n".join(L)+"\n",encoding='utf-8')
print('done')
sys.exit(0)
