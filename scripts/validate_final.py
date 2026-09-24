#!/usr/bin/env python3
"""Independent validation of dataset/final/sycaudit_evaluator_dataset.csv.

Re-derives the authoritative source records (existing extraction logic) and checks
every CSV row for provenance, metadata fidelity, integrity and coverage per the
construction spec §9. Exits non-zero on any failure.
"""
from __future__ import annotations

import csv
import json
import pathlib
import sys
from collections import Counter, defaultdict

REPO = pathlib.Path(__file__).resolve().parent.parent
DATASET = REPO / "dataset"
FINAL = DATASET / "final"
CSV_PATH = FINAL / "sycaudit_evaluator_dataset.csv"
MANIFEST = FINAL / "dataset_manifest.json"

sys.path.insert(0, str(REPO / "scripts"))
from build_final import (  # noqa: E402
    COLUMNS,
    build_schis02_rows,
    build_camilablank_rows,
    row_id,
)
from build_final import FRAMINGS  # noqa: E402

LABELS_OK = {"S1", "S2", "C", "H", "R"}


def main():
    fails = []
    warnings = []

    # ---- parse CSV ----
    rows = []
    with open(CSV_PATH, encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        if reader.fieldnames != COLUMNS:
            fails.append(f"header mismatch: {reader.fieldnames} != {COLUMNS}")
        for r in reader:
            rows.append(r)
    total = len(rows)
    if total < 2500:
        fails.append(f"row count {total} < 2500")

    # ---- id / dataset / empty checks ----
    ids = [r["id"] for r in rows]
    if len(ids) != len(set(ids)):
        fails.append("duplicate id values")
    for r in rows:
        if r["source_dataset"] not in {"schis02", "camilablank"}:
            fails.append(f"bad source_dataset {r['source_dataset']!r}")
        if not r["prompt"].strip():
            fails.append(f"empty prompt ({r['id']})")
        if not r["response"].strip():
            fails.append(f"empty response ({r['id']})")
        for f in ("f1", "f2", "f3", "f4", "f5"):
            if r[f] not in ("", None):
                fails.append(f"f1-f5 must be empty ({r['id']})")
    # deterministic id check
    for r in rows:
        expect = row_id(r["source_dataset"], r["source_file"], r["source_id"],
                        r["prompt"], r["response"])
        if r["id"] != expect:
            fails.append(f"id mismatch for {r['id']} (expected {expect})")

    # ---- rebuild authoritative sources ----
    schis02_authoritative = {  # (source_file, source_id, prompt, response) -> rowdict
        (r["source_file"], r["source_id"], r["prompt"], r["response"]): r
        for r in build_schis02_rows()}
    cami_authoritative = {}
    for r in build_camilablank_rows():
        cami_authoritative.setdefault(
            (r["source_file"], r["source_id"], r["prompt"], r["response"]), r)

    # ---- per-row provenance verification ----
    dup_records = []
    seen_pairs = set()
    dup_pairs = 0
    gates = {"schis02_seen": set(), "cami_family_rows": defaultdict(int)}
    for r in rows:
        key = (r["source_dataset"], r["source_file"], r["source_id"],
               r["prompt"], r["response"])
        if key in dup_records:
            fails.append(f"duplicate source record row: {r['source_id']}")
        dup_records.append(key)
        pair = (r["prompt"], r["response"])
        if pair in seen_pairs:
            dup_pairs += 1
        seen_pairs.add(pair)

        if r["source_dataset"] == "schis02":
            src = schis02_authoritative.get(
                (r["source_file"], r["source_id"], r["prompt"], r["response"]))
            if src is None:
                fails.append(f"unresolved provenance: {r['source_file']}::{r['source_id']}")
                continue
            for field in ("model", "framing", "prompt", "response",
                          "temperature", "sample_idx", "seed"):
                if r[field] != str(src.get(field, "")):
                    fails.append(f"metadata drift {field} on {r['source_id']}: "
                                 f"csv={r[field]!r} src={src.get(field)!r}")
            if r["group_id"] != src["group_id"]:
                fails.append(f"group_id drift on {r['source_id']}")
            if r["framing"] not in FRAMINGS:
                fails.append(f"framing not in FRAMINGS: {r['framing']}")
            if r["source_label"] not in LABELS_OK:
                fails.append(f"schis02 source_label not S1-S5: {r['source_label']!r}")
            if r["is_paper1_bridge"] not in ("", "True", "False"):
                fails.append(f"schis02 is_paper1_bridge bad: {r['is_paper1_bridge']!r}")
            if r["category"] not in ("s1_ablation_subset", "false-premise-health", ""):
                fails.append(f"schis02 category bad: {r['category']!r}")
        else:  # camilablank
            if r["framing"] != "unframed":
                fails.append(f"camilablank framing must be 'unframed': {r['framing']!r}")
            src = cami_authoritative.get(
                (r["source_file"], r["source_id"], r["prompt"], r["response"]))
            if src is None:
                fails.append(f"unresolved camilablank provenance: {r['source_id']}")
                continue
            if r["group_id"] != src["group_id"]:
                fails.append(f"camilablank group_id drift: {r['source_id']}")
            if any(r[f] != "" for f in ("temperature", "sample_idx", "seed",
                                        "category", "is_paper1_bridge", "model")):
                fails.append(f"camilablank invented metadata on {r['source_id']}")
            fam = r["source_id"].split("::")[0]
            gates["cami_family_rows"][fam] += 1

    # ---- coverage / reporting ----
    s_rows = [r for r in rows if r["source_dataset"] == "schis02"]
    c_rows = [r for r in rows if r["source_dataset"] == "camilablank"]
    sch = Counter()
    for r in s_rows:
        sch[(r["group_id"], r["framing"], r["temperature"])] += 1
    t0 = sum(1 for r in s_rows if r["temperature"] == "0.0")
    tgt = len(s_rows) - t0
    models = Counter(r["model"] for r in s_rows)
    framings = Counter(r["framing"] for r in s_rows)
    facts = Counter(r["group_id"] for r in s_rows)
    labels = Counter(r["source_label"] for r in s_rows if r["source_label"])
    cami_groups = len({r["group_id"] for r in c_rows})

    # manifest cross-check
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if manifest["total_rows"] != total:
        fails.append(f"manifest total_rows {manifest['total_rows']} != {total}")
    if manifest["source_counts"] != {"schis02": len(s_rows), "camilablank": len(c_rows)}:
        fails.append("manifest source_counts mismatch")

    if dup_pairs:
        warnings.append(f"identical (prompt, response) pairs appear {dup_pairs} times "
                        "(across sources; expected 0)")

    # ---- report ----
    print("=== FINAL DATASET VALIDATION REPORT ===")
    print(f"rows: {total:,}  (schis02 {len(s_rows):,} / camilablank {len(c_rows):,})")
    print(f"T=0 rows: {t0}   T>0 rows: {tgt}")
    print("SCHIS02 facts:", len(facts), "| models:", dict(sorted(models.items())))
    print("SCHIS02 framings:", dict(sorted(framings.items())))
    print(f"SCHIS02 rows per fact: min={min(facts.values())} "
          f"max={max(facts.values())} mean={sum(facts.values())/len(facts):.1f}")
    print("SCHIS02 label distribution:", dict(sorted(labels.items())))
    print(f"CamilaBlank groups: {cami_groups} | families: "
          f"{dict(sorted(gates['cami_family_rows'].items()))}")
    print("CamilaBlank rows with conversational history (2+ turns):",
          sum(1 for r in c_rows
              if r["source_id"].split("::")[0] != "mmlu_single_turn"))

    if fails:
        print("\nFAILED CHECKS:")
        for f in fails[:40]:
            print("  -", f)
        print(f"  ... {len(fails) - min(40, len(fails))} more" if len(fails) > 40 else "")
        raise SystemExit(1)
    for w in warnings:
        print("WARNING:", w)
    print("\nALL CHECKS PASSED.")


if __name__ == "__main__":
    main()