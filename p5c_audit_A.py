"""Read-only audit of Phase 5C Variant A accounting. Makes NO API calls."""

import collections
import csv
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent
D = ROOT / "dataset" / "combined"
B = D / "qwen_calibration" / "prompt_variant_A"

recs = [json.loads(l) for l in (B / "annotations.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
perf = json.loads((B / "performance.json").read_text(encoding="utf-8"))

cal = {r["record_id"] for r in csv.DictReader(
    (D / "human_annotations_50.csv").open(encoding="utf-8-sig", newline=""))}

print("=" * 70)
print("ANNOTATIONS FILE")
print("=" * 70)
print(f"records on disk            : {len(recs)}")
print(f"unique record_ids          : {len(set(r['record_id'] for r in recs))}")
print(f"all within frozen calib 50 : {set(r['record_id'] for r in recs) <= cal}")
print(f"timestamp field present    : "
      f"{[k for k in recs[0] if 'time' in k or 'date' in k] or 'NONE'}")
print(f"distinct model values      : {set(r.get('model') for r in recs)}")
print(f"distinct provider values   : {set(r.get('provider') for r in recs)}")
print(f"distinct rubric_version    : {set(r.get('rubric_version') for r in recs)}")
print(f"distinct variant           : {set(r.get('variant') for r in recs)}")
print(f"attempt count distribution : "
      f"{dict(sorted(collections.Counter(r.get('attempts') for r in recs).items()))}")
print(f"sum(attempts) over records : {sum(r.get('attempts', 0) for r in recs)}")
print(f"latency_s recorded         : {sum(1 for r in recs if 'latency_s' in r)}/{len(recs)}")

print()
print("=" * 70)
print("PERFORMANCE COUNTERS")
print("=" * 70)
for k in ("total_requests", "successful_requests", "failed_records", "retries",
          "transport_failures", "http_429", "http_402", "http_5xx", "timeout",
          "malformed_json", "validation_failures", "terminated_on_402"):
    print(f"  {k:<22} {perf.get(k)}")

print()
print("=" * 70)
print("INTERNAL CONSISTENCY")
print("=" * 70)
succ = perf["successful_requests"]
tf = perf["transport_failures"]
mal = perf["malformed_json"]
val = perf["validation_failures"]
tot = perf["total_requests"]
print(f"  successful + failures      = {succ} + ({tf}+{mal}+{val}) = {succ + tf + mal + val}")
print(f"  total_requests             = {tot}")
print(f"  consistent                 : {succ + tf + mal + val == tot}")
print(f"  failed_records             = {perf['failed_records']}")
print(f"  retries                    = {perf['retries']}")
print(f"  retries vs total-requests  : {perf['retries']} / {tot} "
      f"(ratio {perf['retries']/tot:.2f})")
print(f"  http_402 counter           = {perf.get('http_402')}  <-- expected 1")
print(f"  terminated_on_402          = {perf.get('terminated_on_402')}")

print()
print("=" * 70)
print("REQUESTS IMPLIED BY PER-RECORD attempt COUNTS")
print("=" * 70)
by_att = collections.Counter(r.get("attempts") for r in recs)
implied = sum(a * c for a, c in by_att.items())
print(f"  records needing >1 attempt : "
      f"{sum(c for a, c in by_att.items() if a > 1)}")
print(f"  HTTP calls those consumed  : {implied}")
print(f"  total_requests counter     : {tot}")
print(f"  gap (requests that produced no record at all): {tot - implied}")

print()
print("=" * 70)
print("PER-RECORD LEDGER (order as written to disk)")
print("=" * 70)
print(f"{'#':>3}  {'record_id':<36} {'try':>4} {'lat_s':>7}")
for i, r in enumerate(recs, 1):
    print(f"{i:>3}  {r['record_id']:<36} {r.get('attempts'):>4} {r.get('latency_s'):>7}")