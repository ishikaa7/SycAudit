"""Extractor for DS3: SycoB.

Response-bearing sources and their handling:

  generated/baseline.jsonl                single-turn responses; prompt joined from
                                          prompts.csv by prompt_id; variant="baseline"
  generated/content_variants.jsonl        single-turn 3-way variants: baseline_text /
                                          subtle_text / overt_text each become a
                                          separate candidate record
  generated/styled_responses.jsonl        single-turn responses with variant+style
  generated/multiturn_baseline.jsonl      one conversation per prompt_id; each
                                          turn_k_text is the assistant response for
                                          turn k (user prompt = multiturn_prompts.csv
                                          turn_k_text)
  generated/multiturn_content_variants.jsonl  baseline_turns/subtle_turns/overt_turns
                                          lists of per-turn responses -> per-turn records
  generated/multiturn_styled.jsonl        single response per (prompt_id, variant,
                                          style, turn_index); user prompt for the turn
                                          from multiturn_prompts.csv; previous user
                                          turns serialized as context
  annotations/batch01_key.jsonl           maps item_id -> prompt_id, style, A_variant,
                                          B_variant, C_variant
  annotations/batch01_tasks.csv           480 annotation tasks; each row's resp_A/B/C
                                          become candidate records (context = prompt);
                                          ann* columns preserved verbatim in the
                                          "annotations" field (never converted to
                                          f1-f5)

Prompt-only sources (NOT response candidates): prompts.csv, multiturn_prompts.csv,
final/{train,dev,test}.jsonl. The final split files are used only to tag the
train/dev/test provenance of sq_ prompt_ids.
"""

import os

from . import (
    DS3_ROOT,
    derive_source_id,
    load_csv_rows,
    load_jsonl,
    make_record,
)

STYLES = ("concise", "markdown_structured", "plain_detailed")


def _lookup_prompts(root):
    """Return {prompt_id: row} for both single-turn and multiturn prompt files."""
    prompts = {}
    for row in load_csv_rows(os.path.join(root, "prompts.csv")):
        prompts[row["prompt_id"]] = dict(row)
    for row in load_csv_rows(os.path.join(root, "multiturn_prompts.csv")):
        prompts[row["prompt_id"]] = dict(row)
    return prompts


def _split_lookup(root):
    """Map sq_ prompt_id -> split from the final train/dev/test files (prompt-only)."""
    split_by_id = {}
    for split in ("train", "dev", "test"):
        path = os.path.join(root, "final", "%s.jsonl" % split)
        if os.path.exists(path):
            for row in load_jsonl(path):
                split_by_id[row.get("prompt_id")] = split
    return split_by_id


def _user_turn(prompt_row, k):
    """User prompt for a single-turn (k=0) or 1-based multiturn (k=1..3) record."""
    if k == 0:
        return prompt_row.get("prompt_text")
    return prompt_row.get("turn_%d_text" % k)


def _context_from_parts(parts):
    return "\n".join(parts) if parts else None


def _make_single(prompt_row, rel, prompt_id, response, variant, style,
                 split_by_id, meta=None, annotations=None, extra=None):
    if prompt_row is None:
        return None
    prompt = prompt_row.get("prompt_text")
    if not response or not prompt:
        return None
    rec = make_record(
        source_dataset="ds3", source_file=rel, source_id=prompt_id,
        prompt=prompt, response=response,
        scenario=prompt_row.get("domain"),
        stance_level=prompt_row.get("stance_level"),
        model=(meta or {}).get("model"),
        model_id=(meta or {}).get("model"),
        variant=variant, style=style,
        split=split_by_id.get(prompt_id),
        temperature=(meta or {}).get("temperature"),
        metadata=dict(meta or {}),
    )
    if prompt_row.get("source"):
        rec["metadata"]["prompt_source"] = prompt_row.get("source")
    if annotations:
        rec["annotations"] = annotations
        rec["record_status"] = "VALID"
    if extra:
        rec["metadata"].update(extra)
    return rec


def extract_ds3(data_root):
    records = []
    errors = []
    files_processed = []
    records_read = 0
    root = os.path.join(data_root, DS3_ROOT)

    prompts = _lookup_prompts(root)
    split_by_id = _split_lookup(root)

    def _missing_prompt(rel, prompt_id):
        errors.append({
            "source_dataset": "ds3", "source_file": rel,
            "source_id": prompt_id, "error_type": "missing_prompt",
            "error_message": "prompt_id not present in prompts.csv / multiturn_prompts.csv",
        })

    # ---- single-turn generated responses ----
    gen = os.path.join(root, "generated")

    rel = "generated/baseline.jsonl"
    files_processed.append(rel)
    for row in load_jsonl(os.path.join(gen, "baseline.jsonl")):
        records_read += 1
        pid = row.get("prompt_id")
        rec = _make_single(prompts.get(pid), rel, pid, row.get("text"),
                           row.get("variant") or "baseline", row.get("style"),
                           split_by_id, meta=row.get("meta") or {})
        if rec is None:
            _missing_prompt(rel, pid)
            continue
        rec["model_id"] = (row.get("meta") or {}).get("model")
        records.append(rec)

    rel = "generated/content_variants.jsonl"
    files_processed.append(rel)
    for row in load_jsonl(os.path.join(gen, "content_variants.jsonl")):
        records_read += 3
        pid = row.get("prompt_id")
        for var, text in (("baseline", row.get("baseline_text")),
                          ("subtle", row.get("subtle_text")),
                          ("overt", row.get("overt_text"))):
            rec = _make_single(prompts.get(pid), rel, pid, text, var, None,
                               split_by_id, meta=row.get("meta") or {})
            if rec is None:
                _missing_prompt(rel, pid)
                continue
            records.append(rec)

    rel = "generated/styled_responses.jsonl"
    files_processed.append(rel)
    for row in load_jsonl(os.path.join(gen, "styled_responses.jsonl")):
        records_read += 1
        pid = row.get("prompt_id")
        rec = _make_single(prompts.get(pid), rel, pid, row.get("text"),
                           row.get("variant"), row.get("style"),
                           split_by_id, meta=row.get("meta") or {})
        if rec is None:
            _missing_prompt(rel, pid)
            continue
        records.append(rec)

    # ---- multiturn generated responses ----
    def _mt_context(prompt_row, up_to_k, asst_by_turn=None):
        parts = []
        for k in range(1, up_to_k):
            u = prompt_row.get("turn_%d_text" % k)
            if u:
                parts.append("USER: %s" % u)
            a = asst_by_turn.get(k, "") if asst_by_turn else ""
            if a:
                parts.append("ASSISTANT: %s" % a)
        return _context_from_parts(parts)

    rel = "generated/multiturn_baseline.jsonl"
    files_processed.append(rel)
    for row in load_jsonl(os.path.join(gen, "multiturn_baseline.jsonl")):
        pid = row.get("prompt_id")
        prompt_row = prompts.get(pid)
        if prompt_row is None or not pid.startswith("mt_"):
            errors.append({
                "source_dataset": "ds3", "source_file": rel,
                "source_id": pid, "error_type": "missing_prompt",
                "error_message": "multiturn prompt_id not in multiturn_prompts.csv",
            })
            continue
        meta = row.get("meta") or {}
        turns = [row.get("turn_%d_text" % k) for k in (1, 2, 3)]
        if any(not (turns[k]) for k in range(3)):
            records_read += 1
            continue
        records_read += 3
        asst_by_turn = {k: turns[k - 1] for k in (1, 2, 3)}
        for k in (1, 2, 3):
            rec = make_record(
                source_dataset="ds3", source_file=rel,
                source_id="%s::t%d" % (pid, k),
                prompt=prompt_row.get("turn_%d_text" % k),
                response=turns[k - 1],
                context=_mt_context(prompt_row, k, asst_by_turn),
                conversation_id=pid, turn_index=k,
                scenario=prompt_row.get("domain"),
                stance_level=prompt_row.get("stance_level"),
                model=meta.get("model"), model_id=meta.get("model"),
                variant="baseline", style=None,
                split=split_by_id.get(pid),
                temperature=meta.get("temperature"),
                metadata=dict(meta),
            )
            if prompt_row.get("source"):
                rec["metadata"]["prompt_source"] = prompt_row.get("source")
            records.append(rec)

    rel = "generated/multiturn_content_variants.jsonl"
    files_processed.append(rel)
    for row in load_jsonl(os.path.join(gen, "multiturn_content_variants.jsonl")):
        pid = row.get("prompt_id")
        prompt_row = prompts.get(pid)
        if prompt_row is None or not pid.startswith("mt_"):
            errors.append({
                "source_dataset": "ds3", "source_file": rel,
                "source_id": pid, "error_type": "missing_prompt",
                "error_message": "multiturn prompt_id not in multiturn_prompts.csv",
            })
            continue
        for var in ("baseline", "subtle", "overt"):
            turns = row.get("%s_turns" % var) or []
            if len(turns) != 3:
                records_read += len(turns)
                continue
            records_read += 3
            for k, text in zip((1, 2, 3), turns):
                rec = make_record(
                    source_dataset="ds3", source_file=rel,
                    source_id="%s::%s::t%d" % (pid, var, k),
                    prompt=prompt_row.get("turn_%d_text" % k),
                    response=text,
                    context=_context_from_parts(
                        ["USER: %s" % prompt_row.get("turn_%d_text" % j)
                         for j in range(1, k) if prompt_row.get("turn_%d_text" % j)]
                    ),
                    conversation_id=pid, turn_index=k,
                    scenario=prompt_row.get("domain"),
                    stance_level=prompt_row.get("stance_level"),
                    model=None, model_id=None,
                    variant=var, style=None,
                    split=split_by_id.get(pid),
                    metadata={},
                )
                if prompt_row.get("source"):
                    rec["metadata"]["prompt_source"] = prompt_row.get("source")
                records.append(rec)

    rel = "generated/multiturn_styled.jsonl"
    files_processed.append(rel)
    for row in load_jsonl(os.path.join(gen, "multiturn_styled.jsonl")):
        records_read += 1
        pid = row.get("prompt_id")
        prompt_row = prompts.get(pid)
        if prompt_row is None or not pid.startswith("mt_"):
            errors.append({
                "source_dataset": "ds3", "source_file": rel,
                "source_id": pid, "error_type": "missing_prompt",
                "error_message": "multiturn prompt_id not in multiturn_prompts.csv",
            })
            continue
        meta = row.get("meta") or {}
        k0 = meta.get("turn_index", 0)
        k = (int(k0) + 1) if k0 is not None else None
        if k is None or k not in (1, 2, 3):
            continue
        user = prompt_row.get("turn_%d_text" % k)
        if not user:
            _missing_prompt(rel, pid)
            continue
        ctx_parts = ["USER: %s" % prompt_row.get("turn_%d_text" % j)
                     for j in range(1, k) if prompt_row.get("turn_%d_text" % j)]
        rec = make_record(
            source_dataset="ds3", source_file=rel,
            source_id="%s::%s::t%d" % (pid, row.get("variant"), k),
            prompt=user, response=row.get("text"),
            context=_context_from_parts(ctx_parts),
            conversation_id=pid, turn_index=k,
            scenario=prompt_row.get("domain"),
            stance_level=prompt_row.get("stance_level"),
            model=meta.get("model"), model_id=meta.get("model"),
            variant=row.get("variant"), style=row.get("style"),
            split=split_by_id.get(pid),
            metadata=dict(meta),
        )
        if prompt_row.get("source"):
            rec["metadata"]["prompt_source"] = prompt_row.get("source")
        records.append(rec)

    # ---- annotation tasks: resp_A/resp_B/resp_C become candidate records ----
    # batch01_key.jsonl maps item_id -> {prompt_id, style, A_variant, B_variant, C_variant}
    key_path = os.path.join(root, "annotations", "batch01_key.jsonl")
    key_by_item = {}
    if os.path.exists(key_path):
        for row in load_jsonl(key_path):
            key_by_item[row.get("item_id")] = row

    rel = "annotations/batch01_tasks.csv"
    files_processed.append(rel)
    task_path = os.path.join(root, "annotations", "batch01_tasks.csv")
    for row in load_csv_rows(task_path):
        item_id = row.get("item_id")
        pid = row.get("prompt_id")
        style = row.get("style") or (key_by_item.get(item_id) or {}).get("style")
        is_mt = str(row.get("is_multiturn")) == "1"
        key = key_by_item.get(item_id) or {}
        variants = {
            "resp_A": key.get("A_variant"),
            "resp_B": key.get("B_variant"),
            "resp_C": key.get("C_variant"),
        }
        for resp_key, resp_val in (("resp_A", row.get("resp_A")),
                                   ("resp_B", row.get("resp_B")),
                                   ("resp_C", row.get("resp_C"))):
            records_read += 1
            if not resp_val:
                continue
            annotations = {k: row[k] for k in row
                           if k.startswith("ann") and row[k] not in (None, "")}
            rec = make_record(
                source_dataset="ds3", source_file=rel,
                source_id="%s::%s" % (item_id, resp_key),
                prompt=row.get("context"), response=resp_val,
                scenario=row.get("domain"),
                stance_level=row.get("stance_level"),
                variant=variants.get(resp_key),
                style=style,
                conversation_id=pid,
                turn_index=None,
                metadata={},
                annotations=annotations,
            )
            try:
                rec["turn_index"] = int(float(row["turn_index"])) + 1 if row.get("turn_index") else None
            except (TypeError, ValueError):
                rec["turn_index"] = None
            if is_mt:
                rec["context"] = row.get("context")
            if row.get("source"):
                rec["metadata"]["prompt_source"] = row.get("source")
            if not rec["prompt"]:
                _missing_prompt(rel, pid)
            records.append(rec)

    summary = {
        "name": "ds3_sycob",
        "files_processed": len(files_processed),
        "records_read": records_read,
        "records_extracted": len(records),
    }
    return records, errors, summary