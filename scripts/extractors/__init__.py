"""Shared helpers for the dataset extraction pipeline.

All extractor modules return the same "internal record" dict shape so a single
orchestrator (scripts/extract_datasets.py) can validate, deduplicate and select
from every dataset uniformly.

Canonical internal record fields (missing values are stored as None):
    source_dataset             - "ds1" | "ds2" | "ds3"
    source_file                - relative path under dataset/<repo>/
    source_id                  - unique id for the record within source_file
    prompt                     - the user prompt string
    response                   - the model response string (wrapper cleaned)
    context                    - prior conversation context or None
    conversation_id            - conversation/group id or None
    turn_index                 - 1-based turn number or None
    model                      - model display name or None
    model_id                   - canonical model id or None
    scenario                   - dataset-specific scenario or None
    category                   - dataset-specific category or None
    framing                    - dataset-specific framing or None
    stance_level               - dataset-specific stance level or None
    variant                    - dataset-specific variant or None
    style                      - dataset-specific style or None
    split                      - train/dev/test or None
    temperature                - sampling temperature or None
    seed                       - sampling seed or None
    sample_idx                 - sample index or None
    gpt4o_label                - raw label from file, preserved verbatim
    human_label                - raw label from file, preserved verbatim
    ablation_label             - raw label from file, preserved verbatim
    turn_judgments             - list of turn-level judgments or None
    judge_raw_responses        - list of judge responses or None
    annotations                - dict of annotation columns (ann1_/ann2_/ann3_) or {}
    ground_truth               - raw ground-truth string or None
    knowledge_*                - knowledge-test fields or None
    is_paper1_bridge           - bool flag or None
    metadata                   - dict of additional raw source fields (timestamp,
                                 prompt_hash, token counts, source provenance, ...)
    record_status              - "VALID" | "WARNING" | "INVALID"
    response_cleaning_status   - "clean" | "cleaned" | "needs_review"
    warnings                   - list of {error_type, error_message}
"""

import json
import os
import re
import warnings as _warnings

# Directory roots (read-only) for each source dataset under dataset/.
DS1_ROOT = "sycophancy-false-premises"
DS2_ROOT = "sycophancy-bench"
DS3_ROOT = "SycoB"


def load_json(path):
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def load_jsonl(path):
    records = []
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def load_csv_rows(path):
    """Read a CSV into a list of dicts, tolerating NaN -> None."""
    try:
        import csv
    except ImportError:
        _warnings.warn("csv module unavailable")
        return []
    rows = []
    with open(path, "r", encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            rows.append({k: (None if v == "" else v) for k, v in row.items()})
    return rows


def clean_text_value(value):
    """Collapse whitespace; return '' for None."""
    if value is None:
        return ""
    if not isinstance(value, str):
        return ""
    return re.sub(r"\s+", " ", value).strip()


def normalize_text(value):
    """Deterministic normalization used for duplicate detection."""
    return clean_text_value(value).lower()


def clean_chat_completion(completion, prompt=None):
    """Strip chat-template wrappers (DS1).

    Returns (answer_text, cleaning_status)

    - "[INST] ... [/INST] answer": text after the last [/INST] marker.
    - 'system\\n\\nYou are a helpful assistant.user\\n\\n{prompt}assistant\\n\\n{ans}'
      (old glue format): anchored on the prompt, then the trailing "assistant"
      marker is removed.
    - Bare answers are returned unchanged.

    If extraction is ambiguous the original completion is preserved and the
    status is "needs_review" (the caller decides whether to flag a warning).
    """
    if completion is None:
        return "", "needs_review"
    comp = clean_text_value(completion)
    if not comp:
        return "", "needs_review"

    if "[/INST]" in comp:
        idx = comp.rfind("[/INST]")
        after = comp[idx + len("[/INST]"):].strip()
        return after, "cleaned"

    if apps := (comp.startswith("system") or comp.startswith("You are a helpful assistant")):
        # transcript glue format: "user\n\n{prompt}assistant\n\n{answer}"
        if prompt and prompt in comp:
            p_idx = comp.find(prompt)
            rest = comp[p_idx + len(prompt):].strip()
            if rest.startswith("assistant"):
                rest = rest[len("assistant"):].strip(" \n")
            if rest:
                return rest, "cleaned"
        # fall back to the last assistant marker
        marker = "assistant\n\n"
        m_idx = comp.rfind(marker)
        if m_idx >= 0:
            return comp[m_idx + len(marker):].strip(), "cleaned"
        return comp, "needs_review"

    if apps and "[/INST]" not in comp:
        pass

    return comp, "clean"


def strip_thinking_block(text):
    """Remove a leading '<think>...</think>' (or '<thinking>...</thinking>') block.

    Returns (text, was_stripped). Markers are built from chr() codes so the
    file source cannot accidentally drop/mangle the angle brackets.
    """
    if not text:
        return text, False
    lt, gt = chr(60), chr(62)
    for tag_name in ("thinking", "think"):
        open_tag = lt + tag_name + gt
        close_tag = lt + "/" + tag_name + gt
        pattern = (r"^\s*" + re.escape(open_tag)
                   + r".*?" + re.escape(close_tag) + r"\s*")
        m = re.search(pattern, text, flags=re.S)
        if m:
            return text[m.end():], True
    return text, False


TEMPLATE_MARKERS = (
    "[/INST]",
    "[INST]",
    "system\n\nYou are a helpful assistant",
    "assistant\n\n",
)


def contains_template_marker(text):
    return any(marker in text for marker in TEMPLATE_MARKERS)


def make_record(**fields):
    """Build the canonical internal record with all keys present (None defaults)."""
    keys = [
        "source_dataset", "source_file", "source_id", "prompt", "response",
        "context", "conversation_id", "turn_index", "model", "model_id",
        "scenario", "category", "framing", "stance_level", "variant", "style",
        "split", "temperature", "seed", "sample_idx",
        "gpt4o_label", "human_label", "ablation_label",
        "turn_judgments", "judge_raw_responses", "annotations",
        "ground_truth", "knowledge_correct_letter", "knowledge_model_choice",
        "knowledge_knows_correct", "knowledge_raw_response", "is_paper1_bridge",
        "metadata",
        "record_status", "response_cleaning_status", "warnings",
    ]
    record = {k: None for k in keys}
    for k, v in fields.items():
        if k in record:
            record[k] = v
        elif k.startswith("knowledge_"):
            record[k] = v
        else:
            raise KeyError("unexpected field for internal record: %s" % k)
    if record["annotations"] is None:
        record["annotations"] = {}
    if record["metadata"] is None:
        record["metadata"] = {}
    if record["warnings"] is None:
        record["warnings"] = []
    return record


def derive_source_id(record):
    """Stable composite source id for the selection/report layer."""
    parts = []
    for key in ("source_file", "source_id"):
        val = record.get(key)
        if val is None:
            continue
        parts.append(str(val))
    if record.get("turn_index") is not None:
        parts.append("turn%d" % record["turn_index"])
    if record.get("variant"):
        parts.append(str(record["variant"]))
    return "::".join(parts)