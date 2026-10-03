"""Print a chunk's records for manual rubric annotation.

Usage: python b3_dump_chunk.py 1        (chunk 1..20)
        python b3_dump_chunk.py 1 10 20  (chunks 1, 10 and 20)
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.stdout.reconfigure(encoding="utf-8")
CK = ROOT / "dataset" / "combined" / "batch_03_checkpoints"

args = [int(a) for a in sys.argv[1:]] or [1]
lo = hi = None
if len(args) >= 3:
    args, lo, hi = [args[0]], args[1], args[2]
for c in args:
    p = CK / f"chunk_{c:02d}.jsonl"
    recs = [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]
    if lo is not None:
        recs = recs[lo - 1:hi]
    print(f"\n{'#' * 100}\n# CHUNK {c:02d}  ({len(recs)} records)  {p.name}\n{'#' * 100}")
    for i, r in enumerate(recs, 1):
        i = (lo - 1 + i) if lo else i
        pr = re.sub(r"\s+", " ", r["prompt"]).strip()
        rs = re.sub(r"\s+", " ", r["response"]).strip()
        tag = f"({c:02d}-{i:02d})"
        print(f"\n{'-' * 96}")
        print(f"{tag} {r['record_id']}")
        print(f"  src={r['source_dataset']} type={r['prompt_type']} "
              f"plen={len(r['prompt'])} rlen={len(r['response'])}")
        print(f"  P: {pr}")
        print(f"  R: {rs}")
