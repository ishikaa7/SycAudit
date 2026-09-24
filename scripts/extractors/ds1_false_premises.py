"""Extractor for DS1: sycophancy-false-premises.

Response-bearing sources (all others are prompt-only or aggregate results and
are skipped):

  root/ablation_labels.json           180 rows: prompt_id, model, prompt, completion,
                                          ground_truth, ablation_label
  root/full_ablation_labels.json      576 rows: same schema
  root/gpt4o_labels_all.json          3000 rows: model, model_id, timestamp, prompt,
                                          completion, gpt4o_label
  root/human_validation_sample.json   50 rows: adds human_label
  phase3_distributional/*_labeled.jsonl      6 files x 5250: id, fact_id, category, framing,
                                          prompt, is_paper1_bridge, temperature, sample_idx,
                                          completion, model, seed, gpt4o_label
  phase3_distributional/cross_judge_gpt4o_labels.jsonl 1500 rows (+gpt4o_cross_label)
  phase4_scale/*_labeled.jsonl        2 files x 1500: model, fact_id, framing, temperature,
                                          sample_idx, prompt, completion, seed, gpt4o_label
  phase4_scale/*_completions.jsonl    2 files x 1500: no label (completions only)
  v1_nf4_quantized/ablation_labels.json         180 (exact dupes of root ablation)
  v1_nf4_quantized/full_ablation_labels.json    576 (exact dupes of root full_ablation)

Skipped (no model response): full_ablation_prompts.json, prompt_pressure_labels.json,
dual_label_wrong_results.json, human_validation_results.json, entropy_results.json,
kdg_results.json, phase4_kdg_comparison.json, miscellaneous .txt reports, and the
v1_nf4_quantized/dual_label_wrong_results.json (no completion).

Wrappers: root files carry [INST]/[/INST] or the old glue transcript format;
phase3/phase4 completions are bare answers.
"""

import os

from . import (
    DS1_ROOT,
    clean_chat_completion,
    contains_template_marker,
    derive_source_id,
    load_json,
    load_jsonl,
    make_record,
)


def _process_completion(completion, prompt, cleaning):
    """Returns (prompt, response, cleaning_status, treat_as_review)."""
    if completion is None:
        return prompt, None, "needs_review", True
    response, status = clean_chat_completion(completion, prompt)
    if not response:
        return prompt, response, "needs_review", True
    return prompt, response, status, False


def _label_columns(record, row, extra_label_key=None):
    for key in ("gpt4o_label", "human_label", "ablation_label"):
        if key in row:
            record[key] = row[key]
    if extra_label_key and extra_label_key in row:
        record["metadata"].setdefault("extra_labels", {})
        record["metadata"]["extra_labels"][extra_label_key] = row[extra_label_key]
    for key in ("ground_truth", "is_paper1_bridge"):
        if key in row:
            record[key] = row[key]


def _row_record(source_file, source_id, row, prompt_key="prompt", completion_key="completion"):
    prompt = row.get(prompt_key)
    completion = row.get(completion_key)
    rec = make_record(
        source_dataset="ds1",
        source_file=source_file,
        source_id=source_id,
        prompt=prompt,
        model=row.get("model"),
        model_id=row.get("model_id"),
    )
    rec["prompt"], rec["response"], status, review = _process_completion(completion, prompt, rec)
    rec["response_cleaning_status"] = status
    for key in ("category", "framing", "temperature", "seed", "sample_idx", "fact_id", "prompt_id"):
        if key in row:
            rec[key] = row[key]
    _label_columns(rec, row, extra_label_key="gpt4o_cross_label")
    for key in ("timestamp", "id"):
        if key in row:
            rec["metadata"][key] = row[key]
    rec["record_status"] = "VALID" if not review else "WARNING"
    if review:
        rec["warnings"].append({
            "error_type": "ambiguous_cleaning",
            "error_message": "response could not be cleanly extracted from chat wrapper; original completion preserved in response_cleaning_status=needs_review",
        })
    if contains_template_marker(rec["response"] or ""):
        rec["warnings"].append({
            "error_type": "possible_template_marker",
            "error_message": "cleaned response still contains a chat-template marker",
        })
        if rec["record_status"] == "VALID":
            rec["record_status"] = "WARNING"
    return rec


def extract_ds1(data_root):
    records = []
    errors = []
    files_processed = []
    records_read = 0
    root = os.path.join(data_root, DS1_ROOT)

    def scan_json(rel, source_id_key="prompt_id", default_source="row"):
        nonlocal records_read
        path = os.path.join(root, rel)
        files_processed.append(rel)
        rows = load_json(path)
        for idx, row in enumerate(rows):
            records_read += 1
            sid = row.get(source_id_key) if source_id_key else None
            if sid is None:
                composite = str(row.get("prompt_id") or row.get("fact_id") or row.get("id") or idx)
                sid = "%s_%d" % (composite, idx)
            sources = [sid, row.get("model")]
            if row.get("sample_idx") is not None:
                sources.append(str(row.get("sample_idx")))
            source_id = "::".join(str(s) for s in sources if s is not None)
            records.append(_row_record(rel, source_id, row))

    def scan_jsonl(rel):
        nonlocal records_read
        path = os.path.join(root, rel)
        files_processed.append(rel)
        rows = load_jsonl(path)
        for idx, row in enumerate(rows):
            records_read += 1
            composite = str(row.get("fact_id") or row.get("id") or idx)
            parts = [composite, row.get("model")]
            if row.get("sample_idx") is not None:
                parts.append(str(row.get("sample_idx")))
            source_id = "::".join(str(p) for p in parts if p is not None)
            records.append(_row_record(rel, source_id, row))

    # Root JSON files
    scan_json("ablation_labels.json")
    scan_json("full_ablation_labels.json")
    scan_json("gpt4o_labels_all.json")
    scan_json("human_validation_sample.json")

    # Phase 3 distributional labeled files
    p3_dir = os.path.join(root, "phase3_distributional")
    for fname in sorted(os.listdir(p3_dir)):
        if fname.endswith("_labeled.jsonl"):
            scan_jsonl("phase3_distributional/" + fname)
        elif fname == "cross_judge_gpt4o_labels.jsonl":
            scan_jsonl("phase3_distributional/" + fname)

    # Phase 4 scale files
    p4_dir = os.path.join(root, "phase4_scale")
    for fname in sorted(os.listdir(p4_dir)):
        if fname.endswith(".jsonl"):
            scan_jsonl("phase4_scale/" + fname)

    # v1_nf4_quantized mirrors (exact duplicates of root ablation files)
    scan_json("v1_nf4_quantized/ablation_labels.json")
    scan_json("v1_nf4_quantized/full_ablation_labels.json")

    summary = {
        "name": "ds1_false_premises",
        "files_processed": len(files_processed),
        "records_read": records_read,
        "records_extracted": len(records),
    }
    return records, errors, summary