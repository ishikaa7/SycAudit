"""Inspect the three cloned sycophancy datasets under ``dataset/``.

Read-only inspection only. It never extracts, transforms, samples, annotates,
deletes or rewrites the source data - it reads every data file (JSON, JSONL,
CSV, Parquet) and produces:

- per-file schema/size/sample summaries,
- a semantic "candidate field" analysis (prompt, response, labels, ...),
- explicit flags for shapes that need special extraction logic,
- a full markdown report (``dataset_inspection_report.md``) plus a terminal
  summary.

Handled gracefully instead of crashing: missing files, unreadable/malformed
JSON (L), broken CSVs, and parquet files without a usable engine are reported
with an error note and the inspection continues.

Dependencies: stdlib only, plus the already-installed ``pandas``/``pyarrow``
for Parquet. No extra installs are performed by this script.
"""
from __future__ import annotations

import csv
import io
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

DATASET_DIR = Path(__file__).resolve().parent.parent / "dataset"
REPORT_PATH = Path(__file__).resolve().parent.parent / "dataset_inspection_report.md"

DATASETS = {
    "sycophancy-false-premises": "Dataset 1 — schis02/sycophancy-false-premises",
    "sycophancy-bench": "Dataset 2 — ustaomeroglu/sycophancy-bench",
    "SycoB": "Dataset 3 — JadenGGGeee/SycoB",
}

DATA_EXTENSIONS = {".json", ".jsonl", ".csv", ".parquet"}
DOC_EXTENSIONS = {".md", ".txt", ".rst"}
IGNORED_DIR_NAMES = {".git", ".idea", ".venv", "__pycache__", ".lfs"}

# --- record/chunk budget for inspection (never used to build output data) ---
MAX_ANALYZED_RECORDS = 30
MAX_SAMPLE_RECORDS = 2
MAX_STRING_CHARS = 160
MAX_RECORD_CHARS = 1400


# --------------------------------------------------------------------------
# key categorisation
# --------------------------------------------------------------------------

_CATEGORY_PATTERNS: dict[str, list[str]] = {
    "prompt": [
        r"prompt", r"question", r"\buser\b", r"query", r"instruction",
        r"original", r"\binput\b", r"request", r"premise", r"statement",
    ],
    "response": [
        r"respons", r"answer", r"\boutput\b", r"completion", r"assistant",
        r"generation", r"reply", r"text", r"\bcontent\b",
    ],
    "conversation": [
        r"conversation", r"messages", r"history", r"dialogue", r"turns", r"\bturn\b",
        r"context", r"multiturn",
    ],
    "id": [r"^id$", r"_id", r"\buid\b", r"idx", r"example", r"sample_id", r"key"],
    "label": [
        r"label", r"verdict", r"is[a-z_]*sycoph", r"sycoph", r"agree", r"agreement",
        r"categor", r"class", r"decision", r"judg", r"comply", r"honest",
    ],
    "score": [
        r"score", r"rating", r"reward", r"confidence", r"prob", r"lollipop", r"lolly",
    ],
    "category": [
        r"scenario", r"category", r"domain", r"setting", r"condition", r"split",
        r"\bphase\b", r"\btype\b", r"\bvariant\b", r"dataset",
    ],
    "model": [
        r"model", r"llm", r"generator", r"participant", r"\bprobe\b", r"actor",
        r"speaker", r"judge_model",
    ],
    "pushback": [
        r"pushback", r"correction", r"rebuff", r"counter.?arg", r"factual",
    ],
    "meta": [
        r"wobble", r"stability", r"analysis", r"rationale", r"reason", r"note",
        r"meta", r"created", r"date", r"version", r"seed", r"temperature", r"audit",
    ],
}

_KEY_PATTERNS = {
    name: [re.compile(p, re.IGNORECASE) for p in patterns]
    for name, patterns in _CATEGORY_PATTERNS.items()
}


def categorize_key(name: str) -> set[str]:
    """Return the semantic categories a top-level field name plausibly belongs to."""
    return {cat for cat, patterns in _KEY_PATTERNS.items() if any(p.search(name) for p in patterns)}


# --------------------------------------------------------------------------
# value shape helpers
# --------------------------------------------------------------------------

def _type_name(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "float"
    if isinstance(value, str):
        return "str"
    if isinstance(value, bytes):
        return "bytes"
    if isinstance(value, list):
        elems = value[:5]
        inner = "mixed"
        if elems:
            kinds = {_type_name(e).split(" ", 1)[0] for e in elems}
            inner = "|".join(sorted(kinds)) if len(kinds) > 1 else next(iter(kinds))
        return f"list[{inner}]"
    if isinstance(value, dict):
        keys = list(value.keys())[:8]
        return "dict{" + ",".join(keys) + "}" if keys else "dict{}"
    return type(value).__name__


def nested_structure(value: Any, depth: int = 2) -> str | None:
    """Compact outline of a nested (dict/list) value, or None when not nested."""
    if isinstance(value, dict):
        parts = []
        for k, v in list(value.items())[:10]:
            if isinstance(v, dict):
                parts.append(f"{k}: dict{{{', '.join(list(v.keys())[:6])}}}")
            elif isinstance(v, list):
                parts.append(f"{k}: list[{'dict' if v and isinstance(v[0], dict) else _type_name(v[0]) if v else '?'} ]x{len(v)}")
            else:
                parts.append(f"{k}: {_type_name(v)}")
        return "{" + "; ".join(parts) + ("; ..." if len(value) > 10 else "") + "}"
    if isinstance(value, list):
        if not value:
            return "list[] (empty)"
        head = value[0]
        if isinstance(head, dict):
            inner = "dict{" + ",".join(list(head.keys())[:8]) + "}"
        else:
            inner = _type_name(head)
        return f"list[{inner}] x{len(value)}"
    return None


def _truncate(value: Any, depth: int = 0) -> str:
    """Render ``value`` compactly for a sample record, truncating aggressively."""
    if depth > 3:
        return "..."
    if isinstance(value, str):
        return value if len(value) <= MAX_STRING_CHARS else value[:MAX_STRING_CHARS] + f"…(+{len(value) - MAX_STRING_CHARS}ch)"
    if isinstance(value, dict):
        parts = []
        for k, v in list(value.items())[:10]:
            parts.append(f"{k}={_truncate(v, depth + 1)}")
        return "{" + ", ".join(parts) + ("…" if len(value) > 10 else "") + "}"
    if isinstance(value, list):
        items = [_truncate(v, depth + 1) for v in value[:5]]
        return "[" + ", ".join(items) + (f"…({len(value)} items)" if len(value) > 5 else "") + "]"
    return str(value)


def _render_sample(record: Any) -> str:
    text = _truncate(record)
    if len(text) > MAX_RECORD_CHARS:
        text = text[:MAX_RECORD_CHARS] + "…"
    return text


def _merge_type(existing: str | None, new: str) -> str:
    if existing is None or existing == new:
        return new
    return f"{existing}|{new}"


# --------------------------------------------------------------------------
# per-file inspectors
# --------------------------------------------------------------------------

@dataclass
class FileInspection:
    rel_path: str
    ext: str
    kind: str  # "data" | "doc"
    records: int | None = None
    parse_failures: int = 0
    fields: list[str] = field(default_factory=list)
    field_types: dict[str, str] = field(default_factory=dict)
    field_nested: dict[str, str] = field(default_factory=dict)
    samples: list[str] = field(default_factory=list)
    shape_notes: list[str] = field(default_factory=list)
    flags: set[str] = field(default_factory=set)
    errors: list[str] = field(default_factory=list)
    identified: dict[str, list[str]] = field(default_factory=dict)

    def add_identified(self, key: str, cats: set[str]) -> None:
        for cat in sorted(cats):
            bucket = self.identified.setdefault(cat, [])
            if key not in bucket:
                bucket.append(key)


def _merged_schema(records: list[dict[str, Any]]) -> tuple[list[str], dict[str, str], dict[str, str]]:
    """Union of keys, merged types, and nested-structure descriptions."""
    keys: list[str] = []
    types: dict[str, str] = {}
    nested: dict[str, str] = {}
    dict_unions: dict[str, set[str]] = {}
    dict_order: dict[str, list[str]] = {}
    for rec in records:
        if not isinstance(rec, dict):
            continue
        for k, v in rec.items():
            if k not in keys:
                keys.append(k)
            types[k] = _merge_type(types.get(k), _type_name(v))
            desc = nested_structure(v)
            if desc and k not in nested:
                nested[k] = desc
            if isinstance(v, dict) and v:
                union = dict_unions.setdefault(k, set())
                order = dict_order.setdefault(k, [])
                for kk in v:
                    if kk not in union:
                        union.add(kk)
                        order.append(kk)
    for k, order in dict_order.items():
        if re.fullmatch(r"dict(?:\{[^}]*\})?(?:\|dict(?:\{[^}]*\})?)*", types[k]):
            types[k] = "dict{" + ",".join(order[:8]) + ("…" if len(order) > 8 else "") + "}"
    return keys, types, nested


def inspect_json(path: Path, rel: str) -> FileInspection:
    info = FileInspection(rel_path=rel, ext=path.suffix.lower(), kind="data")
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except Exception as exc:  # noqa: BLE001 - inspection must not crash
        info.errors.append(f"JSON load failed: {type(exc).__name__}: {exc}")
        info.flags.add("cannot_load")
        return info
    analyzed: list[dict[str, Any]] = []
    if isinstance(data, list):
        info.records = len(data)
        analyzed = [r for r in data if isinstance(r, dict)][:MAX_ANALYZED_RECORDS]
        if data and not analyzed:
            info.shape_notes.append(f"list of {len(data)} non-dict items (scalar records)")
            info.samples = [_render_sample(data[i]) for i in range(min(MAX_SAMPLE_RECORDS, len(data)))]
    elif isinstance(data, dict):
        list_values = {k: v for k, v in data.items() if isinstance(v, list)}
        if list_values and len(list_values) == len(data):
            info.records = len(max(list_values.values(), key=len))
            info.shape_notes.append("dict-of-lists payload: each key is a column")
            analyzed = []
            for i in range(min(MAX_ANALYZED_RECORDS, info.records)):
                analyzed.append({k: (v[i] if i < len(v) else None) for k, v in list_values.items()})
        elif data and all(not isinstance(v, (dict, list)) for v in data.values()):
            info.records = len(data)
            str_values = [v for v in data.values() if isinstance(v, str)]
            looks_like_categorical = bool(str_values) and len(str_values) == len(data) and (
                all(len(v) <= 40 for v in str_values)
                and len(set(str_values)) <= max(10, len(data) // 10 + 1)
            )
            if looks_like_categorical:
                info.shape_notes.append(
                    f"dict map payload: {len(data)} key -> value entries; "
                    "keys and short categorical string values sampled"
                )
                analyzed = [{"prompt": k, "label": v} for k, v in list(data.items())[:MAX_ANALYZED_RECORDS]]
            else:
                info.shape_notes.append(
                    f"dict map payload: {len(data)} key -> value entries (non-record map)"
                )
                analyzed = [{"key": k, "value": v} for k, v in list(data.items())[:MAX_ANALYZED_RECORDS]]
        else:
            info.records = 1
            info.shape_notes.append("single dict payload (aggregate/analysis object, not a row dataset)")
            analyzed = [data]
            info.samples = [_render_sample(data)]
    else:
        info.records = 1
        info.fields = []
        info.samples = [_render_sample(data)]
        return info
    info.fields, info.field_types, info.field_nested = _merged_schema(analyzed)
    if not info.samples:
        info.samples = [_render_sample(r) for r in analyzed[:MAX_SAMPLE_RECORDS]]
    for rec in analyzed:
        if isinstance(rec, dict):
            for key in rec:
                info.add_identified(key, categorize_key(key))
    return info


def inspect_jsonl(path: Path, rel: str) -> FileInspection:
    info = FileInspection(rel_path=rel, ext=path.suffix.lower(), kind="data")
    total_lines = 0
    valid: list[dict[str, Any]] = []
    try:
        with open(path, encoding="utf-8") as fh:
            for lineno, raw in enumerate(fh, 1):
                line = raw.strip()
                if not line:
                    continue
                total_lines += 1
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError as exc:
                    info.parse_failures += 1
                    if len(info.errors) < 5:
                        info.errors.append(
                            f"line {lineno}: malformed JSONL ({exc.msg}); skipped"
                        )
                    continue
                if isinstance(obj, dict):
                    valid.append(obj)
    except Exception as exc:  # noqa: BLE001
        info.errors.append(f"JSONL read failed: {type(exc).__name__}: {exc}")
        info.flags.add("cannot_load")
        return info
    info.records = len(valid)
    if info.parse_failures:
        info.shape_notes.append(f"{info.parse_failures} of {total_lines} non-empty lines failed to parse")
        info.flags.add("partial_load")
    analyzed = valid[:MAX_ANALYZED_RECORDS]
    info.fields, info.field_types, info.field_nested = _merged_schema(analyzed)
    info.samples = [_render_sample(r) for r in analyzed[:MAX_SAMPLE_RECORDS]]
    for rec in analyzed:
        for key in rec:
            info.add_identified(key, categorize_key(key))
    return info


def inspect_csv(path: Path, rel: str) -> FileInspection:
    info = FileInspection(rel_path=rel, ext=path.suffix.lower(), kind="data")
    try:
        with open(path, encoding="utf-8-sig", newline="") as fh:
            reader = csv.DictReader(fh)
            if reader.fieldnames is None:
                info.errors.append("CSV has no header row")
                info.flags.add("cannot_load")
                return info
            info.fields = list(reader.fieldnames)
            rows: list[dict[str, Any]] = []
            count = 0
            for row in reader:
                count += 1
                if count <= MAX_ANALYZED_RECORDS:
                    rows.append(row)
            info.records = count
    except Exception as exc:  # noqa: BLE001
        info.errors.append(f"CSV read failed: {type(exc).__name__}: {exc}")
        info.flags.add("cannot_load")
        return info
    info.field_types, info.field_nested = {}, {}
    for row in rows:
        for k in info.fields:
            v = row.get(k)
            info.field_types[k] = _merge_type(info.field_types.get(k), _type_name(v))
            desc = nested_structure(v) if v else None
            if desc and k not in info.field_nested:
                info.field_nested[k] = desc
    info.samples = [_render_sample(row) for row in rows[:MAX_SAMPLE_RECORDS]]
    for row in rows:
        for key in row:
            info.add_identified(key, categorize_key(key))
    return info


def inspect_parquet(path: Path, rel: str) -> FileInspection:
    info = FileInspection(rel_path=rel, ext=path.suffix.lower(), kind="data")
    try:
        import pyarrow.parquet as pq
    except Exception as exc:  # noqa: BLE001
        info.errors.append(f"parquet engine unavailable: {type(exc).__name__}: {exc}")
        info.flags.add("cannot_load")
        return info
    try:
        pf = pq.ParquetFile(path)
        info.records = pf.metadata.num_rows
        schema = pf.schema_arrow
        for field in schema:
            info.fields.append(field.name)
            info.field_types[field.name] = str(field.type)
            type_str = str(field.type)
            if type_str.startswith(("list<", "struct<")):
                info.field_nested[field.name] = type_str
        table = pf.read_row_group(0)
        records = table.to_pylist()
        if records:
            info.samples = [_render_sample(r) for r in records[:MAX_SAMPLE_RECORDS]]
            for rec in records[:MAX_ANALYZED_RECORDS]:
                for key in rec:
                    info.add_identified(key, categorize_key(key))
    except Exception as exc:  # noqa: BLE001
        info.errors.append(f"parquet read failed: {type(exc).__name__}: {exc}")
        info.flags.add("cannot_load")
    return info


INSPECTORS = {".json": inspect_json, ".jsonl": inspect_jsonl, ".csv": inspect_csv, ".parquet": inspect_parquet}


def _collect_flags(info: FileInspection) -> None:
    response_keys = sorted(set(info.identified.get("response", [])))
    if len(response_keys) >= 2:
        info.flags.add("multiple_response_fields")
    if info.identified.get("conversation") or "multiturn" in info.rel_path.lower():
        info.flags.add("conversation_multiturn")
    if any(re.search(r"choice|option|letter|correct", k, re.IGNORECASE) for k in info.fields):
        info.flags.add("multiple_choice")
    has_label = bool(info.identified.get("label") or info.identified.get("score"))
    if not response_keys and has_label:
        info.flags.add("response_via_rubric_label")
    if info.identified.get("category"):
        info.flags.add("has_categories")
    if info.identified.get("pushback"):
        info.flags.add("has_pushback_corrections")
    if any(info.field_nested.values()):
        info.flags.add("nested_values")
    if info.flags - {"nested_values"}:
        info.flags.add("special_extraction")


def scan_datasets(dataset_dir: Path) -> dict[str, list[FileInspection]]:
    results: dict[str, list[FileInspection]] = {}
    if not dataset_dir.is_dir():
        print(f"ERROR: dataset directory not found: {dataset_dir}")
        sys.exit(1)
    try:
        entries = list(dataset_dir.iterdir())
    except OSError as exc:
        print(f"ERROR: cannot read {dataset_dir}: {exc}")
        sys.exit(1)
    for dataset_name in DATASETS:
        results.setdefault(dataset_name, [])
    for root, dirs, files in os_walk(dataset_dir):
        dirs[:] = [d for d in dirs if d not in IGNORED_DIR_NAMES]
        for name in sorted(files):
            p = Path(root) / name
            rel = p.relative_to(dataset_dir).as_posix()
            owner = rel.split("/", 1)[0]
            if owner not in DATASETS:
                continue
            ext = p.suffix.lower()
            made = False
            if ext in DATA_EXTENSIONS:
                made = True
                info = INSPECTORS[ext](p, rel)
                _collect_flags(info)
                results[owner].append(info)
            elif ext in DOC_EXTENSIONS:
                made = True
                info = FileInspection(rel_path=rel, ext=ext, kind="doc")
                try:
                    with open(p, encoding="utf-8", errors="replace") as fh:
                        first_line = fh.readline().strip()[:160]
                    info.shape_notes.append(f"documentation ({name == 'README.md' and 'README' or ext.lstrip('.').upper()}); first line: {first_line or '(empty)'}")
                except Exception as exc:  # noqa: BLE001
                    info.errors.append(f"read failed: {type(exc).__name__}: {exc}")
                results[owner].append(info)
            if not made:
                results[owner].append(
                    FileInspection(rel_path=rel, ext=ext, kind="doc",
                                   shape_notes=["not a data/doc extension; ignored"])
                )
    return results


def os_walk(base: Path):
    stack = [base]
    while stack:
        current = stack.pop()
        dirs, files = [], []
        try:
            for entry in sorted(current.iterdir(), key=lambda e: e.name.lower()):
                if entry.is_dir():
                    if entry.name not in IGNORED_DIR_NAMES:
                        dirs.append(entry.name)
                else:
                    files.append(entry.name)
        except OSError:
            continue
        yield current, dirs, files
        for d in sorted(dirs, reverse=True):
            stack.append(current / d)


# --------------------------------------------------------------------------
# dataset-level aggregation
# --------------------------------------------------------------------------

@dataclass
class DatasetSummary:
    name: str
    display: str
    files: list[FileInspection]

    @property
    def data_files(self) -> list[FileInspection]:
        return [f for f in self.files if f.kind == "data"]

    @property
    def doc_files(self) -> list[FileInspection]:
        return [f for f in self.files if f.kind == "doc"]

    @property
    def approximate_records(self) -> int:
        return sum(f.records or 0 for f in self.data_files)

    def _candidate(self, category: str) -> list[tuple[str, int, list[FileInspection]]]:
        counts: dict[str, int] = {}
        where: dict[str, list[FileInspection]] = {}
        if category == "prompt":
            exclude = lambda k: "id" in categorize_key(k)
        elif category == "response":
            exclude = lambda k: bool({"id", "prompt"} & categorize_key(k))
        else:
            exclude = None
        for f in self.data_files:
            for key in f.identified.get(category, []):
                if exclude and exclude(key):
                    continue
                counts[key] = counts.get(key, 0) + 1
                where.setdefault(key, []).append(f)
        return sorted(
            ((k, c, w) for k, c, w in ((k, c, where[k]) for k, c in counts.items())),
            key=lambda t: (-t[1], t[0]),
        )

    def strongest(self, category: str) -> str | None:
        ranked = self._candidate(category)
        return ranked[0][0] if ranked else None

    @property
    def has_context(self) -> bool:
        return any(f.identified.get("conversation") for f in self.data_files) or any(
            "multiturn" in f.rel_path.lower() for f in self.data_files
        )

    @property
    def has_label(self) -> bool:
        return any(f.identified.get("label") or f.identified.get("score") for f in self.data_files)

    @property
    def special_flags(self) -> set[str]:
        out: set[str] = set()
        for f in self.data_files:
            out |= {flag for flag in f.flags if flag != "special_extraction"}
        return out


# --------------------------------------------------------------------------
# report rendering
# --------------------------------------------------------------------------

def _severity(errors: list[str]) -> str:
    return "ERROR: " + "; ".join(errors) if errors else ""


def _flags_text(info: FileInspection) -> str:
    if not info.flags:
        return "—"
    return ", ".join(sorted(info.flags))


def _rows_field(info: FileInspection) -> str:
    if info.records is None:
        return "n/a"
    base = str(info.records)
    if info.parse_failures:
        base += f" ({info.parse_failures} skipped)"
    return base


def _cap_keys(keys: list[str], limit: int = 12) -> str:
    if len(keys) <= limit:
        return ", ".join(keys)
    return ", ".join(keys[:limit]) + f"…(+{len(keys) - limit} more)"


def _write_file_details(md: list[str], info: FileInspection) -> None:
    md.append(f"#### `{info.rel_path}`")
    md.append("")
    if info.kind == "doc":
        md.append("- **kind**: non-record file (documentation/analysis output)")
        for note in info.shape_notes:
            md.append(f"- **note**: {note}")
        if info.errors:
            md.append(f"- **errors**: {_severity(info.errors)}")
        md.append("")
        return
    md.append(f"- **file type**: {info.ext.lstrip('.')} ")
    md.append(f"- **records/rows**: {_rows_field(info)}")
    if info.shape_notes:
        md.append("- **shape notes**: " + "; ".join(info.shape_notes))
    md.append(f"- **flags**: {_flags_text(info)}")
    if info.field_types:
        md.append("- **fields (name : type)** :")
        for name in info.fields:
            line = f"    - `{name}` : {info.field_types.get(name, '?')}"
            if name in info.field_nested:
                line += f"  — nested: `{info.field_nested[name]}`"
            md.append(line)
    elif info.fields:
        md.append(f"- **fields**: {', '.join(info.fields)}")
    if info.identified:
        md.append("- **identified semantics**: "
                  + "; ".join(f"{cat}: {_cap_keys(v)}" for cat, v in sorted(info.identified.items())))
    if info.samples:
        md.append("- **sample records** (truncated):")
        for i, sample in enumerate(info.samples, 1):
            md.append(f"    - record {i}: `{sample}`")
    if info.errors:
        md.append(f"- **load status**: {_severity(info.errors)}")
    md.append("")


def render_markdown(results: dict[str, list[FileInspection]]) -> str:
    md: list[str] = []
    md.append("# Sycophancy Dataset Inspection")
    md.append("")
    md.append("Generated by `scripts/inspect_datasets.py` — inspection only. No source data was modified.")
    md.append("")
    md.append("## Overview")
    md.append("")
    md.append("| Dataset | Data files | Doc files | Approx. records |")
    md.append("| --- | ---: | ---: | ---: |")
    summaries: list[DatasetSummary] = []
    for name, display in DATASETS.items():
        files = results.get(name, [])
        summary = DatasetSummary(name=name, display=display, files=files)
        summaries.append(summary)
        md.append(f"| {display} | {len(summary.data_files)} | {len(summary.doc_files)} | ~{summary.approximate_records} |")
    md.append("")

    for summary in summaries:
        md.append(f"# {summary.display}")
        md.append("")
        md.append("## files")
        md.append("")
        for f in summary.files:
            kind = "data" if f.kind == "data" else "doc"
            md.append(f"- `{f.rel_path}` ({kind})")
        md.append("")
        md.append("## schema")
        md.append("")
        for f in summary.data_files:
            _write_file_details(md, f)
        md.append("## sample records")
        md.append("")
        md.append("Shown inline within each file section above.")
        md.append("")
        md.append("## candidate prompt field")
        md.append("")
        candidate = summary.strongest("prompt")
        if candidate:
            ranked = summary._candidate("prompt")
            alternatives = ", ".join(k for k, _, _ in ranked[1:4])
            md.append(f"**Primary:** `{candidate}`  (strongest = most files use it)")
            if alternatives:
                md.append(f"**Alternatives:** {alternatives}")
        else:
            md.append("No field clearly matches a prompt/question role across files.")
        md.append("")
        md.append("## candidate response field")
        md.append("")
        candidate = summary.strongest("response")
        if candidate:
            ranked = summary._candidate("response")
            alternatives = ", ".join(k for k, _, _ in ranked[1:4])
            md.append(f"**Primary:** `{candidate}`  (strongest = most files use it)")
            if alternatives:
                md.append(f"**Alternatives:** {alternatives}")
        else:
            md.append("No field clearly matches a response/output role across files.")
        md.append("")
        md.append("## useful metadata")
        md.append("")
        meta: dict[str, set[str]] = {"id": set(), "label": set(), "score": set(), "category": set(), "model": set(), "pushback": set(), "conversation": set(), "meta": set()}
        for f in summary.data_files:
            for cat, keys in f.identified.items():
                if cat in meta:
                    meta[cat] |= set(keys)
        md.append("| Aspect | Candidate fields |")
        md.append("| --- | --- |")
        for cat, keys in sorted(meta.items()):
            md.append(f"| {cat} | {'None found' if not keys else ', '.join(sorted(keys))} |")
        md.append("")
        md.append("## extraction considerations")
        md.append("")
        md.append("| File | Flags / considerations |")
        md.append("| --- | --- |")
        for f in summary.data_files:
            bits = []
            flags = ", ".join(sorted(f.flags)) if f.flags else "none notable"
            bits.append(flags)
            if f.parse_failures:
                bits.append(f"{f.parse_failures} unparsed lines")
            if not f.identified.get("response") and f.records:
                bits.append("no response-like field detected")
            errs = "; ".join(f.errors) if f.errors else ""
            if errs:
                bits.append(f"ERROR: {errs}")
            md.append(f"| `{f.rel_path}` | {('; '.join(bits)) or '—'} |")
        md.append("")

    # conclusion: per-dataset new shape flags
    md.append("# Comparison")
    md.append("")
    md.append("| Dataset | Files | Approx. Records | Prompt Field | Response Field | Has Context? | Has Sycophancy Label? | Special Handling? |")
    md.append("| ------- | ----- | --------------: | ------------ | -------------- | ------------ | --------------------- | ----------------- |")
    for summary in summaries:
        flags = sorted(summary.special_flags) if summary.special_flags else "None"
        md.append(
            f"| {summary.display} | {len(summary.data_files)} | ~{summary.approximate_records} "
            f"| {summary.strongest('prompt') or '—'} | {summary.strongest('response') or '—'} "
            f"| {'Yes' if summary.has_context else 'No'} | {'Yes' if summary.has_label else 'No'} "
            f"| {flags} |"
        )
    md.append("")
    return "\n".join(md)


def terminal_summary(summaries: list[DatasetSummary]) -> None:
    def w(text: str) -> None:
        # sanitise non-ascii glyphs for cp1252 terminals; the .md keeps UTF-8
        print(text.replace("\u2014", "-"))

    w("=" * 78)
    w("SYCOPHANCY DATASET INSPECTION - SUMMARY")
    w("=" * 78)
    for summary in summaries:
        w("")
        w(f"{summary.display}")
        w(f"  data files: {len(summary.data_files)}  doc files: {len(summary.doc_files)}  approx records: ~{summary.approximate_records}")
        top = {cat: summary.strongest(cat) for cat in ("prompt", "response", "label", "conversation")}
        w(f"  primary prompt field : {top['prompt']}")
        w(f"  primary response field: {top['response']}")
        w(f"  has context/multiturn : {'Yes' if summary.has_context else 'No'}")
        w(f"  has label/score field : {'Yes' if summary.has_label else 'No'}")
        flagged = [f.rel_path for f in summary.data_files if f.flags]
        errored = [f.rel_path for f in summary.data_files if f.errors]
        w(f"  flagged files: {len(flagged)}  files with load errors: {len(errored)}")
        for f in summary.data_files:
            if f.errors:
                w(f"    ERROR {f.rel_path}: {'; '.join(f.errors)[:140]}")
        special = sorted(summary.special_flags)
        if special:
            w(f"  special handling needed: {', '.join(special)}")
    w("")
    w("Report written to: " + str(REPORT_PATH))
    w("NOTE: analysis-only run; no data was extracted, transformed or sampled.")


def main(argv: list[str]) -> int:
    dataset_dir = Path(argv[0]) if argv else DATASET_DIR
    results = scan_datasets(dataset_dir)
    summaries = [DatasetSummary(name=name, display=display, files=results.get(name, []))
                 for name, display in DATASETS.items()]
    report = render_markdown(results)
    try:
        REPORT_PATH.write_text(report, encoding="utf-8")
    except OSError as exc:
        print(f"WARNING: could not write report: {exc}")
    terminal_summary(summaries)
    return 0


if __name__ == "__main__":
    main(sys.argv[1:])