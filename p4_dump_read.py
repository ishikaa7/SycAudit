"""Phase 4 - dump the 50 gold records in a blinding-safe form for reading.

Writes prompt/response only. No facets, no metadata, no record ordering guarantee
against the source file. Used once to produce a readable transcript.
"""
import csv
import random
from pathlib import Path

SRC = Path("dataset/combined/human_annotations_50.csv")
OUT = Path("_p4_read_all.txt")

rows = list(csv.DictReader(SRC.open(encoding="utf-8-sig", newline="")))
rng = random.Random(20240417)
order = list(range(len(rows)))
rng.shuffle(order)

lines = []
for pos, i in enumerate(order, 1):
    r = rows[i]
    lines.append("=" * 96)
    lines.append(f"[{pos:02d}] {r['record_id']}")
    lines.append("PROMPT:")
    lines.append(r["prompt"])
    lines.append("RESPONSE:")
    lines.append(r["response"])

OUT.write_text("\n".join(lines), encoding="utf-8")
print(f"wrote {OUT} ({len(rows)} records, shuffled for reading)")
print("order:", [rows[i]["record_id"] for i in order])
