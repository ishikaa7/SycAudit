import json
import csv

input_file = "dataset/selected/unified_2100.jsonl"
output_file = "dataset/selected/unified_2100.csv"

with open(input_file, "r", encoding="utf-8") as f:
    records = [json.loads(line) for line in f if line.strip()]

fields = [
    "id",
    "source_dataset",
    "source_file",
    "source_id",
    "model",
    "prompt",
    "response",
    "f1",
    "f2",
    "f3",
    "f4",
    "f5",
]

with open(output_file, "w", newline="", encoding="utf-8-sig") as f:
    writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(records)

print(f"Converted {len(records)} records")
print(f"Saved to: {output_file}")