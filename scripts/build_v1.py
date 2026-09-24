#!/usr/bin/env python3
"""Build SycAudit Dataset v1 (read-only over the source, reuse-established logic).

Unit = (fact_id, model). Only complete units (all five framings) with a
deterministic T=0 response. Source labels S1/S2/C/H/R kept verbatim, auxiliary.
Split strictly by fact_id (30/10/10), deterministic, stratified by category,
not optimized on labels or responses. Existing artifacts are left untouched.

Outputs (new files only):
    dataset/v1/train.jsonl
    dataset/v1/validation.jsonl
    dataset/v1/test.jsonl
    dataset/v1/dataset_manifest.json
    dataset/v1/dataset_schema.md
"""
from __future__ import annotations

import json
import pathlib
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from extract_preview import iter_records, build_prompt_completion, FALSE_PREMISES_CLEAN  # noqa: E402
from group_inspect import MODEL_SHORT, FRAMINGS  # noqa: E402
from v1_schema import SCHEMA_MD  # noqa: E402

DATASET = pathlib.Path(__file__).resolve().parent.parent / "dataset"
V1 = DATASET / "v1"
PHASE3_LABELED = FALSE_PREMISES_CLEAN[:6]
PHASE3_CROSS_JUDGE = FALSE_PREMISES_CLEAN[6]
PHASE4_LABELED = [FALSE_PREMISES_CLEAN[8], FALSE_PREMISES_CLEAN[10]]
T0 = 0.0

TRAIN_N = 30
VALID_N = 10
TEST_N = 10

REFERENCE_ARTIFACTS = [
    "dataset/extraction_preview.jsonl",
    "dataset/extraction_preview_report.md",
    "dataset/schis02_group_inspection.md",
    "dataset/schis02_group_inspection.json",
    "dataset/schis02_label_analysis.md",
    "dataset/schis02_label_analysis.json",
]

LABELS_OK = {"S1", "S2", "C", "H", "R"}


def to_model_short(model_full):
    return MODEL_SHORT.get(model_full, str(model_full))


def load_t0_cells():
    """All deterministic T=0 cells (fact, framing, model).

    Reuses build_prompt_completion so prompt/completion/source_id match the
    established extraction. Phase-4 records have no category/is_paper1_bridge/id:
    category is inherited per fact, is_paper1_bridge per (fact_id, framing) from
    phase-3 metadata (a template property, constant across models).
    """
    cells = {}
    phase3_meta = {}

    def record_keys(rel, rec):
        if rec is None:
            return False
        if rec.get("temperature") != T0:
            return False
        status, payload = build_prompt_completion(rec, pathlib.Path(rel).stem)
        if status != "extracted":
            return False
        prompt, completion, source_id = payload
        key = (rec.get("fact_id"), rec.get("framing"), rec.get("model"))
        if key in cells:
            return True  # duplicate T=0 cell in source; keep first-seen
        cells[key] = {
            "prompt": prompt, "completion": completion,
            "label": rec.get("gpt4o_label"), "temperature": rec.get("temperature"),
            "sample_idx": rec.get("sample_idx"), "seed": rec.get("seed"),
            "model": rec.get("model"), "model_short": to_model_short(rec.get("model")),
            "fact_id": rec.get("fact_id"), "framing": rec.get("framing"),
            "category": rec.get("category"),
            "is_paper1_bridge": rec.get("is_paper1_bridge"),
            "source_file": rel, "source_row": rec.get("_line_no"),
            "source_id": source_id, "rec_id": rec.get("id"),
        }
        return True

    for rel in PHASE3_LABELED:
        line_no = 0
        for rec, line_no in iter_records(DATASET / rel):
            if rec is None:
                continue
            rec["_line_no"] = line_no
            record_keys(rel, rec)
            if rec.get("temperature") == T0:
                phase3_meta.setdefault((rec.get("fact_id"), rec.get("framing")),
                                       (rec.get("category"), rec.get("is_paper1_bridge")))
    for rel in PHASE4_LABELED:
        for rec, line_no in iter_records(DATASET / rel):
            if rec is None:
                continue
            rec["_line_no"] = line_no
            record_keys(rel, rec)

    for c in cells.values():
        if c["category"] is None:
            cat, _ = phase3_meta.get((c["fact_id"], c["framing"]), (None, None))
            c["category"] = cat
        if c["is_paper1_bridge"] is None:
            _, br = phase3_meta.get((c["fact_id"], c["framing"]), (None, None))
            c["is_paper1_bridge"] = br
    return cells


def group_units(cells):
    by_unit = defaultdict(dict)
    for (fact_id, framing, model), c in cells.items():
        by_unit[(fact_id, model)][framing] = c
    complete, incomplete = [], []
    for key, fcells in sorted(by_unit.items()):
        if all(f in fcells for f in FRAMINGS):
            complete.append({"fact_id": key[0], "model_full": key[1],
                             "model_short": to_model_short(key[1]),
                             "category": fcells["neutral"]["category"],
                             "cells": fcells})
        else:
            incomplete.append({"fact_id": key[0],
                               "model_short": to_model_short(key[1]),
                               "missing_framings": [f for f in FRAMINGS if f not in fcells]})
    return complete, incomplete


def assign_split(facts_by_category):
    """Deterministic stratified fact split: per category stratum, facts sorted
    ascending by fact_id; (index mod 5) in {0,1,2}->train, ==3->validation,
    ==4->test. 60/20/20 per stratum -> train 30, validation 10, test 10.
    Input: {category: [fact_id, ...]}."""
    train, valid, test = [], [], []
    for cat in sorted(facts_by_category):
        ids = facts_by_category[cat]
        if isinstance(ids, str):
            raise TypeError(f"stratum for {cat!r} is a string, expected a list of fact_id")
        for i, fid in enumerate(sorted(ids)):
            r = i % 5
            (train if r < 3 else valid if r == 3 else test).append(fid)
    return sorted(train), sorted(valid), sorted(test)


def dump_unit(unit):
    unit2 = {"fact_id": unit["fact_id"], "model": unit["model_short"],
             "model_full": unit["model_full"], "category": unit["category"],
             "framings": {}}
    for f in FRAMINGS:
        c = unit["cells"][f]
        entry = {
            "framing": f, "prompt": c["prompt"], "completion": c["completion"],
            "label": c["label"], "temperature": c["temperature"],
            "sample_idx": c["sample_idx"], "seed": c["seed"],
            "model": c["model"], "model_short": c["model_short"],
            "fact_id": c["fact_id"], "category": c["category"],
            "is_paper1_bridge": c["is_paper1_bridge"],
            "source_file": c["source_file"], "source_row": c["source_row"],
            "source_id": c["source_id"],
        }
        if c["rec_id"] is not None:
            entry["id"] = c["rec_id"]
        unit2["framings"][f] = entry
    return unit2


def main():
    cells = load_t0_cells()
    complete, incomplete = group_units(cells)
    if incomplete:
        print("INCOMPLETE UNITS EXCLUDED:", incomplete)

    facts_cat = {}
    for u in complete:
        facts_cat.setdefault(u["fact_id"], u["category"])
    facts_by_cat = {c: [] for c in sorted(set(facts_cat.values()))}
    for fid, cat in facts_cat.items():
        facts_by_cat[cat].append(fid)

    train, valid, test = assign_split(facts_by_cat)
    split_of = {fid: ("train" if fid in set(train) else "validation" if fid in set(valid) else "test")
                for fid in facts_cat}

    splits_out = {"train": [], "validation": [], "test": []}
    for u in complete:
        splits_out[split_of[u["fact_id"]]].append(dump_unit(u))

    V1.mkdir(exist_ok=True)
    for name, records in splits_out.items():
        with open(V1 / f"{name}.jsonl", "w", encoding="utf-8") as fh:
            for r in records:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")

    all_units = splits_out["train"] + splits_out["validation"] + splits_out["test"]
    label_counts, framing_counter, category_counts, model_counts = Counter(), Counter(), Counter(), Counter()
    label_by_split = {k: Counter() for k in splits_out}
    label_by_framing = {f: Counter() for f in FRAMINGS}
    model_counts_by_split = {}
    for name, records in splits_out.items():
        mc = Counter()
        for r in records:
            model_counts[r["model"]] += 1
            mc[r["model"]] += 1
            category_counts[r["category"]] += 1
            for f, c in r["framings"].items():
                framing_counter[f] += 1
                label_counts[c["label"]] += 1
                label_by_split[name][c["label"]] += 1
                label_by_framing[f][c["label"]] += 1
        model_counts_by_split[name] = dict(mc)

    manifest = {
        "dataset_version": "v1",
        "dataset_name": "SycAudit schis02 false-premises grouped T=0 units",
        "source": "schis02/sycophancy-false-premises",
        "construction_timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "split_method": ("deterministic stratified fact-level split; within each category stratum "
                         "(s1_ablation_subset, false-premise-health) facts are sorted ascending by "
                         "fact_id and assigned by (index mod 5): {0,1,2}->train, 3->validation, "
                         "4->test; no randomness, no label/response optimization"),
        "split_seed": None,
        "unit_definition": "(fact_id, model)",
        "framings": list(FRAMINGS),
        "train_fact_ids": train,
        "validation_fact_ids": valid,
        "test_fact_ids": test,
        "train_unit_count": len(splits_out["train"]),
        "validation_unit_count": len(splits_out["validation"]),
        "test_unit_count": len(splits_out["test"]),
        "total_unit_count": len(all_units),
        "train_fact_count": len(train),
        "validation_fact_count": len(valid),
        "test_fact_count": len(test),
        "total_fact_count": len(facts_cat),
        "fact_category_counts": dict(Counter(facts_cat.values())),
        "category_counts": dict(category_counts),
        "model_counts": dict(model_counts),
        "model_counts_by_split": model_counts_by_split,
        "framing_counts": dict(framing_counter),
        "label_counts": dict(label_counts),
        "label_counts_by_split": {k: dict(v) for k, v in label_by_split.items()},
        "label_counts_by_framing": {k: dict(v) for k, v in label_by_framing.items()},
        "excluded_incomplete_units": incomplete,
        "excluded_reasoning": ("unit excluded unless all five framings have a deterministic T=0 "
                               "response with a gpt4o_label in the source"),
        "complete_units": len(complete),
        "t0_cells_total": len(cells),
        "t0_cells_used": sum(len(r["framings"]) for r in all_units),
        "framing_completeness": "5/5 framings per unit (verified at build time)",
        "labels_auxiliary": True,
        "no_sycophancy_target": True,
        "source_files": {"phase3_labeled": PHASE3_LABELED,
                         "phase4_labeled": PHASE4_LABELED,
                         "phase3_cross_judge": PHASE3_CROSS_JUDGE},
        "source_artifact_references": REFERENCE_ARTIFACTS,
    }
    with open(V1 / "dataset_manifest.json", "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, ensure_ascii=False)
    (V1 / "dataset_schema.md").write_text(SCHEMA_MD, encoding="utf-8")

    print("SUCCESS: v1 constructed")
    print(f"  complete units: {manifest['complete_units']} (train/val/test = "
          f"{manifest['train_unit_count']}/{manifest['validation_unit_count']}/"
          f"{manifest['test_unit_count']})")
    print(f"  facts: train {manifest['train_fact_count']} | validation "
          f"{manifest['validation_fact_count']} | test {manifest['test_fact_count']}")
    print(f"  label counts: {dict(label_counts)}")


if __name__ == "__main__":
    main()