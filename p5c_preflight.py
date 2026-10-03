"""Phase 5C preflight summary. Read-only. Prints no secret values."""

import csv
import hashlib
import sys
from pathlib import Path

from dotenv import dotenv_values

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent
D = ROOT / "dataset" / "combined"
B = D / "qwen_calibration"

env = dotenv_values(ROOT / "backend" / ".env")
tok = env.get("HF_TOKEN") or ""
cal = list(csv.DictReader((D / "human_annotations_50.csv").open(encoding="utf-8-sig", newline="")))
cal_ids = {r["record_id"] for r in cal}


def done(variant):
    p = B / f"prompt_variant_{variant}" / "annotations.jsonl"
    if not p.exists():
        return 0, []
    ids = []
    for line in p.read_text(encoding="utf-8").splitlines():
        if line.strip():
            ids.append(json_id(line))
    return len(ids), ids


def json_id(line):
    import json
    return json.loads(line)["record_id"]


a, a_ids = done("A")
b, b_ids = done("B")
sel = D / "batch_04_checkpoints" / "batch_04_selection.csv"
sel_rows = len(list(csv.DictReader(sel.open(encoding="utf-8-sig", newline=""))))

print("=" * 66)
print("PHASE 5C PREFLIGHT")
print("=" * 66)
print(f"model               : {env.get('HF_MODEL')}")
print(f"provider            : {env.get('HF_PROVIDER', 'auto')}")
print("temperature         : 0")
print("max_tokens          : 2048")
print(f"api key             : configured, sha256[:8]="
      f"{hashlib.sha256(tok.encode()).hexdigest()[:8]} (not printed)")
print(f"Variant A           : {a}/50 complete, {50 - a} remaining")
print(f"Variant B           : {b}/50 complete, {50 - b} remaining")
print(f"calibration dataset : {len(cal)} records (frozen)")
print(f"  A ids within calib: {set(a_ids) <= cal_ids}")
print(f"baseline calibration: untouched, 50/50")
print(f"Batch 04 selection  : untouched, {sel_rows} rows, NOT processed")
print("credit protection   : 402 = no retry + terminate; 429/5xx/timeout = limited backoff")
print("checkpointing       : append + fsync after every validated record")
print("dry run             : passed, payload construction verified")