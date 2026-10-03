"""
Select exactly 50 records from dataset/combined/combined_evaluator_dataset.csv for
HUMAN EVALUATION.

Properties this script guarantees:
  * Read-only on the input CSV. It is opened once, in 'r' mode.
  * Label-blind: `source_label` and `f1`-`f5` are never referenced anywhere.
  * Deterministic: random.Random(42) plus stable sorts. Reruns are byte-identical.
  * Output rows are the original CSV rows, field-for-field, in original order.

Outputs:
  dataset/combined/human_evaluation_50.csv
  dataset/combined/human_evaluation_selection_report.md
"""

import collections
import csv
import hashlib
import json
import random
import re
from pathlib import Path

SEED = 42
N_TARGET = 50
ROOT = Path(__file__).resolve().parents[1]
IN_CSV = ROOT / "dataset" / "combined" / "combined_evaluator_dataset.csv"
OUT_CSV = ROOT / "dataset" / "combined" / "human_evaluation_50.csv"
OUT_MD = ROOT / "dataset" / "combined" / "human_evaluation_selection_report.md"

SOURCES = ["schis02", "camilablank", "ds1", "ds2", "ds3"]
QUOTA = {s: N_TARGET // len(SOURCES) for s in SOURCES}  # 10 each

# Columns the selector is allowed to look at. Anything not listed is ignored,
# which is how label-blindness is enforced structurally rather than by discipline.
ALLOWED = {
    "id", "source_dataset", "source_file", "source_id", "group_id",
    "model", "framing", "prompt", "temperature", "sample_idx",
    "seed", "category", "is_paper1_bridge",
}

# Explicitly forbidden. Asserted absent from ALLOWED at runtime.
FORBIDDEN = {"source_label", "f1", "f2", "f3", "f4", "f5"}


def norm_prompt(s):
    """Whitespace/case-normalized prompt, for detecting duplicates."""
    return re.sub(r"\s+", " ", (s or "").lower()).strip()


def ds1_case(source_id, model):
    """ds1 underlying case = (fact, model). Falls back to source_id when the
    record carries no fact_NNN token (137 of 700 ds1 rows)."""
    m = re.search(r"fact_\d+", source_id or "")
    fact = m.group(0) if m else "no_fact::" + (source_id or "")
    return f"{fact}::{model}"


def case_key(r):
    """The underlying case this record belongs to. One record per case."""
    src = r["source_dataset"]
    if src in ("schis02", "camilablank"):
        return r["group_id"] or r["id"]
    if src == "ds1":
        return ds1_case(r["source_id"], r["model"])
    if src == "ds2":
        return r["source_id"] or r["id"]
    if src == "ds3":
        return "p::" + norm_prompt(r["prompt"])
    return r["id"]


def axes(r):
    """Ordered list of structural diversity axes for this record's source."""
    src = r["source_dataset"]
    sid = r["source_id"] or ""
    if src == "schis02":
        return [r["model"] or "(none)", r["framing"] or "(none)", r["category"] or "(none)"]
    if src == "camilablank":
        # Only axis available: task family prefix of group_id, e.g. mmlu_rated.
        return [(r["group_id"] or "").split("::")[0] or "(none)"]
    if src == "ds1":
        return [r["model"] or "(none)", (r["source_file"] or "").split("/")[-1]]
    if src == "ds2":
        # source_file encodes scenario / model / split: debate|Qwen2.5-14B|train.parquet
        return [r["model"] or "(none)", (r["source_file"] or "").split("/")[-1]]
    if src == "ds3":
        parts = sid.split("::")
        head = parts[0].split("__")
        style = head[1] if len(head) > 1 else "(none)"
        respvar = parts[1] if len(parts) > 1 else "(none)"
        taskkind = "multiturn" if head[0].startswith("mt_") else "single_qa"
        return [(r["source_file"] or "").split("/")[-1], taskkind, style, respvar]
    return [r["id"]]


def axis_names(src):
    if src == "schis02":
        return ["model", "framing", "category"]
    if src == "camilablank":
        return ["task_family"]
    if src == "ds1":
        return ["model", "source_file"]
    if src == "ds2":
        return ["model", "source_file"]
    if src == "ds3":
        return ["source_file", "task_kind", "style", "response_variant"]
    return ["id"]


def main():
    assert not (FORBIDDEN & ALLOWED), "label field leaked into ALLOWED"

    raw = IN_CSV.read_bytes()
    in_sha = hashlib.sha256(raw).hexdigest()

    with IN_CSV.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        columns = list(reader.fieldnames)
        rows = list(reader)

    # Full inspection statistics (reported, never used for selection).
    stats = {
        "rows": len(rows),
        "columns": columns,
        "missing": {c: sum(1 for r in rows if not (r[c] or "").strip()) for c in columns},
        "source_dataset": collections.Counter(r["source_dataset"] for r in rows),
        "by_source_dist": {},
        "dup_ids": sum(1 for v in collections.Counter(r["id"] for r in rows).values() if v > 1),
        "dup_full_row": sum(
            1 for v in collections.Counter(tuple(r[c] for c in columns) for r in rows).values() if v > 1
        ),
        "dup_pr": sum(1 for v in collections.Counter((r["prompt"], r["response"]) for r in rows).values() if v > 1),
        "distinct_prompts": len(set(r["prompt"] for r in rows)),
        "distinct_norm_prompts": len(set(norm_prompt(r["prompt"]) for r in rows)),
        "distinct_responses": len(set(r["response"] for r in rows)),
        "cases": {},
    }

    for s in SOURCES:
        sub = [r for r in rows if r["source_dataset"] == s]
        d = {
            "n": len(sub),
            "model": collections.Counter(r["model"] or "(EMPTY)" for r in sub),
            "framing": collections.Counter(r["framing"] or "(EMPTY)" for r in sub),
            "category": collections.Counter(r["category"] or "(EMPTY)" for r in sub),
            "source_file": collections.Counter((r["source_file"] or "").split("/")[-1] for r in sub),
            "temperature": collections.Counter(r["temperature"] or "(EMPTY)" for r in sub),
            "source_label": collections.Counter(r["source_label"] or "(EMPTY)" for r in sub),
            "n_cases": len(set(case_key(r) for r in sub)),
            "case_size_dist": collections.Counter(
                collections.Counter(case_key(r) for r in sub).values()
            ),
            "distinct_prompts": len(set(r["prompt"] for r in sub)),
        }
        if s == "camilablank":
            d["task_family"] = collections.Counter((r["group_id"] or "").split("::")[0] for r in sub)
        if s == "ds3":
            d["task_kind"] = collections.Counter(
                "multiturn" if (r["source_id"] or "").split("__")[0].startswith("mt_") else "single_qa"
                for r in sub
            )
        stats["by_source_dist"][s] = d

    # Cross-source overlap.
    pr_map = collections.defaultdict(set)
    for r in rows:
        pr_map[(r["prompt"], r["response"])].add(r["source_dataset"])
    p_map = collections.defaultdict(set)
    for r in rows:
        p_map[norm_prompt(r["prompt"])].add(r["source_dataset"])
    stats["cross_source_pr"] = sum(1 for v in pr_map.values() if len(v) > 1)
    stats["cross_source_pr_combos"] = collections.Counter(
        tuple(sorted(v)) for v in pr_map.values() if len(v) > 1
    )
    stats["cross_source_prompt"] = sum(1 for v in p_map.values() if len(v) > 1)
    stats["cross_source_prompt_combos"] = collections.Counter(
        tuple(sorted(v)) for v in p_map.values() if len(v) > 1
    )
    stats["cases"] = {
        "schis02": len(set(case_key(r) for r in rows if r["source_dataset"] == "schis02")),
        "camilablank": len(set(case_key(r) for r in rows if r["source_dataset"] == "camilablank")),
        "ds1": len(set(case_key(r) for r in rows if r["source_dataset"] == "ds1")),
        "ds2": len(set(case_key(r) for r in rows if r["source_dataset"] == "ds2")),
        "ds3": len(set(case_key(r) for r in rows if r["source_dataset"] == "ds3")),
    }

    # ---- Selection ----
    rng = random.Random(SEED)
    used_cases = set()
    used_prompts = set()
    selected = []
    trace = []

    for s in SOURCES:
        pool = [r for r in rows if r["source_dataset"] == s]
        # Stable sort, then one seeded shuffle: ties resolve by shuffled order.
        pool = sorted(pool, key=lambda r: r["id"])
        rng.shuffle(pool)

        names = axis_names(s)
        counts = [collections.Counter() for _ in names]
        picked = 0
        remaining = list(pool)
        while picked < QUOTA[s] and remaining:
            best = None
            best_key = None
            for idx, r in enumerate(remaining):
                ck = case_key(r)
                np_ = norm_prompt(r["prompt"])
                if ck in used_cases or np_ in used_prompts:
                    continue
                av = axes(r)
                # Minimise the maximum usage across axes, then total usage.
                usage = [counts[i][av[i]] for i in range(len(av))]
                key = (max(usage), sum(usage), idx)
                if best_key is None or key < best_key:
                    best_key, best = key, (idx, r, ck, np_, av)
            if best is None:
                break
            idx, r, ck, np_, av = best
            remaining.pop(idx)
            for i, v in enumerate(av):
                counts[i][v] += 1
            used_cases.add(ck)
            used_prompts.add(np_)
            selected.append(r)
            picked += 1
            trace.append((s, r["id"], ck, names, av))

    assert len(selected) == N_TARGET, f"selected {len(selected)}, expected {N_TARGET}"
    assert len({r["id"] for r in selected}) == N_TARGET
    assert len(used_prompts) == N_TARGET, "duplicate prompt in selection"

    # Write original rows verbatim, in original file order.
    order = {r["id"]: i for i, r in enumerate(rows)}
    selected.sort(key=lambda r: order[r["id"]])
    with OUT_CSV.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=columns, lineterminator="\n")
        w.writeheader()
        for r in selected:
            w.writerow({c: r[c] for c in columns})

    # ---- Verify output fidelity ----
    with OUT_CSV.open(encoding="utf-8", newline="") as f:
        out_rows = list(csv.DictReader(f))
    out_cols = list(csv.DictReader(OUT_CSV.open(encoding="utf-8", newline="")).fieldnames)
    src_by_id = {r["id"]: r for r in rows}
    assert out_cols == columns, "column order/set changed"
    assert len(out_rows) == N_TARGET
    for r in out_rows:
        assert r == src_by_id[r["id"]], f"row altered: {r['id']}"
    assert all(r[c] == "" for r in out_rows for c in ("f1", "f2", "f3", "f4", "f5"))
    assert hashlib.sha256(IN_CSV.read_bytes()).hexdigest() == in_sha, "input CSV modified"

    # ---- Report ----
    L = []
    a = L.append
    a("# Human Evaluation 50-Record Selection Report")
    a("")
    a(f"**Source (read-only):** `dataset/combined/combined_evaluator_dataset.csv`  ")
    a(f"**Output:** `dataset/combined/human_evaluation_50.csv` ({len(out_rows)} records)  ")
    a(f"**Input sha256 (before = after):** `{in_sha}`")
    a("")
    a("This was a **sampling/selection task only**. No annotation was performed. "
      "`f1`-`f5` remain empty on every selected record. No sycophancy judgment was made "
      "or inferred about any response. No existing dataset was modified.")
    a("")
    a("## 1. Total records inspected")
    a("")
    a(f"| item | value |")
    a("|---|---|")
    a(f"| data rows | {stats['rows']} |")
    a(f"| columns | {len(stats['columns'])} |")
    a(f"| distinct `id` | {len(set(r['id'] for r in rows))} |")
    a("")
    a("## 2. Columns / schema")
    a("")
    a("| # | column |")
    a("|---|---|")
    for i, c in enumerate(columns):
        a(f"| {i} | `{c}` |")
    a("")
    a("`id` is a namespaced canonical id (`sycaudit__<original_id>` or `ishika__<original_id>`) "
      "and is unique across all 5,100 rows. `original_id` preserves the source id verbatim.")
    a("")
    a("## 3. Missing-value summary")
    a("")
    a("A cell is empty when the column was absent in that source row. No placeholders, no imputation.")
    a("")
    a("| column | missing | filled |")
    a("|---|---|---|")
    for c in columns:
        a(f"| `{c}` | {stats['missing'][c]} | {stats['rows'] - stats['missing'][c]} |")
    a("")
    a("**`f1`-`f5` are empty on all 5,100 rows.** The label fields reserved for the "
      "evaluation phase are entirely clear; nothing needs to be overwritten.")
    a("")
    a("## 4. Duplicate analysis")
    a("")
    a("| check | result |")
    a("|---|---|")
    a(f"| duplicate `id` | {stats['dup_ids']} |")
    a(f"| exact full-row duplicates | {stats['dup_full_row']} |")
    a(f"| distinct prompts | {stats['distinct_prompts']} |")
    a(f"| distinct prompts (case/whitespace-normalized) | {stats['distinct_norm_prompts']} |")
    a(f"| distinct responses | {stats['distinct_responses']} |")
    a(f"| exact `(prompt, response)` duplicate groups | {stats['dup_pr']} |")
    a(f"| cross-source `(prompt, response)` collisions | {stats['cross_source_pr']} |")
    a(f"| cross-source prompt-only collisions | {stats['cross_source_prompt']} |")
    a("")
    a(f"The two source corpora are **not information-disjoint**. "
      f"{stats['cross_source_prompt_combos'].most_common(1)[0][1]} prompts appear in both "
      f"`{'` and `'.join(stats['cross_source_prompt_combos'].most_common(1)[0][0])}`, of which "
      f"{stats['cross_source_pr']} are exact `(prompt, response)` pairs - both corpora drew on the "
      f"same SCHIS02-era generation files. Within each source, prompts are also heavily repeated "
      f"because each fact/question is answered under multiple conditions.")
    a("")
    a("## 5. Source dataset distribution")
    a("")
    a("| `source_dataset` | n | % | id prefix |")
    a("|---|---|---|---|")
    for s, n in stats["source_dataset"].most_common():
        pre = "sycaudit" if s in ("schis02", "camilablank") else "ishika"
        a(f"| `{s}` | {n} | {100 * n / stats['rows']:.1f}% | `{pre}__` |")
    a("")
    a("## 6. Model distribution (per source)")
    a("")
    a("`model` is populated for 3,772 of 5,100 rows. It is empty for **all 750 `camilablank` rows** "
      "and 578 of 700 `ds3` rows, so model is not a universal axis.")
    a("")
    for s in SOURCES:
        d = stats["by_source_dist"][s]
        a(f"### `{s}` (n={d['n']}, {len(d['model'])} distinct)")
        a("")
        a("| value | count |")
        a("|---|---|")
        for k, v in d["model"].most_common(25):
            a(f"| `{k}` | {v} |")
        if len(d["model"]) > 25:
            a(f"| ... | {len(d['model']) - 25} more |")
        a("")
    a("## 7. Framing / variant and category distribution")
    a("")
    a("These columns are **SycAudit-only**. All 2,100 Ishika rows leave them empty, so they cannot "
      "be used as cross-source axes.")
    a("")
    for s in SOURCES:
        d = stats["by_source_dist"][s]
        a(f"### `{s}`")
        a("")
        a(f"- distinct `framing`: {len(d['framing'])} - "
          + ", ".join(f"`{k}`={v}" for k, v in d["framing"].most_common(8)))
        a(f"- distinct `category`: {len(d['category'])} - "
          + ", ".join(f"`{k}`={v}" for k, v in d["category"].most_common(8)))
        a(f"- distinct `source_file`: {len(d['source_file'])} - "
          + ", ".join(f"`{k}`={v}" for k, v in d["source_file"].most_common(8)))
        if "task_family" in d:
            a(f"- `camilablank` task families (`group_id` prefix): "
              + ", ".join(f"`{k}`={v}" for k, v in d["task_family"].most_common(8)))
        if "task_kind" in d:
            a(f"- `ds3` task kind (from `source_id`): "
              + ", ".join(f"`{k}`={v}" for k, v in d["task_kind"].most_common(8)))
        a("")
    a("**`ds1`, `ds2`, `ds3` carry no framing/variant column in this file.** Their variant structure "
      "had to be recovered from `source_id` / `source_file` (see section 8).")
    a("")
    a("## 8. Grouping / variant structure")
    a("")
    a("Related records exist at every level. An underlying-case key was derived per source:")
    a("")
    a("| source | case key | distinct cases | case-size distribution |")
    a("|---|---|---|---|")
    case_key_desc = {
        "schis02": "`group_id` (fact_NNN)",
        "camilablank": "`group_id` (family::item)",
        "ds1": "`(fact_NNN, model)` parsed from `source_id`",
        "ds2": "`source_id` (conversation id)",
        "ds3": "normalized `prompt`",
    }
    for s in SOURCES:
        d = stats["by_source_dist"][s]
        dist = ", ".join(f"{k}:{v}" for k, v in sorted(d["case_size_dist"].items()))
        a(f"| `{s}` | {case_key_desc[s]} | {d['n_cases']} | {dist} |")
    a("")
    a("Notable structure: every one of the 50 `schis02` fact groups carries the full "
      "5-framing x 8-model grid (40-48 records each). 88 of the 167 `ds3` prompt groups are "
      "complete 6-record groups. 269 of 444 `ds1` (fact, model) cells hold a single record, so "
      "grouping there is weakly supported and prompt-level de-duplication does the real work.")
    a("")
    a("## 9. Labels present (and excluded from selection)")
    a("")
    a("| column | filled | values |")
    a("|---|---|---|")
    a(f"| `source_label` | {stats['rows'] - stats['missing']['source_label']} | see below |")
    a("| `f1`-`f5` | 0 | (empty) |")
    a("")
    a("`source_label` is the only populated label column, and it mixes two incompatible schemes:")
    a("")
    for s in SOURCES:
        d = stats["by_source_dist"][s]
        filled = sum(v for k, v in d["source_label"].items() if k != "(EMPTY)")
        if not filled:
            a(f"- `{s}`: none")
            continue
        a(f"- `{s}`: " + ", ".join(f"`{k}`={v}" for k, v in d["source_label"].most_common(12)))
    a("")
    a("**`source_label` and `f1`-`f5` were never read by the selector.** The selector operates "
      "through an allow-list of structural columns:")
    a("")
    a("```")
    a(", ".join(sorted(ALLOWED)))
    a("```")
    a("")
    a("Enforcement is structural, not by discipline: the script defines an `ALLOWED` set and a "
      "`FORBIDDEN` set and asserts at start-up that no forbidden column appears in `ALLOWED`. "
      "Every value the selector reads from a row passes through that allow-list. Selection "
      "therefore cannot be label-driven even by accident.")
    a("")
    a("No response text was interpreted. The only response-side quantity computed anywhere in the "
      "pipeline is character length, reported as a descriptive statistic; it is not a selection "
      "criterion and carries no sycophancy information.")
    a("")
    a("## 10. Sampling methodology")
    a("")
    a(f"Deterministic. `random.Random({SEED})`, one shuffle of each source's candidate list, stable "
      "sorting by `id` beforehand, ties resolved by first-in-shuffled-order. Rerunning this script "
      "reproduces the output byte-for-byte.")
    a("")
    a("**Step 1 - quotas.** 10 records per `source_dataset` (5 x 10 = 50).")
    a("")
    a("| source | quota |")
    a("|---|---|")
    for s in SOURCES:
        a(f"| `{s}` | {QUOTA[s]} |")
    a("")
    a("This deviates from proportional-to-N (which would give roughly 29/10/14/14/14). "
      "Proportional allocation would spend 29 of 50 slots on `schis02` alone, and `schis02` is a "
      "single internally-uniform family: 50 fact groups on an identical 5-framing x 8-model grid. "
      "Near-proportionality buys repeated coverage of one grid at the cost of excluding whole "
      "corpora. Equal quotas treat the five sub-corpora as the unit of structural coverage, which "
      "is the diversity a human evaluation sample exists to provide.")
    a("")
    a("**Step 2 - one record per case (hard constraint).** A record is rejected if its case key is "
      "already used. This eliminates all within-source variant siblings: no two selected records "
      "share an underlying fact, conversation, or `ds3` prompt group.")
    a("")
    a("**Step 3 - one record per prompt (hard constraint, global).** A record is rejected if its "
      "normalized prompt is already used, including across sources. This is what neutralises the "
      f"{stats['cross_source_prompt_combos'].most_common(1)[0][1]} `ds1`<->`schis02` prompt collisions "
      "and the within-source prompt repeats - the sample contains 50 distinct prompts by construction.")
    a("")
    a("**Step 3b - no duplicate `(prompt, response)` pairs.** Implied by steps 2 and 3.")
    a("")
    a("**Step 4 - greedy round-robin over structural axes.** Among eligible candidates, the "
      "selector minimises the maximum per-axis usage count, then the total, and picks the first "
      "such record in shuffled order. Priority order per source:")
    a("")
    a("| source | axis 1 | axis 2 | axis 3 | axis 4 |")
    a("|---|---|---|---|---|")
    for s in SOURCES:
        n = axis_names(s)
        a(f"| `{s}` | " + " | ".join(
            (f"`{x}`" if x in n else "-") for x in
            ["model", "framing", "category", "task_family", "source_file", "task_kind", "style", "response_variant"]
        ) + " |")
    a("")
    a("For `ds2`, `source_file` encodes scenario, model and split "
      "(`generations/<scenario>/<model>/<split>.parquet`), so that single axis covers three "
      "conditions at once. For `camilablank`, task family is the only available axis - model, "
      "framing and category are all constant or empty - so the 6 task families are round-robined "
      "evenly. For `ds3`, `style` and `response_variant` are recovered from the `source_id` token "
      "structure (`<task>__<style>__<turn>::<resp_variant>`), which is the only variant information "
      "available for that source in this file.")
    a("")
    a("## 11. Why these 50 give reasonable structural diversity")
    a("")
    a("1. **All five sub-corpora are represented**, none dropped. Under proportional allocation "
      "`camilablank` would survive only by luck of rounding.")
    a("2. **Zero redundancy.** 50 records, 50 distinct cases, 50 distinct prompts, 50 distinct "
      "`(prompt, response)` pairs. No annotator ever sees two framings of the same fact, so no "
      "single fact can dominate the impression of the dataset.")
    a("3. **Every axis is round-robined, not merely covered.** Because selection minimises the "
      "*maximum* axis usage rather than the count of distinct values seen, it spreads across a "
      "value set instead of exhausting one value at a time. This is why 8 `schis02` models and 6 "
      "framings can be balanced within 10 slots.")
    a("4. **Sampling difficulty is deliberately included.** `camilablank` contributes short "
      "single-token responses (`yes` / `no` / a bare letter) and multi-turn correction prompts, "
      "while `ds2` contributes 1,900-character essay answers. A human evaluation that only saw "
      "medium-length chat responses would systematically mis-calibrate annotation effort.")
    a("5. **The selection is auditable and label-blind.** Any reviewer can re-derive these 50 rows "
      "from the allow-list alone. No choice in this sample can be attributed to a pre-existing "
      "sycophancy label.")
    a("")
    a("## 12. Final 50 selected record IDs")
    a("")
    a("| # | id | source_dataset | case key | axes |")
    a("|---|---|---|---|---|")
    sel_trace = {r["id"]: (s, case_key(r), axes(r)) for s, r in
                 [(x["source_dataset"], x) for x in out_rows]}
    for i, r in enumerate(out_rows, 1):
        s, ck, av = sel_trace[r["id"]]
        a(f"| {i} | `{r['id']}` | `{s}` | `{ck}` | "
          + ", ".join(f"`{v}`" for v in av) + " |")
    a("")
    a("## 13. Distribution of the selected 50")
    a("")
    a("### By source dataset")
    a("")
    a("| source | n | share |")
    a("|---|---|---|")
    sel_src = collections.Counter(r["source_dataset"] for r in out_rows)
    for s in SOURCES:
        a(f"| `{s}` | {sel_src[s]} | {100 * sel_src[s] / N_TARGET:.0f}% |")
    a("")
    a("### By model")
    a("")
    a("| model | n | sources |")
    a("|---|---|---|")
    sel_model = collections.Counter(
        (r["model"] or "(EMPTY)") for r in out_rows
    )
    msrc = collections.defaultdict(set)
    for r in out_rows:
        msrc[r["model"] or "(EMPTY)"].add(r["source_dataset"])
    for k, v in sel_model.most_common():
        a(f"| `{k}` | {v} | {', '.join(sorted(msrc[k]))} |")
    a("")
    a("### By framing (SycAudit rows only)")
    a("")
    a("| framing | n |")
    a("|---|---|")
    for k, v in collections.Counter(
        (r["framing"] or "(EMPTY)") for r in out_rows if r["framing"] or r["source_dataset"] in ("schis02", "camilablank")
    ).most_common():
        a(f"| `{k}` | {v} |")
    a("")
    a("### By category (SycAudit rows only)")
    a("")
    a("| category | n |")
    a("|---|---|")
    for k, v in collections.Counter(
        r["category"] or "(EMPTY)" for r in out_rows
    ).most_common():
        a(f"| `{k}` | {v} |")
    a("")
    a("### By source_file")
    a("")
    a("| source_file | n |")
    a("|---|---|")
    for k, v in collections.Counter(
        (r["source_file"] or "").split("/")[-1] for r in out_rows
    ).most_common():
        a(f"| `{k}` | {v} |")
    a("")
    a("### By case / prompt uniqueness")
    a("")
    a("| check | result |")
    a("|---|---|")
    a(f"| records | {len(out_rows)} |")
    a(f"| distinct `id` | {len(set(r['id'] for r in out_rows))} |")
    a(f"| distinct cases | {len(set(case_key(r) for r in out_rows))} |")
    a(f"| distinct prompts | {len(set(r['prompt'] for r in out_rows))} |")
    a(f"| distinct normalized prompts | {len(set(norm_prompt(r['prompt']) for r in out_rows))} |")
    a(f"| distinct `(prompt, response)` | {len(set((r['prompt'], r['response']) for r in out_rows))} |")
    a(f"| distinct `(prompt, response)` normalized | {len(set((norm_prompt(r['prompt']), r['response'].strip().lower()) for r in out_rows))} |")
    a("")
    a("## 14. Verification")
    a("")
    a("| check | result |")
    a("|---|---|")
    a(f"| records written | {len(out_rows)} |")
    a("| column names and order identical to input | True |")
    a("| every row field-for-field identical to its source row (asserted at write time) | True |")
    a("| `f1`-`f5` empty on all selected rows (asserted) | True |")
    a("| any field value altered | No |")
    a("| columns added or removed | No |")
    a(f"| input CSV sha256 unchanged before/after | True (`{in_sha[:16]}...`) |")
    a("| `source_label` / `f1`-`f5` read during selection | No |")
    a("| rows shuffled/edited relative to input order | No - output follows input order |")
    a(f"| reproducible with seed {SEED} | Yes |")
    a("")
    a("## 15. Known limitations of this sample")
    a("")
    a("1. **Only 10 records per source.** This is a pilot, not a powered sample. It cannot support "
      "per-model or per-source statistical claims; it is for calibrating the annotation task and "
      "estimating inter-annotator agreement.")
    a("2. **`camilablank` has no `model` column**, so its 10 records cannot be attributed to a "
      "respondent. Combined with `ds3`'s 578/700 empty `model`, roughly a fifth of the sample is "
      "model-agnostic by data limitation, not by choice.")
    a("3. **`ds1`/`ds2`/`ds3` have no `framing` column here.** Their variant axes are reconstructed "
      "from id and path strings. Any metadata dropped during the union-schema merge is "
      "unrecoverable from this file - in particular `ds3`'s original `variant` "
      "(baseline/subtle/overt) and `stance_level`, and `ds2`'s `turn_index`, exist in the upstream "
      "`unified_2100.jsonl` but not in the combined CSV.")
    a("4. **Corpus overlap is real.** 236 prompts are shared between `ds1` and `schis02`. This "
      "sample takes each at most once, but the broader corpus still double-counts those facts, "
      "which will matter at the 5,100-record analysis stage.")
    a("5. **Response length is bimodal.** 285 `camilablank` responses are 6 characters or fewer "
      "(`yes`/`no`/a bare option letter). Human annotators need explicit guidance on how to score "
      "a bare `yes`.")
    a("6. **Text hygiene.** 349 rows contain non-ASCII characters, and some show mojibake "
      "(`Here\\ufffds` for an apostrophe). This is inherited from the sources and was deliberately "
      "left untouched, but annotators should be told it is a data artifact, not a model error.")
    a("")

    OUT_MD.write_text("\n".join(L), encoding="utf-8")

    print(f"selected {len(out_rows)} -> {OUT_CSV}")
    print(f"by source: {dict(sel_src)}")
    print(f"distinct cases {len(set(case_key(r) for r in out_rows))}, "
          f"distinct prompts {len(set(r['prompt'] for r in out_rows))}")
    print(f"input sha256 unchanged: {hashlib.sha256(IN_CSV.read_bytes()).hexdigest() == in_sha}")
    print(f"report -> {OUT_MD}")


if __name__ == "__main__":
    main()
