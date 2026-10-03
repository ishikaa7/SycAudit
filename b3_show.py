import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
n = int(sys.argv[1]) if len(sys.argv) > 1 else 2
start = int(sys.argv[2]) if len(sys.argv) > 2 else 1
end = int(sys.argv[3]) if len(sys.argv) > 3 else 10
width = int(sys.argv[4]) if len(sys.argv) > 4 else 1800

recs = [json.loads(l) for l in
        Path(f"dataset/combined/batch_03_checkpoints/chunk_{n:02d}.jsonl")
        .read_text(encoding="utf-8").splitlines() if l.strip()]

print(f"chunk_{n:02d}: {len(recs)} records; showing {start}..{end}")
for i, r in enumerate(recs, 1):
    if not (start <= i <= end):
        continue
    print("=" * 78)
    print(f"[{i}] {r['record_id']}")
    print("--- PROMPT ---")
    print(r["prompt"][:width])
    print("--- RESPONSE ---")
    print(r["response"][:width])
