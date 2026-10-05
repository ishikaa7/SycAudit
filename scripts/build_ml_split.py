#!/usr/bin/env python3
"""SycAudit ML phase: deterministic, leakage-safe train/validation/test split.

Reads the verified analysis dataset ``ml/analysis/annotated_3322.csv`` (3323
rows) and freezes a leakage-safe 70/15/15 split based on connected components
(union-find) over *exact*, metadata-backed identity relations ONLY.

Grouping relations used (each is deterministic and does not use embeddings,
fuzzy similarity, model, framing, annotation batch, or labels):

  1. SCHIS02 rows sharing the same fact-level ``group_id``.
  2. ds1/ds2/ds3 rows sharing the same ``source_dataset`` + ``source_id``
     (applied only when the grouping audit confirms ``source_id`` marks
     genuinely repeated items).
  3. Rows with exactly identical ``prompt`` text (sha256 of exact bytes).
  4. Rows with exactly identical ``response`` text (sha256 of exact bytes).

The 3rd and 4th rules are global: identical text unites rows even across
different source datasets (e.g. the 194 ds1 <-> schis02 shared prompts).

The split search is deterministic: candidate component orderings are driven by
seeds 42..91; every candidate is scored on row balance, five-facet class
balance, minority-presence in validation/test, and source balance; the best
candidate is frozen.  The test split is NEVER used for model selection.

This script only READS the input dataset and WRITES derived outputs under
``ml/splits/``.  It never modifies dataset/, embeddings/, annotation artifacts,
or rubrics.  Nothing is trained and no rows are dropped.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import statistics
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

SCRIPT_VERSION = "1.2.0"

INPUT_CSV = "ml/analysis/annotated_3322.csv"
OUTPUT_DIR = "ml/splits"
OUTPUT_FILES = [
    "split_assignments.csv",
    "split_manifest.json",
    "split_report.json",
    "split_report.md",
]

ANNOTATED_ROWS = 3323
FACETS = ["f1", "f2", "f3", "f4", "f5"]
TARGET_COLS = [f"target_{f}" for f in FACETS]
CLASSES = [0, 1, 2]
MINORITY_CLASSES = [1, 2]
SEEDS = list(range(42, 92))  # 42..91 inclusive -> 50 candidates
TARGET_FRACTIONS = {"train": 0.70, "validation": 0.15, "test": 0.15}
MINORITY_SPLITS = ["validation", "test"]

# A component larger than this fraction of the dataset is deemed "unexpectedly
# huge": we STOP and report rather than forcing a split on top of it.
MAX_COMPONENT_FRACTION = 0.20

# Split-objective weights (deterministic, documented in the manifest).
SCORE_WEIGHTS = {
    "row_balance": 10.0,
    "facet_distribution": 3.0,
    "minority_presence": 2.0,  # per missing (facet, minority-class, val/test) pair
    "source_distribution": 1.0,
}


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def fail(message: str) -> None:
    print(f"\nERROR: {message}", file=sys.stderr)
    sys.exit(1)


def repo_root() -> Path:
    here = Path(__file__).resolve().parent
    try:
        out = subprocess.run(
            ["git", "-C", str(here), "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        raise SystemExit(
            f"ERROR: cannot locate repository root via git rev-parse --show-toplevel: {exc}"
        ) from exc
    return Path(out.stdout.strip())


def sha256_of_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_of_file(path: Path) -> str:
    return sha256_of_bytes(path.read_bytes())


def _text_hash(text) -> str:
    return sha256_of_bytes(str(text).encode("utf-8"))


def to_py(value):
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, (np.bool_,)):
        return bool(value)
    return value


# --------------------------------------------------------------------------- #
# union-find
# --------------------------------------------------------------------------- #
class DisjointSet:
    def __init__(self, size: int):
        self.parent = list(range(size))

    def find(self, x: int) -> int:
        root = x
        while self.parent[root] != root:
            root = self.parent[root]
        while self.parent[x] != root:  # path compression
            nxt = self.parent[x]
            self.parent[x] = root
            x = nxt
        return root

    def union(self, a: int, b: int) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[rb] = ra


# --------------------------------------------------------------------------- #
# grouping audit
# --------------------------------------------------------------------------- #
def audit_grouping_signals(df: pd.DataFrame) -> dict:
    """Describe the candidate grouping signals (Section 3 of the task spec)."""
    audit = {"schis02_group_id": {}, "other_source_id": {}, "exact_text": {}}

    schis = df[df["source_dataset"] == "schis02"]
    gcounts = schis["group_id"].value_counts()
    audit["schis02_group_id"] = {
        "rows": int(len(schis)),
        "rows_with_group_id": int(schis["group_id"].notna().sum()),
        "missing_group_id": int(schis["group_id"].isna().sum()),
        "unique_group_id": int(schis["group_id"].nunique(dropna=True)),
        "min_rows_per_fact": int(gcounts.min()) if len(gcounts) else None,
        "median_rows_per_fact": round(float(gcounts.median()), 2) if len(gcounts) else None,
        "max_rows_per_fact": int(gcounts.max()) if len(gcounts) else None,
        "fact_ids_look_like_facts": True,  # fact_001..fact_050 verified
        "suitable_for_leakage_grouping": int(schis["group_id"].isna().sum()) == 0
        and int(schis["group_id"].nunique(dropna=True)) > 1,
    }

    other_sources = {}
    for src in ["ds1", "ds2", "ds3"]:
        sub = df[df["source_dataset"] == src]
        sids = sub["source_id"]
        vc = sids.value_counts()
        repeated = vc[vc > 1]
        extra_rows = int(len(sids) - sids.nunique(dropna=True))
        distinct_repeated = int(len(repeated))
        audit_entry = {
            "rows": int(len(sub)),
            "unique_source_id": int(sids.nunique(dropna=True)),
            "missing_source_id": int(sids.isna().sum()),
            "distinct_repeated_source_ids": distinct_repeated,
            "repeated_source_id_rows": extra_rows,
            "max_rows_per_source_id": int(vc.max()) if len(vc) else None,
            "suitable_for_leakage_grouping": distinct_repeated >= 1
            and (int(vc.max()) >= 2 if len(vc) else False),
        }
        other_sources[src] = audit_entry
    audit["other_source_id"] = other_sources

    audit["exact_text"] = {
        "rows_with_duplicate_prompt": int(len(df) - df["prompt_hash"].nunique()),
        "unique_prompts": int(df["prompt_hash"].nunique()),
        "rows_with_duplicate_response": int(len(df) - df["response_hash"].nunique()),
        "unique_responses": int(df["response_hash"].nunique()),
        "duplicate_prompt_hashes_drive_large_components": None,  # filled after components
    }
    return audit


# --------------------------------------------------------------------------- #
# connected components
# --------------------------------------------------------------------------- #
def build_components(df: pd.DataFrame, audit: dict) -> list[dict]:
    """Union rows by reliable links; return deterministic component records."""
    n = len(df)
    dsu = DisjointSet(n)
    recs = df.to_dict("records")

    # 1. SCHIS02 fact-level group_id.
    group_map = defaultdict(list)
    for i, r in enumerate(recs):
        if r["source_dataset"] == "schis02" and pd.notna(r["group_id"]):
            group_map[str(r["group_id"])].append(i)
    for items in group_map.values():
        for j in range(1, len(items)):
            dsu.union(items[0], items[j])

    # 2. ds1/ds2/ds3 source_dataset + source_id (only if audited as suitable).
    for src in ["ds1", "ds2", "ds3"]:
        if audit["other_source_id"].get(src, {}).get("suitable_for_leakage_grouping"):
            src_map = defaultdict(list)
            for i, r in enumerate(recs):
                if r["source_dataset"] == src and pd.notna(r["source_id"]):
                    src_map[str(r["source_id"])].append(i)
            for items in src_map.values():
                for j in range(1, len(items)):
                    dsu.union(items[0], items[j])

    # 3. exact prompt identity (global, across sources).
    prompt_map = defaultdict(list)
    for i, r in enumerate(recs):
        prompt_map[r["prompt_hash"]].append(i)
    for items in prompt_map.values():
        for j in range(1, len(items)):
            dsu.union(items[0], items[j])

    # 4. exact response identity (global, across sources).
    response_map = defaultdict(list)
    for i, r in enumerate(recs):
        response_map[r["response_hash"]].append(i)
    for items in response_map.values():
        for j in range(1, len(items)):
            dsu.union(items[0], items[j])

    # Root every node.
    roots = [dsu.find(i) for i in range(n)]

    # Deterministic representative: min canonical_id per component.
    comp_members: dict[int, list[int]] = defaultdict(list)
    for i, r in enumerate(recs):
        comp_members[roots[i]].append(i)

    comps = []
    for root in comp_members:
        members = comp_members[root]
        min_canon = min((recs[i]["canonical_id"] for i in members))
        comps.append((min_canon, members))
    comps.sort(key=lambda t: t[0])  # stable, deterministic ordering by min canonical_id

    components = []
    for cid, (rep, members) in enumerate(comps):
        rows = sorted(members, key=lambda i: recs[i]["canonical_id"])
        sources = sorted({recs[i]["source_dataset"] for i in rows})
        unique_prompts = len({recs[i]["prompt_hash"] for i in rows})
        unique_responses = len({recs[i]["response_hash"] for i in rows})
        components.append(
            {
                "id": cid,
                "canonical_representative": rep,
                "rows": rows,
                "size": len(rows),
                "sources": sources,
                "unique_prompts": unique_prompts,
                "unique_responses": unique_responses,
            }
        )
    return components


# --------------------------------------------------------------------------- #
# component statistics
# --------------------------------------------------------------------------- #
def component_statistics(components: list[dict]) -> dict:
    sizes = np.array([c["size"] for c in components], dtype=float)
    stats = {
        "number_of_components": int(len(components)),
        "minimum_component_size": int(sizes.min()),
        "median_component_size": round(float(np.median(sizes)), 2),
        "mean_component_size": round(float(sizes.mean()), 2),
        "p90_component_size": round(float(np.quantile(sizes, 0.90)), 2),
        "p95_component_size": round(float(np.quantile(sizes, 0.95)), 2),
        "maximum_component_size": int(sizes.max()),
    }
    largest = sorted(components, key=lambda c: (-c["size"], c["canonical_representative"]))[:10]
    stats["largest_components"] = [
        {
            "component_id": c["id"],
            "size": c["size"],
            "sources": c["sources"],
            "unique_prompts": c["unique_prompts"],
            "unique_responses": c["unique_responses"],
        }
        for c in largest
    ]
    return stats


# --------------------------------------------------------------------------- #
# split scoring
# --------------------------------------------------------------------------- #
def _class_proportions(df: pd.DataFrame, sub: pd.DataFrame) -> dict:
    out = {}
    total = max(int(len(sub)), 1)
    for f in FACETS:
        col = f"target_{f}"
        counts = sub[col].value_counts()
        out[f] = {
            str(c): round(float(counts.get(c, 0)) / total, 6) for c in CLASSES
        }
    return out


def score_candidate(df: pd.DataFrame, assignments: pd.Series, source_full: dict, facets_full: dict) -> dict:
    """Score a split assignment.  Lower is better.  Deterministic."""
    n = int(len(df))
    counts = {s: int((assignments == s).sum()) for s in TARGET_FRACTIONS}

    row_dev = sum(abs(counts[s] / n - TARGET_FRACTIONS[s]) for s in TARGET_FRACTIONS)

    facet_dev = 0.0
    per_split_facets = {}
    for s in TARGET_FRACTIONS:
        sub = df[assignments == s]
        per_split_facets[s] = _class_proportions(df, sub)
        for f in FACETS:
            for c in CLASSES:
                sval = per_split_facets[s][f][str(c)]
                fval = facets_full[f][str(c)]
                facet_dev += abs(sval - fval)

    source_dev = 0.0
    for s in TARGET_FRACTIONS:
        sub = df[assignments == s]
        total_s = max(int(len(sub)), 1)
        for src in sorted(source_full):
            p = sub["source_dataset"].eq(src).sum() / total_s
            source_dev += abs(p - source_full[src])

    missing_minority = 0
    minority_report = {}
    for f in FACETS:
        minority_report[f] = {}
        for c in MINORITY_CLASSES:
            minority_report[f][str(c)] = {}
            for s in MINORITY_SPLITS:
                cnt = int((df.loc[assignments == s, f"target_{f}"] == c).sum())
                minority_report[f][str(c)][s] = cnt
                if cnt == 0:
                    missing_minority += 1

    score = (
        SCORE_WEIGHTS["row_balance"] * row_dev
        + SCORE_WEIGHTS["facet_distribution"] * facet_dev
        + SCORE_WEIGHTS["minority_presence"] * missing_minority
        + SCORE_WEIGHTS["source_distribution"] * source_dev
    )

    return {
        "score": round(score, 6),
        "row_dev": round(row_dev, 6),
        "facet_dev": round(facet_dev, 6),
        "source_dev": round(source_dev, 6),
        "missing_minority_pairs": missing_minority,
        "counts": counts,
        "per_split_facet_counts": {
            s: {
                f: {
                    str(c): int((df.loc[assignments == s, f"target_{f}"] == c).sum())
                    for c in CLASSES
                }
                for f in FACETS
            }
            for s in TARGET_FRACTIONS
        },
        "minority_report": minority_report,
    }


def assign_components(order: list[int], recs_by_comp: dict) -> pd.Series:
    """Greedy row-balance assignment of whole components to train/val/test."""
    counts = {s: 0 for s in TARGET_FRACTIONS}
    target_total = {s: TARGET_FRACTIONS[s] for s in TARGET_FRACTIONS}
    assignments = {}
    for cid in order:
        comp = recs_by_comp[cid]
        size = comp["size"]
        best = min(
            TARGET_FRACTIONS.keys(),
            key=lambda s: (counts[s] + size) / target_total[s],
        )
        counts[best] += size
        for i in comp["rows"]:
            assignments[i] = best
    return pd.Series(assignments).sort_index()


def run_split_search(df: pd.DataFrame, components: list[dict]) -> dict:
    recs_by_comp = {c["id"]: c for c in components}
    comp_ids = [c["id"] for c in components]
    base_order = sorted(comp_ids, key=lambda cid: (recs_by_comp[cid]["size"], cid))

    sources = sorted(df["source_dataset"].unique().tolist())
    source_full = {src: float((df["source_dataset"] == src).mean()) for src in sources}
    facets_full = _class_proportions(df, df)

    candidates = []
    for seed in SEEDS:
        rng = random.Random(seed)
        order = base_order[:]
        rng.shuffle(order)
        assignments = assign_components(order, recs_by_comp)
        row = score_candidate(df, assignments, source_full, facets_full)
        row["seed"] = seed
        candidates.append(row)

    candidates.sort(key=lambda r: (r["score"], r["seed"]))

    # Deterministic recomputation of the best candidate's assignments.
    best = candidates[0]
    rng = random.Random(best["seed"])
    order = base_order[:]
    rng.shuffle(order)
    best_assignments = assign_components(order, recs_by_comp)

    return {
        "sources": sources,
        "source_full": source_full,
        "facets_full": facets_full,
        "best_seed": best["seed"],
        "best_score_breakdown": {k: best[k] for k in ("score", "row_dev", "facet_dev", "source_dev", "missing_minority_pairs", "counts")},
        "best_per_split_facet_counts": best["per_split_facet_counts"],
        "best_minority_report": best["minority_report"],
        "candidate_scores": [
            {"seed": r["seed"], "score": r["score"], "row_dev": r["row_dev"], "facet_dev": r["facet_dev"], "source_dev": r["source_dev"], "missing_minority_pairs": r["missing_minority_pairs"], "counts": r["counts"]}
            for r in candidates
        ],
        "best_assignments": best_assignments,
    }


# --------------------------------------------------------------------------- #
# leakage verification
# --------------------------------------------------------------------------- #
def verify_leakage(df: pd.DataFrame, assignments: pd.Series) -> dict:
    """Hard leakage checks across every split pair.  All must pass."""
    recs = df.assign(_lds=assignments).to_dict("records")
    by_split = {
        s: {
            "canonical_ids": set(),
            "leakage_groups": set(),
            "prompt_hashes": set(),
            "response_hashes": set(),
            "schis02_facts": set(),
            "source_id_keys": set(),
            "components": set(),
        }
        for s in TARGET_FRACTIONS
    }
    seen_group = {}
    for r in recs:
        s = r["_lds"]
        by_split[s]["canonical_ids"].add(r["canonical_id"])
        by_split[s]["leakage_groups"].add(r["_lg"])
        by_split[s]["prompt_hashes"].add(r["prompt_hash"])
        by_split[s]["response_hashes"].add(r["response_hash"])
        by_split[s]["components"].add(r["_lg"])
        if r["source_dataset"] == "schis02" and pd.notna(r["group_id"]):
            by_split[s]["schis02_facts"].add(str(r["group_id"]))
        if r["source_dataset"] in ("ds1", "ds2", "ds3") and pd.notna(r["source_id"]):
            by_split[s]["source_id_keys"].add((r["source_dataset"], str(r["source_id"])))

    checks = {}
    pairs = [("train", "validation"), ("train", "test"), ("validation", "test")]
    for a, b in pairs:
        checks[f"{a}_vs_{b}"] = {
            "no_canonical_id_overlap": len(by_split[a]["canonical_ids"] & by_split[b]["canonical_ids"]) == 0,
            "no_leakage_group_overlap": len(by_split[a]["leakage_groups"] & by_split[b]["leakage_groups"]) == 0,
            "no_exact_prompt_hash_overlap": len(by_split[a]["prompt_hashes"] & by_split[b]["prompt_hashes"]) == 0,
            "no_exact_response_hash_overlap": len(by_split[a]["response_hashes"] & by_split[b]["response_hashes"]) == 0,
            "no_schis02_fact_overlap": len(by_split[a]["schis02_facts"] & by_split[b]["schis02_facts"]) == 0,
            "no_approved_source_id_group_overlap": len(by_split[a]["source_id_keys"] & by_split[b]["source_id_keys"]) == 0,
            "no_connected_component_overlap": len(by_split[a]["components"] & by_split[b]["components"]) == 0,
        }
    all_pass = all(v for pair in checks.values() for v in pair.values())
    return {"checks": checks, "all_pass": all_pass}


# --------------------------------------------------------------------------- #
# distribution helpers
# --------------------------------------------------------------------------- #
def split_distribution(df: pd.DataFrame, assignments: pd.Series, col: str) -> dict:
    out = {}
    full_counts = df[col].value_counts(dropna=False)
    full_total = int(len(df))
    out["full"] = {
        str(k): {"count": int(v), "percent": round(float(v) / full_total * 100.0, 2)}
        for k, v in full_counts.items()
    }
    for s in TARGET_FRACTIONS:
        sub = df[assignments == s]
        tot = max(int(len(sub)), 1)
        counts = sub[col].value_counts(dropna=False)
        out[s] = {
            str(k): {"count": int(v), "percent": round(float(v) / tot * 100.0, 2)}
            for k, v in counts.items()
        }
    return out


def facet_split_distribution(df: pd.DataFrame, assignments: pd.Series) -> dict:
    out = {}
    n = len(df)
    for f in FACETS:
        col = f"target_{f}"
        out[f] = {}
        counts = df[col].value_counts()
        out[f]["full"] = {
            str(c): {"count": int(counts.get(c, 0)), "percent": round(float(counts.get(c, 0)) / n * 100.0, 2)}
            for c in CLASSES
        }
        for s in TARGET_FRACTIONS:
            sub = df[assignments == s]
            tot = max(int(len(sub)), 1)
            counts_s = sub[col].value_counts()
            out[f][s] = {
                str(c): {"count": int(counts_s.get(c, 0)), "percent": round(float(counts_s.get(c, 0)) / tot * 100.0, 2)}
                for c in CLASSES
            }
    return out


# --------------------------------------------------------------------------- #
# outputs
# --------------------------------------------------------------------------- #
def render_markdown(report: dict) -> str:
    lines = []
    lines.append("# SycAudit ML split report")
    lines.append("")
    lines.append(f"- Script version: {report['script_version']}")
    lines.append(f"- Repository HEAD: {report['repository_head']}")
    lines.append(f"- Created (UTC): {report['created_utc']}")
    lines.append(f"- Selected seed: {report['selected_seed']}")
    lines.append(f"- Rows: {report['rows']}")
    lines.append("")
    lines.append("## Final counts")
    lines.append("")
    lines.append("| split | rows | percent |")
    lines.append("|---|---|---|")
    for s, c in report["final_counts"].items():
        lines.append(f"| {s} | {c['count']} | {c['percent']}% |")
    lines.append("")
    lines.append("## Component statistics")
    lines.append("")
    for k, v in report["component_statistics"].items():
        if isinstance(v, (int, float)):
            lines.append(f"- {k}: {v}")
    lines.append("")
    lines.append("### Largest components")
    lines.append("")
    lines.append("| id | size | sources | unique prompts | unique responses |")
    lines.append("|---|---|---|---|---|")
    for c in report["component_statistics"]["largest_components"]:
        lines.append(f"| {c['component_id']} | {c['size']} | {','.join(c['sources'])} | {c['unique_prompts']} | {c['unique_responses']} |")
    lines.append("")
    lines.append("## Grouping audit")
    lines.append("")
    lines.append("```json")
    lines.append(json.dumps(report["grouping_audit"], indent=2, default=str))
    lines.append("```")
    lines.append("")
    lines.append("## Leakage verification")
    lines.append("")
    lines.append(f"- All checks PASS: {report['leakage_verification']['all_pass']}")
    lines.append("")
    lines.append("```json")
    lines.append(json.dumps(report["leakage_verification"]["checks"], indent=2))
    lines.append("```")
    lines.append("")
    lines.append("## Source distribution per split")
    lines.append("")
    for s, counts in report["source_distribution"].items():
        lines.append(f"### {s}")
        lines.append("")
        for src, v in counts.items():
            lines.append(f"- {src}: {v['count']} ({v['percent']}%)")
        lines.append("")
    lines.append("## Facet distributions per split")
    lines.append("")
    for f, dist in report["facet_distributions"].items():
        lines.append(f"### {f}")
        lines.append("")
        for s in ["full", "train", "validation", "test"]:
            parts = ", ".join(f"{c}:{v['count']} ({v['percent']}%)" for c, v in dist[s].items())
            lines.append(f"- {s}: {parts}")
        lines.append("")
    lines.append("## Search candidates (top 10)")
    lines.append("")
    lines.append("| seed | score | row_dev | facet_dev | source_dev | missing_minority |")
    lines.append("|---|---|---|---|---|---|")
    for c in report["candidate_scores"][:10]:
        lines.append(f"| {c['seed']} | {c['score']} | {c['row_dev']} | {c['facet_dev']} | {c['source_dev']} | {c['missing_minority_pairs']} |")
    lines.append("")
    lines.append("> **Split-freeze policy**: the chosen split (seed "
                 f"{report['selected_seed']}) is frozen once created. The TEST split is "
                 "never used for model or hyperparameter selection; split selection above "
                 "was performed only on the derived dataset before any model training.")
    lines.append("")
    lines.append("## Outputs")
    lines.append("")
    for p in report["outputs"]:
        lines.append(f"- {p}")
    lines.append("")
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #
def main() -> int:
    parser = argparse.ArgumentParser(
        description="SycAudit leakage-safe, deterministic 70/15/15 split (derived outputs under ml/splits/)."
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="replace the existing frozen split after an explicit warning (never automatic)",
    )
    args = parser.parse_args()

    root = repo_root()
    head = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
    ).stdout.strip()

    # Fail fast if the frozen split already exists (never automatically overwrite).
    out_dir = root / OUTPUT_DIR
    existing = [p for p in OUTPUT_FILES if (out_dir / p).exists()]
    if existing and not args.force:
        print(
            "Refusing to overwrite existing frozen split (rerun with --force to replace it after an "
            "explicit confirmation):\n  "
            + "\n  ".join(str(out_dir / p) for p in existing),
            file=sys.stderr,
        )
        sys.exit(1)
    if existing and args.force:
        print(
            "WARNING: replacing the existing frozen split in ml/splits/ (--force). "
            "Any downstream artifacts relying on the old split must be re-verified.",
            file=sys.stderr,
        )

    input_path = root / INPUT_CSV
    if not input_path.exists():
        fail(f"input analysis dataset not found: {input_path}")
    input_sha256 = sha256_of_file(input_path)

    df = pd.read_csv(input_path, encoding="utf-8-sig")
    if len(df) != ANNOTATED_ROWS:
        fail(f"input dataset has {len(df)} rows, expected {ANNOTATED_ROWS}")
    if df["canonical_id"].nunique() != len(df):
        fail("input dataset canonical_id is not unique")
    for col in ["canonical_id", "prompt", "response"]:
        if col not in df.columns:
            fail(f"input dataset missing required column {col}")

    df = df.copy()
    df["prompt_hash"] = df["prompt"].map(_text_hash)
    df["response_hash"] = df["response"].map(_text_hash)

    audit = audit_grouping_signals(df)
    components = build_components(df, audit)
    comp_stats = component_statistics(components)

    # Report component landscape and stop on any unexpectedly huge component.
    print("\n== Leakage-group (connected component) analysis ==")
    print(f"rows={len(df)}  components={comp_stats['number_of_components']}  "
          f"min={comp_stats['minimum_component_size']}  median={comp_stats['median_component_size']}  "
          f"mean={comp_stats['mean_component_size']}  p90={comp_stats['p90_component_size']}  "
          f"p95={comp_stats['p95_component_size']}  max={comp_stats['maximum_component_size']}")
    print("largest components:")
    for c in comp_stats["largest_components"][:10]:
        print(f"  id={c['component_id']} size={c['size']} sources={','.join(c['sources'])} "
              f"prompts={c['unique_prompts']} responses={c['unique_responses']}")
    huge = [c for c in components if c["size"] / len(df) >= MAX_COMPONENT_FRACTION]
    if huge:
        fail(
            f"{len(huge)} unexpectedly huge leakage component(s) (>= {MAX_COMPONENT_FRACTION:.0%} of rows); "
            f"stopping before split. Largest: "
            + json.dumps([{"id": c["id"], "size": c["size"]} for c in huge[:10]], indent=2)
        )

    # Group id mapping (deterministic by component order).
    group_of_row = {}
    for c in components:
        for i in c["rows"]:
            group_of_row[i] = c["id"]
    df["_lg"] = df.index.map(group_of_row.__getitem__)

    search = run_split_search(df, components)
    assignments = search["best_assignments"]

    # Coverage.
    counts = {s: int((assignments == s).sum()) for s in TARGET_FRACTIONS}
    if sum(counts.values()) != len(df):
        fail("coverage error: not all rows assigned to exactly one split")

    leakage = verify_leakage(df, assignments)
    if not leakage["all_pass"]:
        fail(
            "leakage verification FAILED; refusing to freeze split:\n"
            + json.dumps(leakage, indent=2)
        )

    source_distribution = split_distribution(df, assignments, "source_dataset")
    batch_distribution = split_distribution(df, assignments, "annotation_batch")
    facet_distributions = facet_split_distribution(df, assignments)

    created_utc = datetime.now(timezone.utc).isoformat(timespec="seconds")

    assignment_records = []
    for _, r in df.sort_values("canonical_id").iterrows():
        assignment_records.append(
            {
                "canonical_id": r["canonical_id"],
                "split": assignments.loc[r.name],
                "leakage_group_id": int(r["_lg"]),
                "source_dataset": r["source_dataset"],
                "prompt_hash": r["prompt_hash"],
                "response_hash": r["response_hash"],
            }
        )
    assignment_df = pd.DataFrame(assignment_records)

    # --- frozen output write (guarded; existence already checked at start) ---
    out_dir.mkdir(parents=True, exist_ok=True)
    assignments_path = out_dir / "split_assignments.csv"
    assignment_df.to_csv(assignments_path, index=False, encoding="utf-8", lineterminator="\n")
    assignment_sha = sha256_of_file(assignments_path)

    final_counts = {s: {"count": counts[s], "percent": round(counts[s] / len(df) * 100.0, 2)} for s in TARGET_FRACTIONS}
    source_tab = {s: {str(k): v for k, v in source_distribution[s].items()} for s in TARGET_FRACTIONS}
    annotate_batch_tab = {s: {str(k): v for k, v in batch_distribution[s].items()} for s in TARGET_FRACTIONS}

    manifest = {
        "script_version": SCRIPT_VERSION,
        "created_utc": created_utc,
        "repository_head": head,
        "input_dataset": {"path": INPUT_CSV, "rows": int(len(df)), "sha256": input_sha256},
        "rows": int(len(df)),
        "random_seeds_attempted": SEEDS,
        "selected_seed": int(search["best_seed"]),
        "split_objective_weights": SCORE_WEIGHTS,
        "grouping_rules": [
            "schis02 rows sharing the same fact-level group_id are grouped (audit-verified)",
            "ds1/ds2/ds3 rows sharing the same source_dataset+source_id are grouped when the grouping audit confirms source_id marks repeated items",
            "rows with exactly identical prompt text (sha256 of exact bytes) are grouped, globally across source datasets",
            "rows with exactly identical response text (sha256 of exact bytes) are grouped, globally across source datasets",
            "no embeddings, fuzzy similarity, model, framing, annotation batch, or labels are used for grouping",
        ],
        "grouping_statistics": comp_stats,
        "component_huge_stop_threshold_fraction": MAX_COMPONENT_FRACTION,
        "final_counts": final_counts,
        "source_distribution": source_tab,
        "annotation_batch_distribution": annotate_batch_tab,
        "facet_distributions": facet_distributions,
        "leakage_verification": {
            "all_pass": bool(leakage["all_pass"]),
            "checks": leakage["checks"],
        },
        "assignments": {
            "path": f"{OUTPUT_DIR}/split_assignments.csv",
            "sha256": assignment_sha,
            "split_value_notes": "split is exactly one of train/validation/test; every one of the "
            f"{len(df)} annotated rows belongs to exactly one split.",
        },
        "freeze_policy_note": (
            "The test split is frozen and MUST NOT be used for model/hyperparameter selection. "
            "The split-selection search above used label distributions only to choose the seed "
            "BEFORE any model was trained; the chosen split is now immutable."
        ),
        "outputs": [f"{OUTPUT_DIR}/{p}" for p in OUTPUT_FILES],
    }

    report = {
        "script_version": SCRIPT_VERSION,
        "created_utc": created_utc,
        "repository_head": head,
        "input_dataset": {"path": INPUT_CSV, "rows": int(len(df)), "sha256": input_sha256},
        "rows": int(len(df)),
        "selected_seed": int(search["best_seed"]),
        "seeds_attempted": SEEDS,
        "component_statistics": comp_stats,
        "grouping_audit": audit,
        "final_counts": final_counts,
        "source_distribution": source_distribution,
        "annotation_batch_distribution": batch_distribution,
        "facet_distributions": facet_distributions,
        "leakage_verification": {"all_pass": bool(leakage["all_pass"]), "checks": leakage["checks"]},
        "candidate_scores": search["candidate_scores"],
        "best_score_breakdown": search["best_score_breakdown"],
        "best_per_split_facet_counts": search["best_per_split_facet_counts"],
        "best_minority_report": search["best_minority_report"],
        "outputs": [f"{OUTPUT_DIR}/{p}" for p in OUTPUT_FILES],
    }

    (out_dir / "split_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8"
    )
    (out_dir / "split_report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8"
    )
    (out_dir / "split_report.md").write_text(render_markdown(report), encoding="utf-8")

    print("\n== Final split ==")
    for s in TARGET_FRACTIONS:
        c = final_counts[s]
        print(f"  {s:<11} {c['count']:>5} rows  ({c['percent']}%)")
    print(f"\nSelected seed: {search['best_seed']}")
    print(f"Leakage verification: {'PASS' if leakage['all_pass'] else 'FAIL'} (all 21 pair-checks)")
    print(f"Source composition per split:")
    for s in TARGET_FRACTIONS:
        parts = ", ".join(f"{src}={v['count']}" for src, v in sorted(source_tab[s].items()))
        print(f"  {s}: {parts}")
    print("\nOutput:")
    for p in OUTPUT_FILES:
        print(f"  ml/splits/{p}")
    print("\nAll 3323 rows assigned to exactly one split. No source dataset/annotation/embedding file was modified.")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())