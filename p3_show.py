"""Phase 3 - print the 26 F2-positive cases in readable batches for adjudication."""
import json
import sys

from p2_lib import D

OUT = D / "rubric_adjudication"
f2 = json.load(open(OUT / "_f2_dump.json", encoding="utf-8"))

lo = int(sys.argv[1]) - 1
hi = int(sys.argv[2])
for i, r in enumerate(f2[lo:hi], lo + 1):
    fs = r["facets"]
    print("=" * 100)
    print(f"[{i}] {r['record_id']}   f1={fs['f1']} f2={fs['f2']} f3={fs['f3']} "
          f"f4={fs['f4']} f5={fs['f5']}")
    print("-- PROMPT --")
    print(r["prompt"][:800])
    print("-- RESPONSE --")
    print(r["response"][:3200])
