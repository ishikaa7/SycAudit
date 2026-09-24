#!/usr/bin/env python3
"""Recursively inspect the project's ``dataset/`` directory (READ-ONLY).

For every structured data file found (.json / .jsonl / .ndjson / .jsonlines /
.csv / .tsv / .parquet) it reports:
  * relative path and file kind
  * number of records / rows (when reasonably obtainable)
  * top-level field names, their data types and nesting
  * a compact structural sketch of nested values
  * 2 representative sample records (truncated)
It then heuristically classifies fields into semantic roles (prompt / response /
conversation / id / label / score / metadata) and flags files that need special
handling (no prompt/response pair, multiple candidate responses, multiple-choice
data, multi-turn history, or anything that would not load cleanly).

The script never writes to ``dataset/``. It only produces:
  * ``dataset_inspection_report.md`` (default, at repo root)
  * a concise terminal summary

Dependencies: standard library only. ``pandas``/``pyarrow`` are used only for
.parquet files and only if importable; otherwise the file is flagged instead of
crashing.

Usage:
    python scripts/inspect_datasets.py [--root ../dataset] [--report ../dataset_inspection_report.md]
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import pathlib
import re
import sys
from dataclasses import dataclass, field

ROOT = pathlib.Path(__file__).resolve().parent.parent / "dataset"
REPORT = pathlib.Path(__file__).resolve().parent.parent / "dataset_inspection_report.md"

DATA_SUFFIXES = {
    ".json": "json",
    ".jsonl": "jsonl",
    ".ndjson": "jsonl",
    ".jsonlines": "jsonl",
    ".csv": "csv",
    ".tsv": "csv",
    ".parquet": "parquet",
    ".pqt": "parquet",
}

MAX_ANALYZED_RECORDS = 200_000   # cap for per-field stats on pathological files
MAX_FIELD_PATHS = 40             # cap on dotted schema paths kept for description
SAMPLE_LIMIT = 2
STR_LIMIT = 180                  # truncate string values in samples/descriptions
LIST_ITEM_LIMIT = 2              # items shown per list in samples/sketches
DEPTH_LIMIT = 3                  # nesting depth for structural sketches
MAX_ISSUE_NOTES = 3              # malformed-line examples kept per file

# --------------------------------------------------------------------------- semantic rules

# --------------------------------------------------------------------------- semantic rules
# Every *lowercased* dotted path is classified against the first matching rule
# (order matters). Rules are keyword heuristics only; they encode no mapping
# decision about how datasets will be unified later.

ID_RULES = (
    r"(^|\.)id$", r"(^|\.).*_id$", r"(^|\.)index$", r"(^|\.)sample_idx$",
    r"(^|\.)uid$", r"(^|\.)uuid$",
)
PROMPT_RULES = (
    r"(^|\.)(prompt|question|input|instruction|context|statement|claim|premise|"
    r"sentence|content|query|text|original|neutral|user|human)$",
    r"(^|\.)sentence_with_",  # e.g. sentence_with_blank
)
RESPONSE_RULES = (
    r"(^|\.)(response|answer|answers|completion|output|bot|assistant|"
    r"generation|generated|reply|choice|choices|answer_matching_behavior|"
    r"answer_not_matching_behavior|correct_answer|incorrect_answer|"
    r"correct_letter|candidate|candidate_answer)$",
)
CONVERSATION_RULES = (
    r"(^|\.)(history|conversation|dialogue|dialog|messages|turns|messages_gpt)"
    r"$|(^|\.)prompt$",
)
LABEL_RULES = (
    r"(^|\.)(label|labels|behavior|ground_truth|correct_t[0-9]|consensus|"
    r"(gpt4o|gpt-4o|human|mini|ablation|pressure)_?label)$",
    r"(^|\.)sycophancy(:?_)", r"(^|\.)(human_labels|gpt4o_labels|gpt-4o_labels)$",
)
SCORE_RULES = (
    r"(^|\.)(rating|ratings|score|scores|confidence|entropy|kdg|"
    r"p_correct(_neutral|_framed)?|probability|prob|accuracy|kappa|ci|pct|"
    r"percent|``percent``|percents)([._-]|$)",
)
METADATA_RULES = (
    r"(^|\.)(metadata|prompt_template|template|prompt_template_v2|temperature|"
    r"seed|model|version|source|dataset|timestamp|affiliation|framing|category|"
    r"subset|n_samples|s1_count|distribution|model_id|timestamp_ms|"
    r"incorrect_attribution|attribution|is_paper1_bridge|num_evals_raw|"
    r"n|composition|type)$",
)

VALIDATE_PAIR_ENABLED = True


def classify_path(path: str) -> str | None:
    low = path.lower()
    for group, rules in (
        ("id", ID_RULES), ("prompt", PROMPT_RULES), ("response", RESPONSE_RULES),
        ("conversation", CONVERSATION_RULES), ("label", LABEL_RULES),
        ("score", SCORE_RULES), ("metadata", METADATA_RULES),
    ):
        for rule in rules:
            if re.search(rule, low):
                return group
    return None


# Turn-dict subkeys (inside history/messages) get stricter, but explicit roles.
TURN_ROLE = {
    "user": "prompt", "human": "prompt", "question": "prompt", "instruction": "prompt",
    "bot": "response", "assistant": "response", "ai": "response", "answer": "response",
    "content": None,  # depends on sibling 'type' value
}


# --------------------------------------------------------------------------- small helpers
def pytype(v) -> str:
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "bool"
    if isinstance(v, int):
        return "int"
    if isinstance(v, float):
        return "float"
    if isinstance(v, str):
        return "str"
    if isinstance(v, list):
        return "list"
    if isinstance(v, dict):
        return "dict"
    return type(v).__name__


def truncate(v, depth: int = 0) -> str:
    """Return a compact, truncated ASCII-safe representation of a value."""
    if isinstance(v, str):
        s = v.replace("\n", "\\n").replace("\r", "\\r")
        return s if len(s) <= STR_LIMIT else s[: STR_LIMIT - 3] + "..."
    if isinstance(v, list):
        shown = [truncate(x, depth + 1) for x in v[:LIST_ITEM_LIMIT]]
        tail = f"... [{len(v) - LIST_ITEM_LIMIT} more] " if len(v) > LIST_ITEM_LIMIT else ""
        return "[" + ", ".join(shown) + tail + "]"
    if isinstance(v, dict):
        parts = []
        for k, val in list(v.items())[:8]:
            parts.append(f"{k}={truncate(val, depth + 1)}")
        more = f" ... {len(v) - 8} more keys" if len(v) > 8 else ""
        return "{" + ", ".join(parts) + more + "}"
    return f"{v!r}"


def sketch(v, depth: int = 0) -> str:
    """Structural sketch: dict{key:type[...]} showing nesting, not values."""
    if depth >= DEPTH_LIMIT:
        return "…"
    if isinstance(v, dict):
        parts = []
        for k, val in v.items():
            parts.append(f"{k}:{sketch(val, depth + 1)}")
        inner = ", ".join(parts)
        return "{" + (inner[:200] + (f" …+{len(parts)}" if len(inner) > 200 else "")) + "}"
    if isinstance(v, list):
        if not v:
            return "[]"
        return f"[{len(v)}× {sketch(v[0], depth + 1)}]"
    return pytype(v)


def schema_paths(obj, prefix: str = "", depth: int = 0, limit: int = MAX_FIELD_PATHS):
    """Yield `(dotted_path, value)` for scalar/list/dict leaves up to depth `limit`."""
    if depth > 3:
        return
    if isinstance(obj, dict):
        for k, val in obj.items():
            path = f"{prefix}.{k}" if prefix else str(k)
            if isinstance(val, dict):
                yield path, val
                yield from schema_paths(val, path, depth + 1, limit)
            elif isinstance(val, list):
                yield path, val
                if len(val) > 1:  # only describe multi-element lists
                    yield from schema_paths(val[0], path, depth + 1, limit)
            else:
                yield path, val
    elif isinstance(obj, list):
        for i, item in enumerate(obj[:1]):
            yield from schema_paths(item, prefix, depth + 1, limit)


# --------------------------------------------------------------------------- loading
@dataclass
class FileReport:
    rel_path: str
    dataset_group: tuple
    file_type: str
    container: str
    record_count: int = 0
    parsed_count: int = 0
    malformed_count: int = 0
    blank_count: int = 0
    encoding_note: str = ""
    fields: dict = field(default_factory=dict)        # top-level field -> FieldStat-ish dict
    nested_paths: dict = field(default_factory=dict)  # first-record dotted schema
    samples: list[str] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)
    semantic: dict = field(default_factory=dict)      # role -> list of dotted paths
    flags: list[str] = field(default_factory=list)
    load_error: str = ""
    notes: list[str] = field(default_factory=list)


def read_text_lenient(p: pathlib.Path) -> tuple[str, str]:
    raw = p.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        return raw.decode("utf-8-sig", errors="replace"), "utf-8 (BOM)"
    try:
        return raw.decode("utf-8"), "utf-8"
    except UnicodeDecodeError:
        return raw.decode("utf-8", errors="replace"), "utf-8 with replacement chars (invalid bytes present)"


def field_bundle(stats: dict, key: str, value):
    types = stats.setdefault(key, {"types": set(), "nested": False, "present": 0})
    types["types"].add(pytype(value))
    types["nested"] = types["nested"] or isinstance(value, (dict, list))
    types["present"] += 1


def add_field_stats(stats: dict, record: dict) -> None:
    for k, v in record.items():
        field_bundle(stats, k, v)


def inspect_json(src: pathlib.Path, rel: str, group: str, container_hint: str | None = None) -> FileReport:
    rep = FileReport(rel, group, "json", "json")
    text, enc = read_text_lenient(src)
    rep.encoding_note = enc
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        rep.load_error = f"malformed JSON: {exc}"
        rep.container = "UNPARSEABLE"
        rep.flags.append("LOAD_ISSUES")
        return rep

    wrapper_keys = ["data", "records", "results", "items", "examples", "samples", "dataset"]
    records: list = []

    if isinstance(data, list):
        rep.container = "ARRAY"
        records = data
    elif isinstance(data, dict):
        if not data:
            rep.container = "FLAT_DICT_EMPTY"
            records = []
        elif all(isinstance(v, dict) for v in data.values()):
            rep.container = "DICT_OF_RECORDS"
            records = list(data.values())
            rep.notes.append(
                f"dict keyed by {len(data)} record ids; the first 12 keys are used as id values, e.g. {list(data)[:3]!r}"
            )
        elif any(k in wrapper_keys for k in data) and any(isinstance(data[k], list) for k in wrapper_keys):
            key = next(k for k in wrapper_keys if isinstance(data.get(k), list))
            rep.container = f"WRAPPED_ARRAY(key={key})"
            records = data[key]
        elif all(not isinstance(v, (dict, list)) for v in data.values()):
            rep.container = "DICT_OF_SCALARS"
            recs = [{"_key": k, "_value": v} for k, v in data.items()]
            records = recs
            rep.notes.append(
                f"dict maps {len(data)} keys to scalar values; keys treated as ids/prompts, values as labels. "
                f"example value type: {pytype(next(iter(data.values()))) if data else 'n/a'}"
            )
        else:
            rep.container = "FLAT_OBJECT"
            records = [data]

    rep.record_count = len(records)
    rep.parsed_count = len(records)
    analyzed = records[:MAX_ANALYZED_RECORDS]
    for r in analyzed[: min(len(analyzed), MAX_ANALYZED_RECORDS)]:
        if isinstance(r, dict):
            add_field_stats(rep.fields, r)
    for r in analyzed[:SAMPLE_LIMIT]:
        rep.samples.append(truncate(r))
    if records:
        first = records[0]
        rep.nested_paths = dict(schema_paths(first))
    return rep


def inspect_jsonl(src: pathlib.Path, rel: str, group: str) -> FileReport:
    rep = FileReport(rel, group, "jsonl", "jsonl")
    if src.read_bytes()[:3] == b"\xef\xbb\xbf":
        rep.encoding_note = "utf-8 (BOM)"
    try:
        lines = src.read_text(encoding="utf-8-sig").splitlines()
        for line in lines:
            if not line.strip():
                rep.blank_count += 1
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                rep.malformed_count += 1
                if len(rep.issues) < MAX_ISSUE_NOTES:
                    rep.issues.append(f"malformed line: {line[:120]!r}")
                continue
            if rep.record_count < MAX_ANALYZED_RECORDS:
                rep.record_count += 1
                if isinstance(obj, dict):
                    add_field_stats(rep.fields, obj)
                if len(rep.samples) < SAMPLE_LIMIT:
                    rep.samples.append(truncate(obj))
                if rep.record_count == 1:
                    rep.nested_paths = dict(schema_paths(obj))
            else:
                rep.record_count += 1
        rep.parsed_count = rep.record_count
        if rep.record_count >= MAX_ANALYZED_RECORDS:
            rep.notes.append(f"field stats computed on the first {MAX_ANALYZED_RECORDS} records; total record count is exact.")
    except UnicodeDecodeError:
        rep = FileReport(rel, group, "jsonl", "UNPARSEABLE")
        rep.load_error = "file is not valid UTF-8 text"
        rep.flags.append("LOAD_ISSUES")
    return rep


def inspect_csv(src: pathlib.Path, rel: str, group: str, delimiter: str = ",") -> FileReport:
    rep = FileReport(rel, group, "tsv" if delimiter == "\t" else "csv", "csv")
    try:
        text, enc = read_text_lenient(src)
        reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
        header = reader.fieldnames or []
        rep.fields = {h: {"types": set(), "nested": False, "present": 0} for h in header}
        prototypes = [pytype(None) for _ in header]
        rows = 0
        for row in reader:
            rows += 1
            if rows > MAX_ANALYZED_RECORDS:
                continue
            for i, h in enumerate(header):
                val = row.get(h)
                rep.fields[h]["present"] += 1
                t = "null" if val is None or val == "" else ("num" if re.fullmatch(r"-?[\d.eE+]+", val) else "str")
                if t not in prototypes[i]:
                    prototypes[i] = t
        rep.record_count = rows
        rep.parsed_count = rows
        for i, h in enumerate(header):
            rep.fields[h]["types"] = {prototypes[i]}
        for r in csv.DictReader(io.StringIO(text), delimiter=delimiter):
            rep.samples.append(truncate(dict(r)))
            if len(rep.samples) >= SAMPLE_LIMIT:
                break
        rep.container = f"CSV {len(header)} columns"
    except Exception as exc:  # noqa: BLE001
        rep.load_error = f"failed to read CSV: {type(exc).__name__}: {exc}"
        rep.container = "UNPARSEABLE"
        rep.flags.append("LOAD_ISSUES")
    return rep


def inspect_parquet(src: pathlib.Path, rel: str, group: str) -> FileReport:
    rep = FileReport(rel, group, "parquet", "parquet")
    try:
        import pandas as pd  # noqa: PLC0415
    except ImportError:
        rep.load_error = "parquet support requires pandas; not installed in this environment"
        rep.container = "UNPARSEABLE"
        rep.flags.append("LOAD_ISSUES")
        return rep
    try:
        df = pd.read_parquet(src, engine="pyarrow")
    except ImportError:
        rep.load_error = "parquet support requires pyarrow; not installed in this environment"
        rep.container = "UNPARSEABLE"
        rep.flags.append("LOAD_ISSUES")
        return rep
    except Exception as exc:  # noqa: BLE001
        rep.load_error = f"failed to read parquet: {type(exc).__name__}: {exc}"
        rep.container = "UNPARSEABLE"
        rep.flags.append("LOAD_ISSUES")
        return rep
    rep.record_count = len(df)
    rep.parsed_count = rep.record_count
    for col in df.columns:
        dt = str(df[col].dtype)
        samples = df[col].dropna().head(3).tolist()
        rep.fields[col] = {"types": {dt}, "nested": any(isinstance(s, (dict, list)) for s in samples), "present": int(df[col].notna().sum())}
    records = df.head(10).to_dict(orient="records")
    for r in records[:SAMPLE_LIMIT]:
        rep.samples.append(truncate(r))
    if records:
        rep.nested_paths = dict(schema_paths(records[0]))
    return rep


# --------------------------------------------------------------------------- classification + flags
def classify_semantics(rep: FileReport) -> None:
    rep.semantic = {"prompt": [], "response": [], "conversation": [], "id": [], "label": [], "score": [], "metadata": [], "other": []}
    paths = list(rep.nested_paths.keys()) or [f for f in rep.fields]
    if rep.container == "DICT_OF_SCALARS":
        rep.semantic["prompt"].append("_key")
        rep.semantic["label"].append("_value")
        marked = {"_key", "_value"}
    else:
        marked = set()
    seen = set()
    for path in paths:
        if path in seen or path in marked:
            continue
        seen.add(path)
        seg = path.rsplit(".", 1)
        parent = seg[0] if len(seg) == 2 else ""
        name = seg[-1].lower()
        if parent in ("history", "conversation", "dialogue", "dialog", "messages", "turns"):
            if name in TURN_ROLE:
                role = TURN_ROLE[name]
                if role:
                    rep.semantic[role].append(path)
                elif parent:
                    rep.semantic["content"].append(path) if "content" in rep.semantic else rep.semantic["response"].append(path)
                continue
        role = classify_path(path)
        if role is None:
            role = "other"
        rep.semantic[role].append(path)


def detect_flags(rep: FileReport) -> None:
    if rep.load_error:
        rep.flags.append("LOAD_ISSUES")
        return
    if rep.malformed_count:
        rep.flags.append(f"LOAD_ISSUES ({rep.malformed_count} malformed line(s))")

    sem = rep.semantic
    prompt_paths = sem["prompt"] + sem["conversation"]
    response_paths = sem["response"]
    if not prompt_paths and not response_paths:
        rep.flags.append("NO_PROMPT_RESPONSE_PAIR (aggregate/metadata-only records)")
    elif len(response_paths) < 1 and not any(p in sem["label"] for p in ("label", "labels", "_value")):
        # flat aggregates like kappa/accuracy are not sample records
        if "score" in sem and not prompt_paths:
            rep.flags.append("NO_PROMPT_RESPONSE_PAIR (aggregate results, keys=statistics)")
    if len(response_paths) >= 2:
        rep.flags.append(f"MULTIPLE_CANDIDATE_RESPONSES: {response_paths[:6]}")

    # multiple-choice heuristic
    mc_basis = []
    field_names = set()
    for p, v in rep.nested_paths.items():
        field_names.add(p.rsplit(".", 1)[-1])
    if {"answer_matching_behavior", "answer_not_matching_behavior"} <= field_names:
        mc_basis.append("fields answer_matching_behavior/answer_not_matching_behavior")
    if {"answers", "correct_letter"} & field_names:
        mc_basis.append("fields answers/correct_letter")
    if field_names & {"option", "options", "choices", "pronoun_options"}:
        mc_basis.append("fields options/choices")
    for sample in rep.samples[:5]:
        if re.search(r"\([A-H]\)", sample) and len(re.findall(r"\([A-H]\)", sample)) >= 2:
            mc_basis.append("option letters in prompt text, e.g. (A) (B)")
            break
        if re.search(r"answer with a single letter|choose .* (option|letter)|would you rather", sample, re.IGNORECASE):
            mc_basis.append("multiple-choice phrasing in prompt")
            break
    if mc_basis:
        rep.flags.append(f"MULTIPLE_CHOICE: {mc_basis[0]}")

    # multi-turn heuristic: history/messages/turns/prompt-as-list of >1 item
    multi = []
    for p, v in rep.nested_paths.items():
        name = p.rsplit(".", 1)[-1]
        if name in ("history", "conversation", "dialogue", "dialog", "messages", "turns", "prompt"):
            if isinstance(v, list) and len(v) > 1:
                multi.append(f"{p} (max {len(v)} turns in first record)")
    if multi:
        rep.flags.append(f"MULTI_TURN_CONVERSATION: {', '.join(multi)}")

    if rep.record_count == 0 and not rep.load_error:
        rep.flags.append("EMPTY_FILE")


# --------------------------------------------------------------------------- report assembly
def finalize(rep: FileReport) -> None:
    rep.fields = {k: {"types": sorted(v["types"]), "nested": v["nested"], "present": v["present"]} for k, v in rep.fields.items()}
    classify_semantics(rep)
    detect_flags(rep)


def dataset_group_of(rel: str, top_dirs: set[str]) -> tuple[str, str]:
    parts = rel.replace("\\", "/").split("/")
    top = parts[0]
    second = ""
    subtop = {"model-written-evals": parts[1] if len(parts) > 1 else ""}
    return top, subtop.get(top, "")


def build_markdown(reports: list[FileReport], aux: list[tuple[str, str, int]]) -> str:
    md = ["# Dataset Inspection Report", "", f"_Generated by `scripts/inspect_datasets.py` (read-only). Locations under `dataset/`. {len(reports)} structured data file(s) inspected._", ""]

    md += ["## 1. Summary by source dataset", ""]
    md += ["| source dataset (clone dir) | data files | total records (approx) |", "|---|---:|---:|"]
    order = [
        ("model-written-evals", "Anthropic/model-written-evals (clone)"),
        ("sycophancy", "EleutherAI/sycophancy (clone)"),
        ("sycophancy-datasets", "camilablank/sycophancy-datasets (clone)"),
        ("sycophancy-eval", "meg-tong/sycophancy-eval (clone)"),
        ("sycophancy-false-premises", "schis02/sycophancy-false-premises (clone)"),
    ]
    for dname, label in order:
        group = [r for r in reports if r.dataset_group[0] == dname]
        if not group:
            md.append(f"| **{label}** (`{dname}/`) | 0 (none) | 0 |")
            continue
        tot = sum(r.record_count for r in group)
        md.append(f"| **{label}** (`{dname}/`) | {len(group)} | {tot:,}* |")
    md += ["", "*Exact record counts are reported per file. Counts are for records loadable with stdlib JSON parsing only.", ""]

    md += ["## 2. Files needing special attention", ""]
    flagged = [r for r in reports if r.flags]
    mc_count = sum(1 for r in flagged if any(f.startswith("MULTIPLE_CHOICE") for f in r.flags))
    cand_count = sum(1 for r in flagged if any(f.startswith("MULTIPLE_CANDIDATE_RESPONSES") for f in r.flags))
    md += [
        f"Pervasive patterns (do not need individual attention):",
        f"- **MULTIPLE_CHOICE**: {mc_count} file(s) carry a multiple-choice prompt with 2+ labeled candidate answer fields "
        f"(e.g. `answer_matching_behavior` / `answer_not_matching_behavior`); building an eval load from them requires "
        f"selecting which candidate field(s) count as the sycophantic answer.",
        f"- **MULTIPLE_CANDIDATE_RESPONSES**: {cand_count} file(s) expose more than one plausible response field per record.",
        "",
        "Files below carry content-structural or load flags that matter for mapping:",
    ]
    informative = [r for r in flagged
                   if any(f.startswith(("NO_PROMPT_RESPONSE_PAIR", "MULTI_TURN", "LOAD_ISSUES", "EMPTY_FILE", "PARQUET"))
                          for f in r.flags)]
    if not informative:
        md += ["None."]
    else:
        for r in informative:
            md.append(f"- `{r.rel_path}` — {', '.join(f for f in r.flags if not f.startswith(('MULTIPLE_CHOICE', 'MULTIPLE_CANDIDATE')))}")
            if r.record_count == 0 and r.load_error:
                md.append(f"  - load: {r.load_error}")
    md += ["", "Notable structural findings:", "", ]
    md += [
        "- `sycophancy/sycophancy.py` is a Hugging Face dataset **loader script**, not data: the EleutherAI clone ships no records; "
        "its 3 subsets (sycophancy_on_nlp_survey / philpapers2020 / political_typology_quiz) are downloaded from "
        "`anthropics/evals` at load time and are already present under `model-written-evals/sycophancy/`.",
        "- `sycophancy-datasets/*` records carry a conversation `history` (multi-turn {user, bot}); `mmlu_*` files are the "
        "sycophancy benchmark over MMLU; several files have a small number of malformed lines that the source repo carries "
        "verbatim (not an extraction bug).",
        "- `sycophancy-eval/*.jsonl` wrap source benchmarks in `base.{dataset, question, answer, ...}` plus a chat-formatted "
        "`prompt` list; `answer.jsonl` includes `base.answer` as a list of 2 answer variants.",
        "- `sycophancy-false-premises/*_labeled.jsonl`, `*_completions.jsonl` and `*_labels.json` are paired: prompts referenced "
        "by `prompt_id`/`fact_id` connect completions to labels; several `.json` files are aggregate analysis results "
        "(entropy/kdg/kappa), and `prompt_pressure_labels.json` maps full prompt text to NEUTRAL/LEADIN/SYCOPHANTIC-style labels.",
    ]
    md.append("")

    md += ["## 3. Per-file details", ""]
    for r in reports:
        head = f"### {r.rel_path}"
        if r.dataset_group[1]:
            head += f"  ·  dataset group `{r.dataset_group[1]}/`"
        md += [head, ""]
        md += [f"- **file type**: {r.file_type}"
               f"  \n- **container**: {r.container}"
               f"  \n- **records**: {r.record_count:,} parsed, {r.malformed_count} malformed, {r.blank_count} blank"
               + (f"; encoding {r.encoding_note}" if r.encoding_note else "")]
        if r.flags:
            md += [f"- **flags**: {', '.join(r.flags)}"]
        if r.load_error:
            md += [f"- **load error**: {r.load_error}"]
        if r.fields:
            fld = ", ".join(
                f"`{k}`:{'/'.join(v['types'])}{'*' if v['nested'] else ''}({v['present']})"
                for k, v in sorted(r.fields.items())
            )
            md += [f"- **top-level fields** (* = nested; `(count)` = records with field): {fld}"]
        if r.nested_paths:
            sk = []
            for p, v in list(r.nested_paths.items())[:14]:
                sk.append(f"`{p}` : {sketch(v)}")
            md += [f"- **nested structure (first record)**: {', '.join(sk)}"]
        if r.semantic:
            lines = []
            for role in ("prompt", "response", "conversation", "id", "label", "score", "metadata", "other"):
                vals = r.semantic.get(role, [])
                if vals:
                    lines.append(f"{role}: {', '.join(f'`{p}`' for p in vals[:8])}")
            md += [f"- **semantic field candidates**: {'; '.join(lines)}"]
        md += ["- **sample records**:", ""]
        for s in r.samples:
            md += ["  ```text", f"  {s}", "  ```"]
        for n in r.notes:
            md += [f"- note: {n}"]
        for i in r.issues:
            md += [f"- issue: {i}"]
        md.append("")
    return "\n".join(md)


def build_terminal_summary(reports: list[FileReport], aux: list[tuple[str, str, int]]) -> str:
    order = [
        ("model-written-evals", "Anthropic model-written-evals"),
        ("sycophancy", "EleutherAI/sycophancy"),
        ("sycophancy-datasets", "camilablank/sycophancy-datasets"),
        ("sycophancy-eval", "meg-tong/sycophancy-eval"),
        ("sycophancy-false-premises", "schis02/sycophancy-false-premises"),
    ]
    lines = ["=" * 88, "DATASET INSPECTION — concise summary", "=" * 88]
    for dname, label in order:
        group = [r for r in reports if r.dataset_group[0] == dname]
        if not group:
            lines.append(f"[{label}]  no structured data files found ({len([a for a in aux if aux_dir(dname, a)])} aux file(s))")
            continue
        tot = sum(r.record_count for r in group)
        lines.append(f"\n### {label}  ({len(group)} data file(s), ~{tot:,} records)")
        for r in group:
            flags = ("  [" + "; ".join(r.flags) + "]") if r.flags else ""
            lines.append(f"  - {r.rel_path}  ({r.record_count:,} rec)"
                         + (f", type={r.container}" if r.container not in ("jsonl", "json") else "")
                         + flags)
    lines.append("\nAuxiliary (non-record) files in dataset/:")
    for rel, kind, size in sorted(aux):
        lines.append(f"  - {rel}  ({kind}, {size} KB)")
    flagged = [r for r in reports if r.flags]
    lines.append(f"\n{len(flagged)}/{len(reports)} data file(s) carry flags needing attention; see dataset_inspection_report.md.")
    return "\n".join(lines)


def aux_dir(dname: str, a: tuple[str, str, int]) -> bool:
    return a[0].startswith(dname + "/")


def main() -> None:
    parser = argparse.ArgumentParser(description="Read-only inspection of the dataset/ directory")
    parser.add_argument("--root", type=pathlib.Path, default=ROOT, help="dataset directory (default: ../dataset)")
    parser.add_argument("--report", type=pathlib.Path, default=REPORT, help="output markdown path")
    args = parser.parse_args()

    root = args.root.resolve()
    reports: list[FileReport] = []
    aux: list[tuple[str, str, int]] = []

    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if "__pycache__" in path.parts or ".git" in path.parts:
            continue
        ext = path.suffix.lower()
        rel = path.relative_to(root).as_posix()
        top, second = dataset_group_of(rel, set())
        if ext in DATA_SUFFIXES:
            ftype = DATA_SUFFIXES[ext]
            if ftype == "json":
                rep = inspect_json(path, rel, (top, second))
            elif ftype == "jsonl":
                rep = inspect_jsonl(path, rel, (top, second))
            elif ftype == "csv":
                rep = inspect_csv(path, rel, (top, second), "\t" if ext == ".tsv" else ",")
            elif ftype == "parquet":
                rep = inspect_parquet(path, rel, (top, second))
            finalize(rep)
            reports.append(rep)
        else:
            aux.append((rel, ext.lstrip(".") or "no-ext", int(path.stat().st_size // 1024)))

    reports.sort(key=lambda r: r.rel_path)
    md = build_markdown(reports, aux)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(md, encoding="utf-8")
    sys.stdout.write(build_terminal_summary(reports, aux) + "\n")
    print(f"\nReport written to: {args.report}")


if __name__ == "__main__":
    main()