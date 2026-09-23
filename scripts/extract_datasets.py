"""Dataset extraction + controlled selection for the 2,100-record audit corpus.

Pipeline (extraction -> validation -> deduplication -> deterministic selection):

  1. Run the three dataset extractors (ds1/ds2/ds3) and collect canonical
     internal records.
  2. Validate every record (missing/empty prompt or response, malformed nested
     structure, invalid response types, template-marker residue). VALID and
     WARNING records become candidates; INVALID records are written to
     dataset/extracted/extraction_errors.jsonl and are never selected.
  3. Detect duplicate candidates within each dataset (exact source identity,
     exact prompt+response, normalized prompt+response). Representatives are
     kept for selection; non-representatives are reported in
     dataset/extracted/duplicate_report.jsonl and never deleted.
  4. Select exactly TARGET_PER_DS (700) records per dataset using the
     Diversity-First Greedy algorithm (see select_diverse). Selection prefers
     VALID records; needs_review cleaning cases are eligible only as a
     fallback.
  5. Assert the final counts and emit dataset/selected/*_700.jsonl plus the
     unified_2100.jsonl corpus and selection_report.md.

Determinism: SEED=42, records are sorted by a stable key before a seeded
Mersenne-Twister shuffle, and no timestamps/UUIDs enter any output record.

Reads/writes: this script only READS dataset/<source-repos> and only WRITES
under dataset/extracted/ and dataset/selected/.
"""

import csv
import json
import os
import random
import sys
from collections import Counter, defaultdict

from extractors import (
    clean_text_value,
    contains_template_marker,
    derive_source_id,
    normalize_text,
)
from extractors.ds1_false_premises import extract_ds1
from extractors.ds2_sycophancy_bench import extract_ds2
from extractors.ds3_sycob import extract_ds3

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "dataset")
EXTRACTED_DIR = os.path.join(DATA_DIR, "extracted")
SELECTED_DIR = os.path.join(DATA_DIR, "selected")

TARGET_PER_DS = 700
UNIFIED_TARGET = 3 * TARGET_PER_DS  # 2100
SEED = 42

DATASET_LABELS = {
    "ds1": "DS1 sycophancy-false-premises",
    "ds2": "DS2 sycophancy-bench",
    "ds3": "DS3 SycoB",
}


# --------------------------------------------------------------------------
# Validation
# --------------------------------------------------------------------------

def validate_record(rec):
    """Return (status, warnings). Status is INVALID only when unselectable."""
    warnings = []

    prompt = rec.get("prompt")
    response = rec.get("response")

    if prompt is None or not isinstance(prompt, str) or not prompt.strip():
        return "INVALID", [{"error_type": "missing_prompt",
                            "error_message": "record has no usable prompt"}]
    if response is None or not isinstance(response, str) or not response.strip():
        return "INVALID", [{"error_type": "missing_response",
                            "error_message": "record has no usable response"}]

    if contains_template_marker(response):
        warnings.append({"error_type": "response_contains_prompt_scaffolding",
                         "error_message": "cleaned response still contains a chat-template marker"})

    for key in ("temperature", "seed", "sample_idx", "turn_index"):
        val = rec.get(key)
        if val is not None and not isinstance(val, (int, float)):
            warnings.append({"error_type": "unexpected_data_type",
                             "error_message": "%s has non-numeric value %r" % (key, val)})

    return ("WARNING" if warnings else "VALID"), warnings


# --------------------------------------------------------------------------
# Duplicate detection
# --------------------------------------------------------------------------

def duplicate_groups(records):
    """Group records with identical normalized (prompt, response)."""
    groups = defaultdict(list)
    for rec in records:
        key = (
            normalize_text(rec.get("prompt")),
            normalize_text(rec.get("response")),
        )
        groups[key].append(rec)
    return {k: v for k, v in groups.items() if len(v) > 1}


def _dup_type(rep, other):
    same_src = (rep["source_file"] == other["source_file"]
                and rep["source_id"] == other["source_id"])
    if same_src:
        return "exact_source"
    if (rep["prompt"] == other["prompt"] and rep["response"] == other["response"]):
        return "exact_prompt_response"
    return "normalized_prompt_response"


# --------------------------------------------------------------------------
# Diversity-First Greedy selection
# --------------------------------------------------------------------------

def feature_value(rec, dim):
    val = rec.get(dim)
    if isinstance(val, bool):
        return "bool:%s" % val
    if isinstance(val, (int, float)):
        return "num:%s" % val
    if isinstance(val, str) and val.strip():
        return "str:%s" % val.strip()
    return "none"


def _stable_key(rec):
    return (rec.get("source_file") or "",
            rec.get("source_id") or "",
            str(rec.get("turn_index") or ""),
            clean_text_value(rec.get("variant")),
            clean_text_value(rec.get("prompt")))


def select_diverse(records, k, dims, group_fn, group_cap, seed=SEED):
    """Diversity-First Greedy (profile level-greedy) selection.

    Deterministic and seeded (seed); returns exactly k records.

    Strategy:
      1. each candidate gets a "profile" = tuple of its dimension feature values
      2. records are stable-sorted then seeded-shuffled (reproducible order)
      3. a level starts at 0; scan the order and accept every record whose
         profile already has <= level selected members and whose selection group
         (fact_id / conversation_id / prompt_id) is under group_cap
      4. when a scan adds nothing, increment the level; stop at exactly k

    Balancing across profiles balances each underlying dimension too, so no
    single model / scenario / framing / variant / style / split can dominate.
    The result is re-normalized to a canonical (stable) order by the caller, so
    the final file order is deterministic regardless of internals.
    """
    order = sorted(records, key=_stable_key)
    rng = random.Random(seed)
    # stable seeded permutation of indices to keep determinism explicit
    idx = list(range(len(order)))
    rng.shuffle(idx)

    # profile_of[p] is the profile of order[p] (looked up by actual position, so
    # the level check always counts members of the same profile as the record)
    profile_of = [tuple(feature_value(order[p], dim) for dim in dims)
                  for p in range(len(order))]
    selected = []
    selected_ids = set()
    profile_counts = Counter()
    group_counts = Counter()
    level = 0

    while len(selected) < k:
        progress = False
        for p in idx:
            rec = order[p]
            if id(rec) in selected_ids:
                continue
            g = group_fn(rec)
            if group_counts[g] >= group_cap:
                continue
            prof = profile_of[p]
            if profile_counts[prof] <= level:
                selected.append(rec)
                selected_ids.add(id(rec))
                profile_counts[prof] += 1
                group_counts[g] += 1
                progress = True
                if len(selected) >= k:
                    break
        if len(selected) >= k:
            break
        if not progress:
            level += 1
            if level > len(order):  # safety: cycle with level>pool is impossible
                break

    if len(selected) < k:
        raise RuntimeError(
            "cannot select %d records from pool of %d (check caps/pool sizes)"
            % (k, len(order))
        )
    return selected


# --------------------------------------------------------------------------
# Output helpers
# --------------------------------------------------------------------------

def write_jsonl(path, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def selected_schema(rec, seq):
    """Emit the final selected-record row (f1..f5 always None)."""
    out = {
        "id": "%s-%06d" % (rec["source_dataset"], seq),
        "source_dataset": rec["source_dataset"],
        "source_file": rec["source_file"],
        "source_id": rec["source_id"],
        "prompt": rec["prompt"],
        "response": rec["response"],
        "f1": None, "f2": None, "f3": None, "f4": None, "f5": None,
        "context": rec.get("context"),
        "conversation_id": rec.get("conversation_id"),
        "turn_index": rec.get("turn_index"),
        "model": rec.get("model"),
        "model_id": rec.get("model_id"),
        "scenario": rec.get("scenario"),
        "category": rec.get("category"),
        "framing": rec.get("framing"),
        "stance_level": rec.get("stance_level"),
        "variant": rec.get("variant"),
        "style": rec.get("style"),
        "split": rec.get("split"),
        "temperature": rec.get("temperature"),
        "seed": rec.get("seed"),
        "sample_idx": rec.get("sample_idx"),
        "gpt4o_label": rec.get("gpt4o_label"),
        "human_label": rec.get("human_label"),
        "ablation_label": rec.get("ablation_label"),
        "turn_judgments": rec.get("turn_judgments"),
        "judge_raw_responses": rec.get("judge_raw_responses"),
        "ground_truth": rec.get("ground_truth"),
        "knowledge_correct_letter": rec.get("knowledge_correct_letter"),
        "knowledge_model_choice": rec.get("knowledge_model_choice"),
        "knowledge_knows_correct": rec.get("knowledge_knows_correct"),
        "knowledge_raw_response": rec.get("knowledge_raw_response"),
        "is_paper1_bridge": rec.get("is_paper1_bridge"),
        "annotations": rec.get("annotations") or {},
        "metadata": rec.get("metadata") or {},
    }
    return out


def count_distribution(records, key):
    counter = Counter()
    for rec in records:
        val = rec.get(key)
        if val is None:
            val = "(none)"
        counter[val] += 1
    return counter


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------

def main():
    os.makedirs(EXTRACTED_DIR, exist_ok=True)
    os.makedirs(SELECTED_DIR, exist_ok=True)

    extractors = {
        "ds1": extract_ds1,
        "ds2": extract_ds2,
        "ds3": extract_ds3,
    }

    all_errors = []
    file_summaries = {}
    per_ds_records = {}

    for ds_name, extractor in extractors.items():
        records, errors, summary = extractor(DATA_DIR)
        file_summaries[ds_name] = summary

        # Validation pass: INVALID -> errors, not candidates.
        valid_records = []
        for rec in records:
            status, warns = validate_record(rec)
            if status == "INVALID":
                errors.append({
                    "source_dataset": ds_name,
                    "source_file": rec["source_file"],
                    "source_id": rec["source_id"],
                    "error_type": warns[0]["error_type"] if warns else "invalid_record",
                    "error_message": warns[0]["error_message"] if warns else "record invalid",
                })
                continue
            rec["record_status"] = status
            rec["warnings"] = (rec.get("warnings") or []) + [w for w in warns if w not in (rec.get("warnings") or [])]
            valid_records.append(rec)

        per_ds_records[ds_name] = valid_records
        for err in errors:
            err["level"] = "invalid" if err.get("error_type", "invalid").startswith(("invalid", "missing", "malformed")) else "warning"
            all_errors.append(err)

    # Write extraction errors report.
    write_jsonl(os.path.join(EXTRACTED_DIR, "extraction_errors.jsonl"), all_errors)

    # ---- per-dataset dedupe + selection ----
    selection_report = {
        "pipeline": "Diversity-First Greedy selection (seed=%d, target=%d per dataset)" % (SEED, TARGET_PER_DS),
        "seed": SEED,
        "datasets": {},
    }

    unified = []
    terminal_rows = []
    duplicate_candidate_total = 0
    all_dup_rows = []

    for ds_name in ("ds1", "ds2", "ds3"):
        records = per_ds_records[ds_name]
        for rec in records:
            rec["record_status"] = rec.get("record_status") or "VALID"

        # Duplicate detection (report-level; nothing is deleted).
        groups = duplicate_groups(records)
        dup_rows = []
        representatives = []
        group_members = set()
        for key, group in groups.items():
            ordered = sorted(group, key=_stable_key)
            rep = ordered[0]
            representatives.append(rep)
            group_members.update(id(r) for r in ordered)
            for other in ordered[1:]:
                dup_rows.append({
                    "source_dataset": ds_name,
                    "source_file": other["source_file"],
                    "source_id": other["source_id"],
                    "duplicate_type": _dup_type(rep, other),
                    "duplicate_of": {
                        "source_file": rep["source_file"],
                        "source_id": rep["source_id"],
                        "source_id_full": derive_source_id(rep),
                    },
                })
        # Non-duplicate members: any record not part of a duplicate group.
        non_dup = [r for r in records if id(r) not in group_members]
        selectable = representatives + non_dup
        duplicate_candidate_total += len(records) - len(selectable)
        all_dup_rows.extend(dup_rows)

        write_jsonl(os.path.join(EXTRACTED_DIR, "%s_candidates.jsonl" % ds_name), records)

        # Selection: prefer VALID and cleaned responses; needs_review fallback only.
        primary = [r for r in selectable if r["record_status"] == "VALID"
                   and r.get("response_cleaning_status") != "needs_review"]
        primary_ids = {id(r) for r in primary}
        fallback = [r for r in selectable if id(r) not in primary_ids]

        if len(primary) + len(fallback) < TARGET_PER_DS:
            raise RuntimeError(
                "only %d selectable candidates for %s (need %d) -> aborting, no cross-dataset filling"
                % (len(primary) + len(fallback), ds_name, TARGET_PER_DS)
            )

        dim_names = {
            "ds1": ["model", "framing", "category", "is_paper1_bridge",
                    "source_file", "split"],
            "ds2": ["model", "scenario", "split", "turn_index", "source_file"],
            "ds3": ["variant", "style", "stance_level", "scenario", "split"],
        }[ds_name]
        dims = dim_names

        def group_fn_ds(rec):
            if ds_name == "ds1":
                return rec.get("fact_id") or rec.get("prompt_id") or rec["source_id"]
            if ds_name == "ds2":
                return (rec.get("conversation_id"), rec.get("model_id"))
            return rec.get("conversation_id") or rec.get("prompt_id") or rec["source_id"]

        group_cap = {"ds1": 12, "ds2": 3, "ds3": 6}[ds_name]

        # Run the greedy on a copy that includes a pseudo-dim for provenance.
        selected = select_diverse(primary, TARGET_PER_DS, dims, group_fn_ds, group_cap, seed=SEED)
        if len(selected) < TARGET_PER_DS:
            raise RuntimeError(
                "selection reached only %d/%d for %s with primary pool; aborting"
                % (len(selected), TARGET_PER_DS, ds_name)
            )

        # deterministic final ordering by stable key
        selected.sort(key=_stable_key)
        selected_rows = [selected_schema(rec, i + 1) for i, rec in enumerate(selected)]
        write_jsonl(os.path.join(SELECTED_DIR, "%s_700.jsonl" % ds_name), selected_rows)
        unified.extend(selected_rows)

        # distribution summary for the report
        dists = {d: dict(count_distribution(selected, d).most_common()) for d in dims}

        models = sorted({(r.get("model") or r.get("model_id") or "") for r in selected})
        scenarios = sorted({(r.get("scenario") or r.get("category") or "(none)") for r in selected})
        selection_report["datasets"][ds_name] = {
            "candidates": len(records),
            "selectable_unique": len(selectable),
            "selected": len(selected_rows),
            "target": TARGET_PER_DS,
            "models": models,
            "scenarios": scenarios,
            "group_cap": group_cap,
            "dimensions": dists,
        }

        terminal_rows.append((ds_name, len(records), len(selected_rows)))

    # Aggregate duplicate report across all datasets (single file).
    write_jsonl(os.path.join(EXTRACTED_DIR, "duplicate_report.jsonl"), all_dup_rows)

    # ---- unified 2100 ----
    assert len(unified) == UNIFIED_TARGET, "unified corpus must have exactly %d rows" % UNIFIED_TARGET
    for ds_name in ("ds1", "ds2", "ds3"):
        sel = [r for r in unified if r["source_dataset"] == ds_name]
        assert len(sel) == TARGET_PER_DS, "%s must have exactly %d selected" % (ds_name, TARGET_PER_DS)
        for row in sel:
            assert row["f1"] is None and row["f2"] is None and row["f3"] is None \
                and row["f4"] is None and row["f5"] is None, "f1..f5 must be None"
    write_jsonl(os.path.join(SELECTED_DIR, "unified_2100.jsonl"), unified)

    # ---- summary json ----
    n_invalid = sum(1 for e in all_errors if e.get("level") == "invalid")
    n_warning = sum(1 for e in all_errors if e.get("level") == "warning")
    summary_json = {
        "seed": SEED,
        "target_per_dataset": TARGET_PER_DS,
        "unified_target": UNIFIED_TARGET,
        "files_processed": {k: v["files_processed"] for k, v in file_summaries.items()},
        "records_read": {k: v["records_read"] for k, v in file_summaries.items()},
        "records_extracted": {k: v["records_extracted"] for k, v in file_summaries.items()},
        "records_invalid": n_invalid,
        "records_with_warnings": n_warning,
        "duplicate_candidates": duplicate_candidate_total,
        "selected": {k: {"selected": len([r for r in unified if r["source_dataset"] == k])} for k in ("ds1", "ds2", "ds3")},
    }
    write_jsonl(os.path.join(EXTRACTED_DIR, "extraction_summary.json"), [summary_json])

    # ---- selection report ----
    report_path = os.path.join(SELECTED_DIR, "selection_report.md")
    with open(report_path, "w", encoding="utf-8") as fh:
        fh.write("# Selection Report\n\n")
        fh.write("Pipeline: Diversity-First Greedy selection (seed=%d, target=%d per dataset)\n\n" % (SEED, TARGET_PER_DS))
        fh.write("Algorithm: profile level-greedy. Each candidate gets a \"profile\" = tuple of its\n")
        fh.write("dimension values. Records are stable-sorted then seeded-shuffled. A level starts at 0;\n")
        fh.write("scan the order and accept every record whose profile already has <= level selected\n")
        fh.write("members and whose selection group (fact_id / conversation_id / prompt_id) is under the\n")
        fh.write("group cap; when a scan adds nothing, increment the level; stop at exactly %d.\n" % TARGET_PER_DS)
        fh.write("This keeps every model / scenario / framing / variant / style represented without any\n")
        fh.write("single condition dominating the result. Determinism: fixed seed=%d, stable tie-breaking,\n" % SEED)
        fh.write("no timestamps or UUIDs.\n\n")
        fh.write("## Overall\n\n")
        fh.write("| Dataset | Candidates | Selectable unique | Selected | Target | Models | Scenarios |\n")
        fh.write("|---|---|---|---|---|---|---|\n")
        for ds in ("ds1", "ds2", "ds3"):
            info = selection_report["datasets"][ds]
            fh.write("| %s | %d | %d | %d | %d | %s | %s |\n" % (
                DATASET_LABELS[ds], info["candidates"], info["selectable_unique"],
                info["selected"], info["target"], ", ".join(info["models"]), ", ".join(info["scenarios"])))
        for ds in ("ds1", "ds2", "ds3"):
            info = selection_report["datasets"][ds]
            fh.write("\n## %s\n\n" % DATASET_LABELS[ds])
            fh.write("Group cap: %d per selection group (%s)\n\n" % (info["group_cap"],
                "fact_id/prompt_id" if ds == "ds1" else ("conversation_id" if ds == "ds2" else "conversation_id/prompt_id")))
            for dim, dist in info["dimensions"].items():
                fh.write("### %s\n\n" % dim)
                fh.write("| value | count |\n|---|---|\n")
                for val, cnt in dist.items():
                    fh.write("| %s | %d |\n" % (val, cnt))

    # ---- terminal summary ----
    print("Dataset 1 (false premises): candidates %d, selected %d" % (terminal_rows[0][1], terminal_rows[0][2]))
    print("Dataset 2 (sycophancy-bench): candidates %d, selected %d" % (terminal_rows[1][1], terminal_rows[1][2]))
    print("Dataset 3 (SycoB): candidates %d, selected %d" % (terminal_rows[2][1], terminal_rows[2][2]))
    total_cand = sum(r[1] for r in terminal_rows)
    print("Total: candidates %d, selected %d" % (total_cand, len(unified)))
    print("Warnings: %d | Invalid records: %d | Duplicate candidates: %d" % (n_warning, n_invalid, duplicate_candidate_total))
    print("Output: %s" % os.path.join(SELECTED_DIR, "unified_2100.jsonl"))


if __name__ == "__main__":
    main()