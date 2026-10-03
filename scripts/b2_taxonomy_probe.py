"""Batch 02 step 2: sample prompts per source/framing to design a behavior-based
prompt-type taxonomy.

Read-only. Taxonomy will key off observable prompt TEXT only, never source_label.
"""
import csv
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.stdout.reconfigure(encoding="utf-8")
D = ROOT / "dataset" / "combined"


def strict(p):
    with p.open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh, strict=True))


comb = strict(D / "combined_evaluator_dataset.csv")
used = {r["record_id"] for r in strict(D / "human_annotations_50.csv")}
used |= {r["record_id"] for r in strict(D / "llm_batch_01.csv")}
pool = [r for r in comb if r["id"] not in used]


def show(title, rows, n=14, width=150):
    print("\n" + "=" * width)
    print(title)
    print("=" * width)
    for r in rows[:n]:
        p = re.sub(r"\s+", " ", r["prompt"]).strip()
        print(f"\n[{r['source_dataset']}|{r['framing'] or '-'}|{r['category'] or '-'}]"
              f" model={r['model'][:26]}")
        print(f"  {p[:width - 4]}")


by_src = defaultdict(list)
for r in pool:
    by_src[(r["source_dataset"], r["framing"] or "-")].append(r)

for key in sorted(by_src):
    rows = sorted(by_src[key], key=lambda r: r["id"])
    step = max(1, len(rows) // 14)
    show(f"SOURCE {key[0]}  framing={key[1]}  (n={len(rows)})", rows[::step])

# what do the multi-record prompts look like? (prompt reused across models)
cnt = Counter(r["prompt"].strip().lower() for r in pool)
top = [k for k, v in cnt.most_common(8) if v > 1]
print("\n" + "=" * 150)
print("PROMPTS APPEARING MULTIPLE TIMES IN POOL (same question, different models)")
print("=" * 150)
for t in top[:6]:
    ex = next(r for r in pool if r["prompt"].strip().lower() == t)
    print(f"\n[{ex['source_dataset']}|{ex['framing'] or '-'}] x{cnt[t]} models :: "
          f"{re.sub(chr(92)+'s+', ' ', ex['prompt'])[:130]}")
    sibs = [r for r in pool if r["prompt"].strip().lower() == t]
    print(f"    models: {sorted({s['model'].split('/')[-1][:18] for s in sibs})}")
