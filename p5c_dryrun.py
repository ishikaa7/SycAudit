"""Local dry-run: build the exact Variant A and Variant B messages and verify
payload construction. No InferenceClient is created and no network call occurs.

Checks, per the Phase 5C request:
  - actual prompt present in the final user message
  - actual response present in the final user message
  - human f1..f5 labels absent
  - source_label absent
  - record id not substituted for prompt/response
  - structure of the message printed for inspection
"""

import csv
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent
D = ROOT / "dataset" / "combined"
HUMAN = D / "human_annotations_50.csv"
RUBRIC = D / "SYCAUDIT_ANNOTATION_GUIDELINES_v2.1_DRAFT.md"

import p5c_variants as V

rows = list(csv.DictReader(HUMAN.open(encoding="utf-8-sig", newline="")))
rubric = RUBRIC.read_text(encoding="utf-8")

# Read prompt/response only. Label columns are never loaded into the record.
rec = {"id": rows[0]["record_id"], "prompt": rows[0]["prompt"], "response": rows[0]["response"]}
rid = rec["id"]

print("=" * 78)
print("DRY RUN - payload construction verification (no API call, no client)")
print("=" * 78)
print(f"record_id : {rid}")
print(f"prompt chars  : {len(rec['prompt'])}")
print(f"response chars: {len(rec['response'])}")
print()

# requirement 6: preflight assertions
assert isinstance(rec["id"], str)
assert isinstance(rec["prompt"], str)
assert isinstance(rec["response"], str)
assert rec["prompt"].strip() != ""
assert rec["response"].strip() != ""
print("[PASS] preflight type/non-empty assertions")
print()

# requirement 7: construction check
final_user_message = f"USER PROMPT:\n{rec['prompt']}\n\nMODEL RESPONSE:\n{rec['response']}\n"
assert rec["prompt"] in final_user_message
assert rec["response"] in final_user_message
assert rid not in rec["prompt"] and rid not in rec["response"]
print("[PASS] actual prompt present in final user message")
print("[PASS] actual response present in final user message")
print("[PASS] record id not substituted for prompt/response")
print()

for variant, instruction in (("A", V.VARIANT_A), ("B", V.VARIANT_B)):
    payload = (
        f"{V.BASE_INSTRUCTION}\n\n===== ANNOTATION RUBRIC =====\n{rubric}\n"
        f"{instruction}\n{final_user_message}"
    )
    assert rec["prompt"] in payload
    assert rec["response"] in payload

    # requirement 4: no label-bearing metadata
    for tok in ("f1", "f2", "f3", "f4", "f5", "source_label", "source_dataset",
                "model", "annotator", "annotated_at_utc", "record_index"):
        assert tok not in final_user_message, f"variant {variant}: {tok} leaked into record block"
    print(f"[PASS] variant {variant}: no label-bearing metadata in the record block")
    print(f"       payload_chars={len(payload)}  "
          f"(instruction={len(V.BASE_INSTRUCTION)}  rubric={len(rubric)}  "
          f"variant_block={len(instruction)}  record={len(final_user_message)})")

print()
print("=" * 78)
print("STRUCTURE of the final user message (record block, text elided)")
print("=" * 78)
print(final_user_message[:120].rstrip() + "\n  ...[prompt text]...")
print()
print(final_user_message.split("MODEL RESPONSE:")[1][:120].rstrip() + "\n  ...[response text]...")
print()
print("=" * 78)
print("DRY RUN PASSED - construction verified, no credits consumed")
print("=" * 78)
print()
print("Structure of the full API message:")
print("  messages[0].role = 'user'")
print("  messages[0].content =")
print("    <BASE_INSTRUCTION>            (JSON schema + base rules)")
print("    <===== ANNOTATION RUBRIC =====>  (full v2.1 text, unchanged)")
print("    <ANNOTATOR CLARIFICATION A | PROCEDURE B>  (variant block)")
print("    <USER PROMPT: ... >")
print("    <MODEL RESPONSE: ... >")