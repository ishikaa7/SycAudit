"""Extractor for DS2: sycophancy-bench.

Response-bearing sources: the generation parquet files under generations/:
  generations/debate/<model>/{train,test}.parquet
  generations/false_presupposition/<model>/{train,test}.parquet

Models present: Qwen2.5-14B-Instruct, Qwen3.5-35B-A3B_no_thinking.

Each row is one conversation:
  turns            list of {assistant_response, prompt_token_count,
                            response_token_count, turn, user_message}
  turn_judgments   parallel list of model-judge verdicts
  judge_raw_responses parallel list of raw judge strings
  metadata         struct with {argument, question} (debate) or
                   {correction, presupposition, question} (false_presupposition)
  knowledge_*      knowledge-test fields (false_presupposition only)

One internal record is produced PER TURN so that conversation context, turn
index and turn-level judgments are all preserved. The model response is always
turns[].assistant_response (never judge/knowledge fields). Qwen3.5 responses
carry a leading "<thinking>...</thinking>" block which is stripped only when it
is present at the very start; otherwise text is preserved unchanged.
"""

import os

from . import (
    DS2_ROOT,
    make_record,
    strip_thinking_block,
)

MODEL_DIRS = ["Qwen2.5-14B-Instruct", "Qwen3.5-35B-A3B_no_thinking"]
THINKING_MODELS = {"Qwen3.5-35B-A3B_no_thinking"}


def _read_parquet(path):
    try:
        import pyarrow.parquet as pq
    except ImportError:
        raise RuntimeError(
            "pyarrow is required to read DS2 parquet files. Install it or rerun without DS2."
        )
    return pq.read_table(path).to_pylist()


def extract_ds2(data_root):
    records = []
    errors = []
    files_processed = []
    records_read = 0
    root = os.path.join(data_root, DS2_ROOT)

    def _extract_file(rel, model_dir_name, split):
        nonlocal records_read
        path = os.path.join(root, rel)
        files_processed.append(rel)
        rows = _read_parquet(path)
        for row in rows:
            records_read += 1
            rid = str(row.get("id") or "")
            scenario = row.get("scenario")
            mt = row.get("metadata") or {}
            turns = row.get("turns") or []
            judges = row.get("turn_judgments") or []
            raw_judges = row.get("judge_raw_responses") or []

            try:
                turns = [dict(t) for t in turns]
            except Exception:
                errors.append({
                    "source_dataset": "ds2", "source_file": rel,
                    "source_id": rid, "error_type": "malformed_nested_structure",
                    "error_message": "turns is not a list of dicts",
                })
                continue

            if not turns:
                continue

            n_turns = len(turns)
            if not isinstance(judges, (list, tuple)):
                judges = []
            if not isinstance(raw_judges, (list, tuple)):
                raw_judges = []
            judge_mismatch = (len(judges) != n_turns) or (len(raw_judges) != n_turns)

            if judge_mismatch:
                errors.append({
                    "source_dataset": "ds2", "source_file": rel,
                    "source_id": rid,
                    "error_type": "invalid_turn_alignment",
                    "error_message": (
                        "turns=%d turn_judgments=%d judge_raw_responses=%d "
                        "do not align; alignment-dependent fields set to None"
                        % (n_turns, len(judges), len(raw_judges)),
                    ),
                })

            context_parts = []
            for i in range(len(turns)):
                turn = turns[i]
                turn_no = turn.get("turn", i + 1)
                user_msg = turn.get("user_message")
                asst = turn.get("assistant_response")

                base = {
                    "source_dataset": "ds2", "source_file": rel, "source_id": rid,
                    "conversation_id": rid, "turn_index": int(turn_no),
                    "model": model_dir_name, "model_id": row.get("model_id"),
                    "scenario": scenario, "split": split,
                }

                if not user_msg or not isinstance(user_msg, str) or not user_msg.strip():
                    errors.append({
                        "source_dataset": "ds2", "source_file": rel,
                        "source_id": rid, "turn_index": int(turn_no),
                        "error_type": "missing_prompt",
                        "error_message": "empty user_message at turn %d" % int(turn_no),
                    })
                    continue

                if asst is None or not isinstance(asst, str) or not asst.strip():
                    errors.append({
                        "source_dataset": "ds2", "source_file": rel,
                        "source_id": rid, "turn_index": int(turn_no),
                        "error_type": "missing_response",
                        "error_message": "empty assistant_response at turn %d" % int(turn_no),
                    })
                    continue

                cleaned_resp = asst
                cleaning_status = "clean"
                if model_dir_name in THINKING_MODELS:
                    stripped, was_stripped = strip_thinking_block(asst)
                    if was_stripped:
                        cleaned_resp = stripped
                        cleaning_status = "cleaned"

                context = "\n".join(context_parts) if context_parts else None
                rec = make_record(
                    **base, prompt=user_msg, response=cleaned_resp, context=context,
                )
                rec["response_cleaning_status"] = cleaning_status
                rec["metadata"]["conversation_metadata"] = dict(mt or {})
                rec["metadata"]["prompt_token_count"] = turn.get("prompt_token_count")
                rec["metadata"]["response_token_count"] = turn.get("response_token_count")
                rec["metadata"]["judge_alignment_broken"] = judge_mismatch
                if judge_mismatch:
                    rec["record_status"] = "WARNING"
                    rec["warnings"].append({
                        "error_type": "invalid_turn_alignment",
                        "error_message": "turn-level judge fields do not align; set to None",
                    })
                else:
                    rec["turn_judgments"] = judges[i]
                    rec["judge_raw_responses"] = raw_judges[i]

                for key in ("knowledge_correct_letter", "knowledge_model_choice",
                            "knowledge_knows_correct", "knowledge_raw_response"):
                    val = row.get(key)
                    if val is not None:
                        rec[key] = val

                records.append(rec)
                context_parts.append("USER: %s\nASSISTANT: %s" % (user_msg, asst))

    for model_dir in MODEL_DIRS:
        for split in ("train", "test"):
            rel = "generations/debate/%s/%s.parquet" % (model_dir, split)
            if os.path.exists(os.path.join(root, rel)):
                _extract_file(rel, model_dir, split)
            rel = "generations/false_presupposition/%s/%s.parquet" % (model_dir, split)
            if os.path.exists(os.path.join(root, rel)):
                _extract_file(rel, model_dir, split)

    summary = {
        "name": "ds2_sycophancy_bench",
        "files_processed": len(files_processed),
        "records_read": records_read,
        "records_extracted": len(records),
    }
    return records, errors, summary