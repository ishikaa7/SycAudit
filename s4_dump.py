"""Readable dump of the 50 selected TEST BATCH 01 records for LLM annotation."""
import csv
import json
import sys
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.stdout.reconfigure(encoding="utf-8")
COMB = ROOT / "dataset" / "combined" / "combined_evaluator_dataset.csv"
SEL = ROOT / "dataset" / "combined" / "llm_batch_01_selection.json"

ids = json.loads(SEL.read_text(encoding="utf-8"))["ids"]
with COMB.open("r", encoding="utf-8-sig", newline="") as fh:
    rows = {r["id"]: r for r in csv.DictReader(fh, strict=True)}

a = int(sys.argv[1]) if len(sys.argv) > 1 else 1
b = int(sys.argv[2]) if len(sys.argv) > 2 else a
cap = int(sys.argv[3]) if len(sys.argv) > 3 else 2600

for n in range(a, b + 1):
    rid = ids[n - 1]
    r = rows[rid]
    print("=" * 112)
    print(f"[{n:02d}] {rid}")
    print(f"     src={r['source_dataset']} framing={r['framing']!r} model={r['model']}")
    print(f"     PROMPT ({len(r['prompt'])} ch):")
    for ln in textwrap.wrap(r["prompt"], 104):
        print(f"       | {ln}")
    resp = r["response"]
    print(f"     RESPONSE ({len(resp)} ch):")
    body = resp if len(resp) <= cap else resp[:cap]
    for ln in textwrap.wrap(body, 104):
        print(f"       | {ln}")
    if len(resp) > cap:
        print(f"       | ...[+{len(resp)-cap} ch of {len(resp)} total; tail: "
              f"{resp[-200:]!r}]")