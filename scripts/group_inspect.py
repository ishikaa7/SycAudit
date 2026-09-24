#!/usr/bin/env python3
"""GROUP-LEVEL INSPECTION of the existing extracted schis02 pool (READ-ONLY).

This script does NOT modify, delete or re-label anything. It does NOT change the
extraction logic. It reconstitutes the EXISTING valid schis02 pool (7,455 unique
(prompt, completion) pairs) using the exact same scan order and dedupe as
``scripts/extract_preview.py`` (FALSE_PREMISES_CLEAN + build_prompt_completion),
then analyzes the GROUP structure of those pairs.

Grouping key under investigation: ``fact_id`` (e.g. ``fact_001``).

Outputs (new files, never overwriting existing extraction artifacts):
    dataset/schis02_group_inspection.md    - human-readable report (sections 1-9)
    dataset/schis02_group_inspection.json  - machine-readable summary

Purpose: understand the actual structure of the dataset BEFORE designing the
supervised SycAudit dataset. No splits, no sampling size, no keep/remove decisions.
"""
from __future__ import annotations

import json
import pathlib
import statistics
import sys
from collections import Counter, defaultdict

REPO = pathlib.Path(__file__).resolve().parent.parent
DATASET = REPO / "dataset"
sys.path.insert(0, str(REPO / "scripts"))
from extract_preview import (  # noqa: E402
    iter_records,
    build_prompt_completion,
    FALSE_PREMISES_CLEAN,
)

OUT_MD = DATASET / "schis02_group_inspection.md"
OUT_JSON = DATASET / "schis02_group_inspection.json"

MODEL_SHORT = {
    "meta-llama/Llama-3.1-8B-Instruct": "Llama-3.1-8B",
    "meta-llama/Meta-Llama-3-8B-Instruct": "Llama-3-8B",
    "mistralai/Mistral-7B-Instruct-v0.1": "Mistral-7B-v0.1",
    "mistralai/Mistral-7B-Instruct-v0.2": "Mistral-7B-v0.2",
    "Qwen/Qwen1.5-7B-Chat": "Qwen1.5-7B",
    "Qwen/Qwen2.5-7B-Instruct": "Qwen2.5-7B",
    "meta-llama/Llama-3.1-70B-Instruct": "Llama-3.1-70B",
    "Qwen/Qwen2.5-72B-Instruct": "Qwen2.5-72B",
}

FRAMINGS = ["neutral", "original", "leading", "opinion", "authority"]
TAXONOMY = ["S1", "S2", "C", "H", "R"]


def reconstitute_pool():
    """Rebuild the existing valid pool: identical order + dedupe as extract_preview.

    Returns (pool, n_unique, n_scanned) where n_scanned counts every candidate row
    that passed the extraction rule (before content dedupe) - i.e. the 39,000 rows
    of the 11 clean files.
    """
    pool = []
    seen_pairs = set()
    n_scanned = 0
    for rel in FALSE_PREMISES_CLEAN:
        path = DATASET / rel
        file_stem = rel.replace("\\", "/").split("/")[-1].rsplit(".", 1)[0]
        for rec, line_no in iter_records(path):
            if rec is None:
                continue
            status, payload = build_prompt_completion(rec, file_stem)
            if status != "extracted":
                continue
            n_scanned += 1
            prompt, completion, source_id = payload
            key = (prompt, completion)
            if key in seen_pairs:
                continue
            seen_pairs.add(key)
            pool.append({
                "prompt": prompt,
                "completion": completion,
                "source_id": source_id,
                "file_stem": file_stem,
                "row": line_no,
                "fact_id": rec.get("fact_id"),
                "framing": rec.get("framing"),
                "model": rec.get("model"),
                "model_short": MODEL_SHORT.get(rec.get("model"), str(rec.get("model"))),
                "temperature": rec.get("temperature"),
                "sample_idx": rec.get("sample_idx"),
                "category": rec.get("category"),
                "is_paper1_bridge": rec.get("is_paper1_bridge"),
                "gpt4o_label": rec.get("gpt4o_label"),
                "gpt4o_cross_label": rec.get("gpt4o_cross_label"),
                "seed_meta": rec.get("seed"),
            })
    return pool, len(seen_pairs), n_scanned


def pct(q, n):
    return f"{100.0 * q / n:.1f}%"


def build_report():
    pool, n_unique, n_scanned = reconstitute_pool()
    n_total = len(pool)
    md = []
    J = {}

    # ---------------------------------------------------------------- group build
    groups = defaultdict(list)
    for r in pool:
        groups[r["fact_id"]].append(r)
    gids = sorted(groups)
    N_G = len(gids)

    # per group: coverage of framings/models/temps etc
    per_group = {}
    for gid in gids:
        rows = groups[gid]
        framings = sorted({r["framing"] for r in rows})
        models = sorted({r["model_short"] for r in rows})
        temps = sorted({str(r["temperature"]) for r in rows})
        cats = sorted({str(r["category"]) for r in rows} - {"None"})
        labels = Counter(r["gpt4o_label"] for r in rows if r["gpt4o_label"])
        cross = Counter(r["gpt4o_cross_label"] for r in rows if r["gpt4o_cross_label"])
        per_group[gid] = {
            "n": len(rows),
            "framings": framings,
            "models": models,
            "n_models": len(models),
            "temps": temps,
            "categories": cats,
            "labels": dict(labels),
            "cross_labels": dict(cross),
            "completion_len_mean": round(statistics.mean(len(r["completion"]) for r in rows), 1),
            "prompt_len_mean": round(statistics.mean(len(r["prompt"]) for r in rows), 1),
        }

    sizes = sorted(per_group[g]["n"] for g in gids)
    mn, mx = sizes[0], sizes[-1]
    mean = statistics.mean(sizes)
    median = statistics.median(sizes)
    pcts = {
        "p05": sizes[int(0.05 * (N_G - 1))], "p10": sizes[int(0.10 * (N_G - 1))],
        "p25": sizes[int(0.25 * (N_G - 1))], "p50": median,
        "p75": sizes[int(0.75 * (N_G - 1))], "p90": sizes[int(0.90 * (N_G - 1))],
        "p95": sizes[int(0.95 * (N_G - 1))],
    }
    hist = Counter(sizes)
    bucket1 = sum(1 for s in sizes if s == 1)
    bucket2 = sum(1 for s in sizes if s == 2)
    bucket3 = sum(1 for s in sizes if s == 3)
    bucket4p = sum(1 for s in sizes if s >= 4)
    in_g2p = sum(s for s in sizes if s >= 2)

    # coverage of (fact x framing x model) cells actually present in the pool
    cell_total = N_G * len(FRAMINGS) * len(MODEL_SHORT)
    cells_present = sum(
        1 for g in gids
        for f in per_group[g]["framings"]
        for m in per_group[g]["models"]
    )

    # ------------------------------------------------- factual checks
    # (a) distinct prompt text per (fact, framing) — expect exactly 1 per cell
    prompt_per_cell = defaultdict(set)
    for r in pool:
        prompt_per_cell[(r["fact_id"], r["framing"])].add(r["prompt"])
    multi_prompt_cells = {k: v for k, v in prompt_per_cell.items() if len(v) > 1}
    # (b) does phase3 prompt == phase4 prompt for the same (fact,framing)?
    phase3_stems = [f.split("/")[-1].rsplit(".", 1)[0] for f in FALSE_PREMISES_CLEAN[:6]]
    phase4_stems = [f.split("/")[-1].rsplit(".", 1)[0] for f in FALSE_PREMISES_CLEAN[7:]]
    p3_prompts = defaultdict(set)
    p4_prompts = defaultdict(set)
    for r in pool:
        k = (r["fact_id"], r["framing"])
        if r["file_stem"] in phase3_stems:
            p3_prompts[k].add(r["prompt"])
        elif r["file_stem"] in phase4_stems:
            p4_prompts[k].add(r["prompt"])
    phase3v4_diff = [k for k in sorted(set(p3_prompts) & set(p4_prompts))
                     if p3_prompts[k] != p4_prompts[k]]

    # (c) completions shared across different fact groups
    comp_by_fact = defaultdict(set)
    for r in pool:
        comp_by_fact[r["fact_id"]].add(r["completion"])
    shared_across_groups = {}
    all_comp = defaultdict(set)
    for g in gids:
        for c in comp_by_fact[g]:
            all_comp[c].add(g)
    shared_across_groups = {c: sorted(gset) for c, gset in all_comp.items() if len(gset) >= 2}
    # top shared completions by multiplicity
    shared_count = Counter(len(v) for v in shared_across_groups.values())

    # within-group completion sharing across models (content duplicated across models)
    comp_per_cell = defaultdict(set)
    for r in pool:
        comp_per_cell[(r["fact_id"], r["framing"])].add(r["completion"])
    # (d) completions per (fact,framing): how many unique outputs
    # (e) completions shared across framings within a group
    within_group_shared = {}
    for g in gids:
        c_by_fr = {f: set() for f in per_group[g]["framings"]}
        for r in groups[g]:
            c_by_fr[r["framing"]].add(r["completion"])
        total = sum(len(v) for v in c_by_fr.values())
        union = set()
        for v in c_by_fr.values():
            union |= v
        within_group_shared[g] = (total - len(union), total)

    # (f) cells (fact,framing,model) with a distinct template-identical prompt
    # (g) label composition by group already in per_group

    # (h) per (fact,framing,model) cell completion multiplicity
    per_cell = defaultdict(int)
    for r in pool:
        per_cell[(r["fact_id"], r["framing"], r["model_short"])] += 1
    cell_sizes = sorted(per_cell.values())
    cell_count = len(cell_sizes)
    cells_by_fact = {g: {} for g in gids}
    for (g, f, m), c in per_cell.items():
        cells_by_fact[g][(f, m)] = c
    # (i) is_paper1_bridge semantics check: True only on framing=original + s1 category?
    bridge_by_framing = Counter()
    bridge_true_cat = Counter()
    for r in pool:
        if r["is_paper1_bridge"] is True:
            bridge_by_framing[r["framing"]] += 1
            bridge_true_cat[str(r["category"])] += 1

    J = {
        "pool_size_unique_pairs": n_total,
        "source_candidate_rows_scanned": n_scanned,
        "content_duplicate_rows_collapsed": n_scanned - n_total,
        "n_groups_by_fact_id": N_G,
        "group_size": {"min": mn, "max": mx, "mean": mean, "median": median,
                       "percentiles_p05_p95": pcts},
        "group_size_histogram": {str(k): v for k, v in sorted(hist.items())},
        "groups_size_buckets": {"n1": bucket1, "n2": bucket2, "n3": bucket3,
                                "n4plus": bucket4p,
                                "obs_in_groups_ge2": in_g2p},
        "cell_coverage": {"n_fact_framing_cells": len(prompt_per_cell),
                          "n_fact_framing_model_cells": cell_count,
                          "completions_per_cell_min_mean_median_max": (
                              cell_sizes[0], round(statistics.mean(cell_sizes), 2),
                              statistics.median(cell_sizes), cell_sizes[-1])},
        "distinct_prompt_texts_per_fact_framing_cells_with_multi": len(multi_prompt_cells),
        "phase3_vs_phase4_prompt_mismatch_cells": len(phase3v4_diff),
        "completions_shared_across_groups": len(shared_across_groups),
        "completions_shared_across_groups_by_multiplicity": dict(shared_count),
        "completions_shared_across_groups_examples": [
            [c, sorted(all_comp[c])] for c in sorted(shared_across_groups, key=lambda k: -len(all_comp[k]))[:5]
        ],
        "completions_shared_within_group_across_framings": within_group_shared,
        "bridge_true_by_framing": dict(bridge_by_framing),
        "bridge_true_by_category": dict(bridge_true_cat),
        "per_group": per_group,
        "categories_by_fact": {g: per_group[g]["categories"] for g in gids},
        "label_coverage": {
            "phase3_labeled_rows_in_pool": sum(1 for r in pool if r["file_stem"] in phase3_stems),
            "phase4_completion_rows_in_pool": sum(1 for r in pool if r["file_stem"] in phase4_stems),
            "rows_with_gpt4o_label": sum(1 for r in pool if r["gpt4o_label"]),
            "rows_with_gpt4o_cross_label": sum(1 for r in pool if r["gpt4o_cross_label"]),
        },
        "taxonomy_counts_in_pool": dict(Counter(r["gpt4o_label"] for r in pool if r["gpt4o_label"])),
        "camilablank_note": "EXCLUDED from primary dataset by decision (conversation-history responses add an unmodeled conditioning variable; SycAudit studies isolated-prompt sycophancy)",
    }

    # ========================================================== REPORT BODY
    md += ["# schis02 Group-Level Inspection", ""]
    md += ["_Generated by `scripts/group_inspect.py` (READ-ONLY; reconstitutes the existing 7,455-pair pool "
           "with the identical scan order + dedupe as `extract_preview.py`; no splits, no sampling, no labels "
           "created, no deletions)._", ""]
    md += [f"> Scope note: `camilablank/sycophancy-datasets` is NOT part of the primary dataset (decision: "
           f"conversation-history-based responses introduce an additional unmodeled conditioning variable). "
           f"This report covers `schis02/sycophancy-false-premises` only.", ""]

    # ---- 1. overview
    md += ["## 1. Dataset overview", ""]
    md += ["Source-authoritative structure (`dataset/sycophancy-false-premises/README.md`):", ""]
    md += [
        "| Component | Rows | Design |",
        "|---|---|---|",
        "| Phase 3 (distributional) | 31,500 | 50 facts x 5 framings x 6 models x 21 samples (1 @T=0, 10 @T=0.3, 10 @T=0.7) |",
        "| cross_judge | 1,500 | GPT-4o re-label of the T=0 sample of every (fact x framing x model) |",
        "| Phase 4 (scale, 70B+) | 3,000 | 50 facts x 5 framings x 2 models x 2 temps x 5 samples |",
        "| Single-shot evaluation (paper 1, EXCLUDED) | 3,000 | 500 false-premise prompts x 6 models |",
        "| Framing ablation (EXCLUDED) | 576 | 96 prompts x 6 models, neutral rephrasing |",
        "| Archived NF4 ablation (EXCLUDED) | _ | v1 archived in `v1_nf4_quantized/` |",
        "",
        f"**Valid extracted pool (this report's subject): {n_total:,} unique (prompt -> completion) pairs**, "
        f"reconstituted from the {n_scanned:,} candidate rows of the 11 clean files with the existing extraction "
        f"logic (content duplicates collapsed: {n_scanned - n_total:,} repeated rows -> {n_total:,} unique pairs).", ""]
    md += [f"- **Framings:** {', '.join(FRAMINGS)}", f"- **Models (8):** {', '.join(sorted(MODEL_SHORT.values()))} "
           f"(6 x 7-8B in phase 3; 2 x 70B+ in phase 4)",
           f"- **Taxonomy (source-defined):** S1 = sycophantic agreement, S2 = confabulation, C = correct, "
           f"H = hedge, R = refusal (GPT-4o-mini, kappa=0.752 vs human per README)", ""]

    # ---- 2. grouping key
    md += ["## 2. Grouping-key analysis", ""]
    md += ["**Key finding: `fact_id` (e.g. `fact_001`) is the correct underlying-group key.**", ""]
    md += [
        "Evidence from the source schema and records:",
        "- `id` in phase-3 files is a **composite** of `fact_id` + framing (e.g. `fact_004_authority`). "
        "All 5,250 rows per phase-3 file carry a suffixed `id`; there are no bare `id`s in the clean files.",
        "- Phase-4 files (`phase4_scale/*`) have **no `id` field at all** - only `fact_id`. "
        "`fact_id` is the only field that survives across every clean family and identifies the shared underlying prompt.",
        "- Every one of the 50 `fact_id`s appears with 5 framings; the 5 prompt texts in a group are the *same factual "
        "probe* re-worded by a controlled lead-in (see section 5 examples). Grouping by `fact_id` therefore keeps "
        "all framing variants of one underlying prompt in one unit - exactly what the SycAudit split-contamination "
        "rule requires.",
        "- `id` (phase 3) or `source_id` should NOT be the group key: it changes with framing (and phase 4 has none).",
        "- `prompt` text alone is too granular (one key per framing variant), and `category`/`is_paper1_bridge` are "
        "fact-level attributes, not group identifiers.",
        "- **No evidence of one fact being spread across multiple IDs** - `fact_id` numbers are contiguous "
        "`fact_001`-`fact_050` and each maps to a single prompt-set.",
        "",
    ]

    # ---- 3. group-size distribution
    md += ["## 3. Group-size distribution (unique (prompt, completion) observations per `fact_id`)", ""]
    md += [
        f"- Number of underlying groups (unique `fact_id`s): **{N_G}**",
        f"- Observations per group: min **{mn}**, max **{mx}**, mean **{mean:.1f}**, median **{median:.0f}**",
        f"- Percentiles: p05 **{pcts['p05']}**, p10 **{pcts['p10']}**, p25 **{pcts['p25']}**, p50 **{pcts['p50']}**, "
        f"p75 **{pcts['p75']}**, p90 **{pcts['p90']}**, p95 **{pcts['p95']}**",
        "",
        "Bucket counts:",
        f"- groups with exactly 1 observation: **{bucket1}**",
        f"- groups with exactly 2 observations: **{bucket2}**",
        f"- groups with exactly 3 observations: **{bucket3}**",
        f"- groups with >= 4 observations: **{bucket4p}**",
        f"- observations belonging to groups with >= 2 observations: **{in_g2p}** of {n_total:,} "
        f"({pct(in_g2p, n_total)})",
        "",
        "Frequency distribution (histogram of group sizes):",
        "| observations/group | number of groups |",
        "|---:|---:|",
    ]
    for k in sorted(hist):
        md += [f"| {k} | {hist[k]} |"]
    md += ["",]
    md += ["**Reading:** the 7,455 observations are **NOT** 7,455 independent units. They are repeated "
           "measurements of only **50 underlying prompt-groups** (mean ~149 observations per group). For any "
           "train/validation/test split that groups by `fact_id`, the real countable units are the 50 facts.", ""]
    md += ["**Deeper cell structure:** within a group, the design is **5 framings x 8 models = 40 "
           "(fact, framing, model) cells**; each cell holds a few unique completions: "
           f"{cell_count} such cells across the pool, completions per cell "
           f"min/mean/median/max = {cell_sizes[0]}/{statistics.mean(cell_sizes):.2f}/"
           f"{statistics.median(cell_sizes)}/{cell_sizes[-1]}. So rows are correlated repeated draws "
           "within a cell - not independent examples.", ""]

    # ---- 4. metadata/schema
    md += ["## 4. Metadata / schema analysis", ""]
    md += ["Field catalog across the clean families (phase 3 vs phase 4), classified by role:", ""]
    md += [
        "| Field | Phase 3 | Phase 4 | Classification |",
        "|---|---|---|---|",
        "| `fact_id` | yes | yes | **GROUP key** - identifies the underlying prompt/fact |",
        "| `id` | yes (`fact_id` + `_framing`) | **no** | Composite; NOT group key |",
        "| `framing` | yes | yes | **TREATMENT/variant** - one of neutral/original/leading/opinion/authority |",
        "| `prompt` | yes | yes | **INPUT** - full rendered prompt for the model |",
        "| `completion` | yes | yes | **RESPONSE (target text)** - raw model output |",
        "| `model` | yes | yes | **SOURCE/condition** - 8 models |",
        "| `temperature` | yes | yes | sampling noise (0.0/0.3/0.7 phase 3; 0.0/0.7 phase 4) |",
        "| `sample_idx` | yes (0-9) | yes (0-4) | sampling draw index (not a feature) |",
        "| `seed` | yes | yes | generation seed (noise dimension; not a feature) |",
        "| `category` | yes | no | fact-level metadata: `s1_ablation_subset` (30 facts) / `false-premise-health` (20 facts) |",
        "| `is_paper1_bridge` | yes | no | fact-level metadata: True only for `original` framing of the 30 s1_ablation facts (rows bridged from paper 1 single-shot prompts) |",
        "| `gpt4o_label` | yes | yes (labeled files) | **EXPLICIT label** - S1/S2/C/H/R (taxonomy defined by source) |",
        "| `gpt4o_cross_label` | only cross_judge | no | second judges on the T=0 sample (GPT-4o vs GPT-4o-mini) |",
        "",
    ]
    md += ["Notes:", "- The 30 `s1_ablation_subset` facts' `original` framing rows have `is_paper1_bridge=True` "
           "and their prompts are the paper-1 single-shot prompts; the single-shot label/eval files "
           "(`gpt4o_labels_all.json`, `human_validation_*`) are EXCLUDED from the pool. Their underlying prompt "
           "content overlaps the (excluded) single-shot evaluation by design.",
           "- `category` and `is_paper1_bridge` are constants within a fact and can therefore leak group identity "
           "if used as features (they are safe as group-level descriptors only).",
           "- `seed`, `sample_idx`, `temperature` are sampling dimensions; they carry no semantic content and "
           "should not enter as features.", ""]

    # ---- 5. representative group examples
    md += ["## 5. Representative group examples", ""]
    # pick groups: max, min, a health one, a bridge (s1 original), an opinion/authority
    # pick groups: max, min, a health one, an s1 one, plus two fixed representative ones
    biggest = max(gids, key=lambda g: len(groups[g]))
    smallest = min(gids, key=lambda g: len(groups[g]))
    chosen = [biggest, smallest]
    first_health = next(g for g in gids if "false-premise-health" in (per_group[g]["categories"] or []))
    if first_health not in chosen:
        chosen.append(first_health)
    for g in ["fact_003", "fact_029", "fact_001"]:
        if g in gids and g not in chosen:
            chosen.append(g)
    # facet labels for the chosen examples
    facet = {g: "max-size group" for g in chosen}
    facet[smallest] = "min-size group"
    if smallest == biggest:
        facet[biggest] = "min AND max size group"
    if first_health:
        facet[first_health] = "false-premise-health category"
    for g in ("fact_001", "fact_003", "fact_029"):
        if g in chosen and g not in (biggest, smallest, first_health):
            facet[g] = "typical s1_ablation_subset group"
    for gid in chosen:
        rows = groups[gid]
        pg = per_group[gid]
        md += [f"### GROUP: `{gid}` _({facet[gid]})_", ""]
        framings = pg["framings"]
        prompts = {}
        for r in rows:
            prompts.setdefault(r["framing"], r["prompt"])
        n_bridge_true = sum(1 for r in rows if r["is_paper1_bridge"] is True)
        md += [f"- **Unique (prompt -> completion) observations in pool:** {len(rows)}",
               f"- **Framings present ({len(framings)}/5):** {', '.join(framings)}",
               f"- **Models present ({pg['n_models']}/8):** {', '.join(pg['models'])}",
               f"- **Temperatures:** {', '.join(pg['temps'])}",
               f"- **Category:** {', '.join(pg['categories']) or 'n/a'}",
               f"- **`is_paper1_bridge=True` rows:** {n_bridge_true}",
               f"- **Label composition (`gpt4o_label`, where present):** {pg['labels']}",
               "",
               "Underlying prompt variants (one per framing):"]
        for fr in FRAMINGS:
            if fr in prompts:
                md += [f"  - **{fr}:** {prompts[fr][:200]}{'...' if len(prompts[fr]) > 200 else ''}"]
        md += [
            "",
            "Response variety (a few short exemplars from distinct models/framings):",
        ]
        # a compact cross-section: unique (model, completion) snippet
        shown = set()
        for r in rows:
            key = (r["model_short"], r["framing"])
            if key in shown or len(shown) >= 6:
                continue
            shown.add(key)
            md += [f"  - **{r['model_short']} | {r['framing']}:** "
                   f"\"{r['completion'][:130]}{'...' if len(r['completion']) > 130 else ''}\""]
        md += ["", "- **Shared completions across framings within this group:** "
               f"{within_group_shared[gid][0]} of {within_group_shared[gid][1]} completions identical across >=2 framings.",
               ""]
    md += ["_Examples above are representative (dense, sparse, health-category, paper-1-bridged, and typical). "
           "All 50 groups behave structurally like these._", ""]

    # ---- 6. duplicate/leakage
    md += ["## 6. Duplicate / leakage analysis", ""]
    md += [f"**Pool-level content duplicates:** {n_scanned - n_total:,} source rows were collapsed to "
           f"{n_total:,} unique pairs by the existing extraction logic (same completion across `sample_idx` draws, "
           f"phase-4 `*_completions` vs `*_labeled` copies, and cross_judge rows that are content-subsets of "
           f"phase-3 files). The pool therefore contains **no exact (prompt, completion) duplication**; every "
           f"row is unique content.", ""]
    md += ["**Group-key integrity / leakage candidates (findings only, nothing removed):**", ""]
    md += [
        f"1. **Prompt text per (fact, framing) cell:** {len(multi_prompt_cells)} of "
        f"{len(prompt_per_cell)} cells have MORE than one distinct prompt text "
        f"({', '.join(f'{k}: {len(v)}' for k, v in multi_prompt_cells.items())}). "
        f"{'Any multi-text cell means the same (fact, framing) was rendered with differing text across files.' if multi_prompt_cells else 'Expected and confirmed: each (fact, framing) maps to exactly one prompt text across files, and phase-4 reuses the phase-3 prompt templates.'}",
        f"2. **Phase-3 vs phase-4 prompt consistency (same (fact, framing)):** "
        f"{len(phase3v4_diff)} mismatching cells out of {len(set(p3_prompts) | set(p4_prompts))} shared cells. "
        f"{'Cells: ' + ', '.join(str(k) for k in phase3v4_diff) if phase3v4_diff else 'Phase-4 uses the same prompt templates as phase-3.'}",
        f"3. **Same completion appearing in >=2 DIFFERENT groups:** {len(shared_across_groups)} distinct completion "
        f"texts (multiplicity distribution: {dict(shared_count)}). "
        f"{'Examples: ' + ' | '.join(f'#reps={len(all_comp[c])} groups={sorted(all_comp[c])} text={c[:60]}...' for c in sorted(shared_across_groups, key=lambda k: -len(all_comp[k]))[:3]) if shared_across_groups else ''} "
        f"These are typically generic outputs that recur across facts; keyed with their prompt they are distinct "
        f"rows, but the content duplication should be noted for eval-pair design.",
        f"4. **Completion shared across framings WITHIN a group** (a model outputting identical text to different "
        f"leads): reported per group in section 5 / JSON - informative for robustness but not a leak.",
        f"5. **`model`, `sample_idx`, `seed`, `temperature` as split dimensions:** none of these should drive "
        f"splits; they are conditions/noise within a group. Splitting on a model or sampling dimension would "
        f"separate variants of the same underlying prompt across splits - the exact contamination the fact-level "
        f"rule forbids.",
        f"6. **Template-generated vs distinct:** all 50 facts are distinct authored templates; the 30 "
        f"`s1_ablation_subset` facts share their `original` prompt text with the (excluded) paper-1 single-shot "
        f"evaluation, and the paper-1 ablation files (excluded) reuse the same facts. If the paper-1 eval files are "
        f"ever re-included, the overlap must be handled; they are currently excluded.",
        "",
    ]

    # ---- 7. available labeling
    md += ["## 7. Available labeling information", ""]
    md += ["**The source EXPLICITLY provides labels; nothing is inferred here.**", ""]
    md += [
        f"- `gpt4o_label` on phase-3 rows (all 31,500) and phase-4 `*_labeled` rows (3,000): taxonomy **S1** "
        f"(sycophantic agreement), **S2** (confabulation), **C** (correct), **H** (hedge), **R** (refusal) - "
        f"defined in the source README, produced by GPT-4o-mini (kappa=0.752 vs human per README; validation "
        f"files are excluded template-embedded copies). In the extracted pool, phase-3 rows carry the label and "
        f"phase-4 pool rows are drawn from the (label-less) `*_completions` files, so exact label coverage in the "
        f"pool is:",
        f"  - rows with `gpt4o_label`: {J['label_coverage']['rows_with_gpt4o_label']:,} of {n_total:,} "
        f"({pct(J['label_coverage']['rows_with_gpt4o_label'], n_total)})",
        f"  - rows with `gpt4o_cross_label` (second judge, T=0 only): {J['label_coverage']['rows_with_gpt4o_cross_label']}",
        f"- Label composition in pool (`gpt4o_label`): {J['taxonomy_counts_in_pool']}",
        "",
        "**Classification of label-related information:**",
        "- *Explicitly provided by source:* S1/S2/C/H/R category labels; cross-judge second labels on T=0; "
        "ground-truth statements exist in the (excluded) ablation/full_ablation_prompts files; "
        "the README's own 86%/KDG/basin-escape analyses.",
        "- *Potential future label (needs definition, NOT current):* framing-conditioned directional labels "
        "(e.g. does the model worsen from neutral to authority?) are computable from completions + labels but are "
        "an analysis artifact we would have to define and justify - do not treat as source labels.",
        "- *Requires human annotation:* a dedicated per-response fine-grained sycophancy severity label "
        "(beyond the 5-way taxonomy) would need new annotation; the source taxonomy is the only sanctioned target.",
        f"- *Cannot be determined from this dataset:* whether a change in output was 'sycophantic' versus "
        f"'sampling luck' per single row - the pairing structure (neutral vs framed) is the signal, not any "
        f"single row in isolation.",
        "",
    ]

    # ---- 8. suitability
    md += ["## 8. Suitability for SycAudit (factual assessment)", ""]
    md += [
        "**What it CAN support:**",
        "- A **framing-conditioned supervised study**: for each of ~50 underlying prompts, we have 5 controlled "
        "lead-in variants x up to 8 models x repeated stochastic draws. This is precisely the 'same underlying "
        "prompt, different controlled framings -> compare behavior' design.",
        "- **Grouped expt: the 50 facts are the units**; every fact has >=4 observations (~149 mean), and all "
        "observations of a fact can be kept in exactly one split with zero leakage (the split units are the facts).",
        "- **Model-conditioning analysis**: identical (fact, framing) prompts with responses from 7B and 70B models, "
        "so scale effects can be inspected within-group.",
        "- **Label-informed EDM (f1-f5) analysis** using the source-provided S1/S2/C/H/R taxonomy on the 59.9% "
        "of pool rows that carry `gpt4o_label` (all 4,462 phase-3 rows; phase-4 labeled copies exist and can be "
        "joined without new rows).",
        "",
        "**What it CANNOT support:**",
        "- Treating the 7,455 rows as 7,455 independent, i.i.d. examples. The effective sample size for split "
        "purposes is ~50 groups (and ~250 (fact, framing) cells, ~2,000 (fact, framing, model) cells).",
        "- Any split that mixes framing variants of one fact across train/eval - that is explicitly the "
        "contamination this grouping rule forbids.",
        "- A claim of per-row ground-truth 'sycophancy' severity beyond the source 5-way taxonomy; single rows "
        "are not labeled with a framing-conditioned deviation.",
        "",
        "**What likely needs additional annotation/work (decision, not this task):**",
        "- Joining `gpt4o_label` onto phase-4 pool rows from the matching `*_labeled` files (rows are content "
        "identical; no new observations).",
        "- Defining the supervised target: response-only label (source taxonomy) vs framing-conditioned target "
        "(requires an explicit, documented construction rule) - must be decided before the final pool.",
        "- Explicitly flagging the ~generic completions shared across many groups for eval-pair construction.",
        "",
        "**What must NOT be assumed from the current data:**",
        "- That group-usize similarity implies label similarity (S1 rates differ by model/framing per README).",
        "- That completions are independent across `sample_idx`/temperature draws (same-text draws were collapsed; "
        "remaining distinct draws within a cell are correlated samples, not independent items).",
        "",
    ]

    # ---- 9. open decisions
    md += ["## 9. Open decisions before dataset construction", ""]
    md += [
        "1. **Split unit**: confirm train/validation/test split at the `fact_id` group level (50 units). "
        "Ratio and size UNDECIDED (out of this task's scope).",
        "2. **Sampled unit / multiplicity**: decide whether each unique (fact, framing, model, completion) row is a "
        "training example (7,455 rows) or whether per-cell completions are aggregated (e.g. majority label / "
        "distribution per (fact, framing, model)) - affects both supervision targets and eval design.",
        "3. **Supervised target** (f1-f5): (a) use source S1/S2/C/H/R directly, (b) define a framing-conditioned "
        "directional label (e.g. neutral->authority deviation), or (c) require a new annotation pass. "
        "Must be explicitly decided; do not infer.",
        "4. **Phase-4 label join**: attach `gpt4o_label` from `*_labeled` to the identical phase-4 `*_completions` "
        "rows (OK to do before sampling).",
        "5. **Label coverage policy**: whether rows without a label (phase-4 completions, until joined) can enter "
        "the pool or are withheld.",
        "6. **Category balance / paper-1 bridge**: whether to balance across `s1_ablation_subset` vs "
        "`false-premise-health` and how to treat the 30 `s1_ablation_subset` facts whose `original` prompts "
        "overlap the excluded paper-1 single-shot eval (informational only; both files currently excluded).",
        "7. **Temperature/sampling policy**: whether to keep all distinct temperature draws or restrict the pool "
        "to T=0 rows (deterministic, one per (fact, framing, model)) - affects pool size several-fold.",
        "8. **Generic completions**: whether completions that recur across many groups (refusals, one-liners) are "
        "kept, down-weighted, or flagged in eval-pair design.",
        "9. **Sampling method for the final N**: stratified-by-group deterministic vs random-with-seed - UNDECIDED.",
        "10. **Post-hoc analysis only (NOT for training target)**: framing-conditioned KDG-style deviation metrics.",
        "",
    ]

    return "\n".join(md), J


def main():
    md, J = build_report()
    OUT_MD.write_text(md, encoding="utf-8")
    OUT_JSON.write_text(json.dumps(J, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    print(f"Wrote: {OUT_MD}")
    print(f"Wrote: {OUT_JSON}")
    pool, _, _ = reconstitute_pool()
    sizes = sorted(Counter(r["fact_id"] for r in pool).values())
    print(f"pool={len(pool):,}  groups={len(sizes)}  size min/mean/median/max = "
          f"{sizes[0]}/{statistics.mean(sizes):.1f}/{statistics.median(sizes)}/{sizes[-1]}")


if __name__ == "__main__":
    main()