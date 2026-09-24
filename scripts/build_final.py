#!/usr/bin/env python3
"""FINAL SycAudit evaluator dataset builder (RESPONSE-LEVEL CSV).

Sources (actual local directories; dataset/project names differ):
  SCHIS02     -> dataset/sycophancy-false-premises/
  CamilaBlank -> dataset/sycophancy-datasets/

Reuses the existing validated extraction/grouping logic:
  scripts/extract_preview.py (iter_records, build_prompt_completion,
       build_conversation, FALSE_PREMISES_CLEAN)
  scripts/group_inspect.py   (reconstitute_pool, MODEL_SHORT, FRAMINGS)

Design (one CSV row = ONE genuine model response):
  * SCHIS02: 2,000 T=0 rows (every (fact, framing, model) cell once) plus a
    deterministic quota-based addition of 250 T>0 rows (broad, non-concentrated);
    fact_id -> group_id; framing preserved; source labels S1/S2/C/H/R preserved
    (phase-4 rows label-joined from the paired *_labeled files, content-identical).
  * CamilaBlank: up to ~750 rows, final bot turn = response, rendered previous
    conversation = prompt (conversation-history representation); framing "unframed";
    native sycophancy_label preserved when present; no model field exists in source.

No model is trained. f1..f5 are reserved and left empty. No row is fabricated,
duplicated, paraphrased or synthesized. Selection is deterministic (no RNG).

Outputs (under dataset/final/):
  sycaudit_evaluator_dataset.csv  dataset_manifest.json  dataset_schema.md
"""
from __future__ import annotations

import csv
import datetime
import hashlib
import json
import pathlib
import sys
from collections import Counter, defaultdict

REPO = pathlib.Path(__file__).resolve().parent.parent
DATASET = REPO / "dataset"
CA = DATASET / "sycophancy-false-premises"
CB = DATASET / "sycophancy-datasets"
FINAL = DATASET / "final"

sys.path.insert(0, str(REPO / "scripts"))
from extract_preview import (  # noqa: E402
    iter_records,
    build_prompt_completion,
    build_conversation,
    FALSE_PREMISES_CLEAN,
)
from group_inspect import reconstitute_pool, MODEL_SHORT, FRAMINGS  # noqa: E402

SCHIS02_REL = [("dataset/" + rel, rel.rsplit("/", 1)[-1].rsplit(".", 1)[0])
               for rel in FALSE_PREMISES_CLEAN]
PHASE3_STEMS = {rel.rsplit("/", 1)[-1].rsplit(".", 1)[0] for rel in FALSE_PREMISES_CLEAN[:7]}
PHASE4_LABELED = [
    "dataset/sycophancy-false-premises/phase4_scale/Qwen2.5-72B-Instruct_labeled.jsonl",
    "dataset/sycophancy-false-premises/phase4_scale/Llama-3.1-70B-Instruct_labeled.jsonl",
]

CAMILABLANK_FILES = [
    "dataset/sycophancy-datasets/mmlu_single_turn.jsonl",
    "dataset/sycophancy-datasets/mmlu_rated.jsonl",
    "dataset/sycophancy-datasets/mmlu_reiterated_turn2.jsonl",
    "dataset/sycophancy-datasets/mmlu_turn3_rated.jsonl",
    "dataset/sycophancy-datasets/triviaqa_rated.jsonl",
    "dataset/sycophancy-datasets/political_opinions_turn2_response_restate.jsonl",
]

COLUMNS = ["id", "source_dataset", "source_file", "source_id", "group_id", "model",
           "framing", "prompt", "response", "f1", "f2", "f3", "f4", "f5",
           "source_label", "temperature", "sample_idx", "seed", "category",
           "is_paper1_bridge"]

TARGET_TOTAL = 3000
SCHIS02_TARGET = 2250     # 75%  (2000 T=0 + 250 T>0)
CAMI_TARGET = 750         # 25%
CAMILABLANK_TARGET = 750


def row_id(source_dataset: str, source_file: str, source_id: str,
           prompt: str, response: str) -> str:
    h = hashlib.sha1(f"{source_dataset}|{source_file}|{source_id}|{prompt}|{response}"
                     .encode("utf-8")).hexdigest()[:14]
    return f"{source_dataset}_{h}"


def empty(v):
    return "" if v is None else v


# --------------------------------------------------------------------------- SCHIS02
def build_schis02_rows():
    """Assemble all SCHIS02 pool rows with labels/category/bridge resolved."""
    stem_to_rel = {}
    for rel, stem in SCHIS02_REL:
        stem_to_rel[stem] = rel

    # phase-4 label join map: (model, fact_id, framing, temp_str, sample_idx)-> label
    p4_label = {}
    for rel in PHASE4_LABELED:
        for rec, _ in iter_records(REPO / rel):
            if rec is None or not rec.get("gpt4o_label"):
                continue
            p4_label[(rec["model"], rec["fact_id"], rec["framing"],
                      str(rec["temperature"]), str(rec["sample_idx"]))] = rec["gpt4o_label"]
    # phase-3 fact-level metadata (for phase-4 inheritance)
    fact_category = {}
    cell_bridge = {}

    pool, _, _ = reconstitute_pool()
    rows = []
    for r in pool:
        stem = r["file_stem"]
        full = stem_to_rel[stem]
        temp = str(r["temperature"])
        is_t0 = (temp == "0.0")
        if stem in PHASE3_STEMS:
            # record fact->category and (fact, framing)->bridge for inheritance
            cat = r["category"]
            if cat:
                fact_category.setdefault(r["fact_id"], cat)
            b = r["is_paper1_bridge"]
            cell_bridge.setdefault((r["fact_id"], r["framing"]), b if b is not None else None)
        else:
            # phase-4: inherit fact-level metadata established in phase-3
            cat = fact_category.get(r["fact_id"])
            b = cell_bridge.get((r["fact_id"], r["framing"]))

        if stem in PHASE3_STEMS:
            label = r["gpt4o_label"] or ""
        else:
            label = p4_label.get((r["model"], r["fact_id"], r["framing"],
                                  temp, str(r["sample_idx"])), "")

        rows.append({
            "source_dataset": "schis02",
            "source_file": full,
            "source_id": r["source_id"],
            "group_id": r["fact_id"],
            "model": r["model"],
            "framing": r["framing"],
            "prompt": r["prompt"],
            "response": r["completion"],
            "source_label": label,
            "temperature": temp,
            "sample_idx": str(r["sample_idx"]),
            "seed": str(r["seed_meta"]) if r["seed_meta"] is not None else "",
            "category": empty(cat),
            "is_paper1_bridge": "" if b is None else str(b),
            "is_t0": is_t0,
            "model_short": r["model_short"],
        })
    return rows


def select_schis02(pool_rows):
    """2,000 T=0 rows (all cells) + 250 T>0 extras (quota per (model, framing))."""
    t0 = [r for r in pool_rows if r["is_t0"]]
    tgt = [r for r in pool_rows if not r["is_t0"]]

    combos = sorted({(r["model"], r["framing"]) for r in tgt})
    extras = []
    picked = set()
    for c, (model, framing) in enumerate(combos):
        quota = 7 if c < 10 else 6
        cand = [r for r in tgt if r["model"] == model and r["framing"] == framing]
        if not cand:
            continue
        by_fact = defaultdict(list)
        for r in cand:
            by_fact[r["group_id"]].append(r)
        facts = sorted(by_fact)
        offset = c % len(facts)
        got = 0
        for k in range(len(facts)):
            if got >= quota:
                break
            fact = facts[(offset + k) % len(facts)]
            ordered = sorted(by_fact[fact], key=lambda x: (x["sample_idx"], x["temperature"], x["response"]))
            for r in ordered:
                key = (r["source_file"], r["prompt"], r["response"])
                if key in picked:
                    continue
                picked.add(key)
                extras.append(r)
                got += 1
                break
    # hard cap to keep total == SCHIS02_TARGET
    if len(t0) + len(extras) > SCHIS02_TARGET:
        extras = extras[:SCHIS02_TARGET - len(t0)]
    return t0, extras


# --------------------------------------------------------------------------- CamilaBlank
def build_camilablank_rows():
    """Final-bot-turn responses from the 6 families; global (prompt,response) dedupe."""
    rows = []
    seen = set()
    for rel in CAMILABLANK_FILES:
        stem = rel.rsplit("/", 1)[-1].rsplit(".", 1)[0]
        n_rows = 0
        for rec, line_no in iter_records(REPO / rel):
            if rec is None:
                continue
            status, payload = build_conversation(rec, stem)
            if status != "extracted":
                continue
            n_rows += 1
            prompt, response, source_id = payload
            key = (prompt, response)
            if key in seen:
                continue
            seen.add(key)
            label = rec.get("sycophancy_label")
            hist = rec.get("history") or []
            rows.append({
                "source_dataset": "camilablank",
                "source_file": rel,
                "source_id": source_id,
                "group_id": f"{stem}::{rec.get('id', 'no-id')}",
                "model": "",
                "framing": "unframed",
                "prompt": prompt,
                "response": response,
                "source_label": label if isinstance(label, str) and label else "",
                "temperature": "",
                "sample_idx": "",
                "seed": "",
                "category": "",
                "is_paper1_bridge": "",
                "history_len": len(hist),
            })
    return rows


def select_camilablank(rows, target):
    """Deterministic even-quota per family; evenly spaced picks within a family."""
    by_stem = defaultdict(list)
    for r in rows:
        by_stem[r["source_id"].split("::")[0]].append(r)
    stems = [rel.rsplit("/", 1)[-1].rsplit(".", 1)[0] for rel in CAMILABLANK_FILES]
    for s in stems:
        by_stem[s].sort(key=lambda x: (x["group_id"], x["prompt"]))

    # quota distribution: give every family an equal share; redistribute any
    # shortfall (family smaller than its share) to the remaining families.
    quotas = {s: 0 for s in stems}
    remaining = target
    active = list(stems)
    while remaining > 0 and active:
        share = -(-remaining // len(active))   # ceiling
        newly_inactive = []
        for s in active:
            take = min(len(by_stem[s]) - quotas[s], share, remaining)
            quotas[s] += take
            remaining -= take
            if remaining <= 0:
                break
            if quotas[s] >= len(by_stem[s]):
                newly_inactive.append(s)
        active = [s for s in active if s not in newly_inactive]
        if remaining > 0 and not active:
            break

    selected = []
    for s in stems:
        fam = by_stem[s]
        n = len(fam)
        q = quotas[s]
        for k in range(q):
            idx = min(n - 1, (k * n) // q)
            selected.append(fam[idx])
    return selected


# --------------------------------------------------------------------------- output
def main():
    FINAL.mkdir(parents=True, exist_ok=True)

    print("Reconstituting SCHIS02 pool (existing extraction logic)...")
    schis02 = build_schis02_rows()
    print(f"  SCHIS02 pool unique pairs: {len(schis02)} "
          f"(T=0: {sum(1 for r in schis02 if r['is_t0'])}, "
          f"T>0: {sum(1 for r in schis02 if not r['is_t0'])})")

    t0, extras = select_schis02(schis02)
    selected_schis02 = t0 + extras
    print(f"  SCHIS02 selected: {len(selected_schis02)} "
          f"(T=0 {len(t0)} + T>0 {len(extras)})")

    print("Extracting CamilaBlank conversation histories...")
    cami = build_camilablank_rows()
    print(f"  CamilaBlank unique pairs: {len(cami)}")
    sel_cami = select_camilablank(cami, CAMILABLANK_TARGET)
    print(f"  CamilaBlank selected: {len(sel_cami)}")

    final = []
    for r in selected_schis02:
        final.append({k: empty(r.get(k, "")) for k in COLUMNS})
    for r in sel_cami:
        final.append({k: empty(r.get(k, "")) for k in COLUMNS})

    for r in final:
        r["id"] = row_id(r["source_dataset"], r["source_file"], r["source_id"],
                         r["prompt"], r["response"])

    # deterministic row order: schis02 (as built) then camilablank (as built)
    csv_path = FINAL / "sycaudit_evaluator_dataset.csv"
    with open(csv_path, "w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=COLUMNS)
        writer.writeheader()
        for r in final:
            writer.writerow(r)

    # ---- statistics for manifest
    s_rows = [r for r in final if r["source_dataset"] == "schis02"]
    c_rows = [r for r in final if r["source_dataset"] == "camilablank"]
    schis02_stats = {
        "total_rows": len(s_rows),
        "facts_represented": sorted({r["group_id"] for r in s_rows}),
        "n_facts": len({r["group_id"] for r in s_rows}),
        "models_represented": sorted(
            {r["model"].rsplit("/", 1)[-1] for r in s_rows if r["model"]}),
        "n_models": len({r["model"] for r in s_rows}),
        "framings_represented": sorted({r["framing"] for r in s_rows}),
        "rows_per_model": dict(Counter(sorted(r["model"].rsplit("/", 1)[-1] for r in s_rows))),
        "rows_per_framing": dict(Counter(r["framing"] for r in s_rows)),
        "rows_per_fact": {f: sum(1 for r in s_rows if r["group_id"] == f)
                          for f in sorted({r["group_id"] for r in s_rows})},
        "t0_rows": sum(1 for r in s_rows if r["temperature"] == "0.0"),
        "tgt_rows": sum(1 for r in s_rows if r["temperature"] != "0.0"),
        "source_label_distribution": dict(
            Counter(r["source_label"] for r in s_rows if r["source_label"])),
        "rows_with_label": sum(1 for r in s_rows if r["source_label"]),
    }
    cami_stats = {
        "total_rows": len(c_rows),
        "conversations_groups": len({r["group_id"] for r in c_rows}),
        "models_represented": [],       # no model metadata exists in these files
        "families": dict(Counter(r["source_id"].split("::")[0] for r in c_rows)),
        "rows_with_conversational_history": sum(1 for r in sel_cami if r["history_len"] >= 2),
        "rows_with_label": sum(1 for r in c_rows if r["source_label"]),
    }

    manifest = {
        "dataset_version": "1.0.0",
        "dataset_name": "SycAudit Evaluator Dataset",
        "construction_timestamp": datetime.datetime.now(datetime.timezone.utc)
            .isoformat(timespec="seconds"),
        "total_rows": len(final),
        "source_counts": {"schis02": len(s_rows), "camilablank": len(c_rows)},
        "source_percentages": {
            "schis02": round(100.0 * len(s_rows) / len(final), 1),
            "camilablank": round(100.0 * len(c_rows) / len(final), 1),
        },
        "schis02_statistics": schis02_stats,
        "camilablank_statistics": cami_stats,
        "selection_method": (
            "Deterministic, no RNG. SCHIS02: all 2,000 deterministic T=0 rows "
            "(one per (fact, framing, model) cell, t=0.0) plus 250 T>0 rows with a "
            "fixed quota per (model, framing) combination (7 for the first 10 sorted "
            "combos, 6 for the rest), cells visited in a rotated fact order per combo "
            "to keep coverage broad; extras are the deterministically first available "
            "T>0 completion per chosen cell. CamilaBlank: even-spacing round-robin "
            "across the 6 source families (sorted by group_id then prompt), capped at "
            "750 rows. Budgets: SCHIS02 2250 (75%), CamilaBlank 750 (25%)."),
        "selection_seed": None,
        "columns": COLUMNS,
        "missing_value_policy": (
            "Empty string when a source value is unavailable; nothing is inferred. "
            "CamilaBlank records carry no model/temperature/sample_idx/seed/category/"
            "bridge metadata in the source files, so those cells are empty."),
        "f1_f5_status": (
            "f1-f5 are reserved evaluator facet fields and were not inferred or "
            "generated during dataset construction; every f1-f5 cell is empty."),
        "deduplication_policy": (
            "SCHIS02 rows come from the existing validated 7,455-pair pool "
            "(exact (prompt, completion) content dedupe per the established extraction "
            "pipeline); CamilaBlank rows are exactly-deduplicated on (prompt, response) "
            "globally; no identical (prompt, response) appears twice in the CSV."),
        "validation_summary": "see scripts/validate_final.py output after construction",
        "f1_f5_statement": (
            "f1-f5 are reserved evaluator facet fields and were not inferred or "
            "generated during dataset construction."),
        "source_directory_mapping": {
            "SCHIS02": "sycophancy-false-premises/",
            "CamilaBlank": "sycophancy-datasets/",
        },
        "discovered_schis02_source_files": [rel for rel, _ in SCHIS02_REL],
        "discovered_camilablank_source_files": CAMILABLANK_FILES,
    }
    (FINAL / "dataset_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    schema = SCHEMA_MD.format(
        total=len(final), s_n=len(s_rows), c_n=len(c_rows),
        s_pct=round(100.0 * len(s_rows) / len(final), 1),
        c_pct=round(100.0 * len(c_rows) / len(final), 1),
        t0=schis02_stats["t0_rows"], tgt=schis02_stats["tgt_rows"],
        n_facts=schis02_stats["n_facts"],
        n_models=schis02_stats["n_models"],
        n_groups=cami_stats["conversations_groups"],
    )
    (FINAL / "dataset_schema.md").write_text(schema, encoding="utf-8")

    print("=" * 78)
    print("FINAL ROW COUNT:", len(final))
    print("SCHIS02 ROWS:", len(s_rows))
    print("CAMILABLANK ROWS:", len(c_rows))
    print(f"SCHIS02 %: {manifest['source_percentages']['schis02']}")
    print(f"CAMILABLANK %: {manifest['source_percentages']['camilablank']}")
    print("T=0 ROWS:", schis02_stats["t0_rows"])
    print("T>0 ROWS:", schis02_stats["tgt_rows"])
    print("NUMBER OF FACT/GROUP IDS:", schis02_stats["n_facts"], "facts +",
          cami_stats["conversations_groups"], "camilablank groups")
    print("NUMBER OF MODELS:", schis02_stats["n_models"])
    print("NUMBER OF FRAMINGS:", len(schis02_stats["framings_represented"]))
    print("F1-F5 STATUS: empty (reserved, not inferred)")
    print("VALIDATION RESULT: run scripts/validate_final.py")
    print()
    print("DISCOVERED SCHIS02 SOURCE FILES")
    for rel, _ in SCHIS02_REL:
        print("  ", rel)
    print("DISCOVERED CAMILABLANK SOURCE FILES")
    for rel in CAMILABLANK_FILES:
        print("  ", rel)


SCHEMA_MD = """# SycAudit Evaluator Dataset - Schema Documentation

Dataset version: 1.0.0. One row = ONE genuine model response.

## 1. One row = one model response
Each CSV row is a single extracted model-generated response to a single
prompt/context. For SCHIS02 each completion is its own row (the five framings are
NOT collapsed into one row). For CamilaBlank, each final-bot-turn response is its
own row. Rows are never fabricated, duplicated, paraphrased or synthesized.

## 2. Why SCHIS02 and CamilaBlank are both included
SCHIS02 (dataset/sycophancy-false-premises/) is the primary structured source: a
controlled 50-fact x 5-framing x 8-model design with GPT-4o-mini labels. CamilaBlank
(dataset/sycophancy-datasets/) adds conversational-response diversity (MMLU, TriviaQA,
political-opinion interactions) that SCHIS02's isolated-prompt design does not cover.
Composition: {s_pct}% / {c_pct}%.

## 3. Why SCHIS02 framing is preserved
Framing (neutral/original/leading/opinion/authority) is a source-provided controlled
treatment variable. It is stored verbatim so evaluators can compare the same fact
across lead-in conditions.

## 4. Why CamilaBlank framing is "unframed"
CamilaBlank records are conversational dialogues with no framing taxonomy in the
source. No framing label is invented; every CamilaBlank row is assigned exactly the
literal value "unframed".

## 5. Why group_id is preserved
- SCHIS02: group_id = fact_id, the underlying prompt group. All framing/temperature
  rows of one fact share one group.
- CamilaBlank: group_id = <file>::<source id>, the underlying conversation/question;
  explicitly NOT a SCHIS02 fact id.

## 6. Why stochastic SCHIS02 responses are retained but must not be treated as
independent experimental facts
T>0 rows (temperature 0.3/0.7) are repeated stochastic draws of the same underlying
(fact, framing, model) cell. They are kept to aid response-diversity analysis, but the
temperature/sample_idx/seed columns expose their sampling origin so they are never
mistaken for independent facts: the group unit is the fact and its cell.

## 7. Why source labels are preserved separately from f1-f5
source_label holds the original source-provided label of the response: SCHIS02 uses the
source taxonomy S1 (sycophantic agreement), S2 (confabulation), C (correct), H (hedge),
R (refusal); CamilaBlank uses its native response labels (e.g. sycophantic_flip /
maintained_correct / switched_incorrect) when present. f1-f5 are reserved evaluator
facet fields and are a distinct, later annotation step.

## 8. Why f1-f5 are currently empty/reserved
No verified facet annotations exist for either source, so f1-f5 must not be guessed or
auto-labeled. Facet annotation is a separate controlled step.

## 9. Exact source composition
Total rows: {total} (SCHIS02 {s_n}, CamilaBlank {c_n}).
- SCHIS02: {t0} T=0 rows + {tgt} T>0 rows; {n_facts} facts, {n_models} models, 5 framings.
- CamilaBlank: history-derived final responses across 6 families; {n_groups} groups.
Rows without an available source metadata value use an empty string (never invented).

## 10. Dataset limitations
- SCHIS02 stochastic rows are not independent facts (see 6).
- CamilaBlank has no model metadata: different responses may come from different
  underlying models; response provenance cannot resolve it from these files.
- CamilaBlank responses are context-conditioned (conversation history); see source_label
  scope and the conversation-history rendering in prompt.
- f1-f5 are empty; any analysis must not assume facet annotations exist.
- Categories/is_paper1_bridge for SCHIS02 phase-4 rows are inherited from the
  phase-3 records of the same fact template (constants per fact/framing).

## 11. Actual local source directory mapping
| Dataset/project name | Actual local directory |
|---|---|
| SCHIS02 | dataset/sycophancy-false-premises/ |
| CamilaBlank | dataset/sycophancy-datasets/ |
"""


if __name__ == "__main__":
    main()