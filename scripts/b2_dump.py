"""Batch 02 step 4: dump the 50 selected records in full for annotation.

Read-only, prints only. Chunked so each record is fully readable.
"""
import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.stdout.reconfigure(encoding="utf-8")
SEL = ROOT / "dataset" / "combined" / "llm_batch_02_selection.csv"

with SEL.open("r", encoding="utf-8-sig", newline="") as fh:
    rows = list(csv.DictReader(fh, strict=True))

print(f"total {len(rows)} records")


def dump(a, b):
    for i, r in enumerate(rows[a:b], start=a + 1):
        p = re.sub(r"\s+", " ", r["prompt"]).strip()
        rp = re.sub(r"\s+", " ", r["response"]).strip()
        print("\n" + "#" * 100)
        print(f"#{i}  {r['record_id']}")
        print(f"    source={r['source_dataset']} framing={r['framing'] or '-'}"
              f" cat={r['category'] or '-'} type={r['prompt_type']}"
              f" model={r['model'] or '(blank)'}")
        print("#" * 100)
        print(f"\nPROMPT >>> {p}\n")
        print(f"RESPONSE >>> {rp}\n")


lo = int(sys.argv[1]) if len(sys.argv) > 1 else 1
hi = int(sys.argv[2]) if len(sys.argv) > 2 else lo
dump(lo - 1, hi)
