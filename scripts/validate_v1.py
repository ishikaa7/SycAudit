#!/usr/bin/env python3
"""Validate SycAudit Dataset v1 files (independent check of train/validation/test).

Checks (per the construction spec):
  * every record has exactly one fact_id and one model
  * every record has exactly the five expected framings (neutral, original,
    leading, opinion, authority)
  * no duplicate (fact_id, model) records (within a split and dataset-wide)
  * no fact_id appears in more than one split
  * every framing has a deterministic T=0 response (temperature == 0.0)
  * labels are only the existing source labels S1/S2/C/H/R
  * prompts and completions are non-empty
  * model/framing/fact metadata are internally consistent
  * JSONL files parse completely
  * total units == train + validation + test; matches dataset_manifest.json

Prints a concise construction summary and exits non-zero on any failure.
"""
from __future__ import annotations

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from group_inspect import FRAMINGS, MODEL_SHORT  # noqa: E402

V1 = pathlib.Path(__file__).resolve().parent.parent / "dataset" / "v1"
FILES = ["train", "validation", "test"]
LABELS_OK = {"S1", "S2", "C", "H", "R"}
CATS_OK = {"s1_ablation_subset", "false-premise-health"}
MODEL_FULLS = set(MODEL_SHORT.keys())


def load(name):
    path = V1 / f"{name}.jsonl"
    records = []
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError as e:
            raise RuntimeError(f"{name}.jsonl line {i}: malformed JSON: {e}")
    return records


def main():
    fails = []
    total_checks = 0

    def check(ok, label, detail=""):
        nonlocal total_checks
        total_checks += 1
        if not ok:
            fails.append((label, detail))

    data = {n: load(n) for n in FILES}
    manifest = json.loads((V1 / "dataset_manifest.json").read_text(encoding="utf-8"))

    # --- record-level checks -------------------------------------------------
    for name, records in data.items():
        seen = set()
        for r in records:
            fid = r.get("fact_id")
            model = r.get("model")
            check(isinstance(fid, str) and fid, f"{name}: fact_id present", str(r.get("fact_id")))
            check(isinstance(model, str) and model, f"{name}: model present", str(r.get("model")))
            key = (fid, model)
            check(key not in seen, f"{name}: duplicate (fact_id, model)", str(key))
            seen.add(key)

            fram = r.get("framings")
            check(isinstance(fram, dict) and set(fram.keys()) == set(FRAMINGS),
                  f"{name} {key}: exactly five framings", str(sorted(fram.keys()) if isinstance(fram, dict) else None))

            check(r.get("category") in CATS_OK, f"{name} {key}: category valid", str(r.get("category")))
            check(r.get("model_full") in MODEL_FULLS, f"{name} {key}: model_full valid", str(r.get("model_full")))
            check(MODEL_SHORT.get(r.get("model_full")) == model,
                  f"{name} {key}: model_short matches model_full", f"{model} vs {r.get('model_full')}")

            for f in FRAMINGS:
                c = fram.get(f)
                check(isinstance(c, dict), f"{name} {key} {f}: framing entry dict", str(c))
                if not isinstance(c, dict):
                    continue
                check(c.get("framing") == f, f"{name} {key} {f}: framing key matches", str(c.get("framing")))
                check(c.get("temperature") == 0.0, f"{name} {key} {f}: T=0", str(c.get("temperature")))
                check(isinstance(c.get("prompt"), str) and c["prompt"].strip(),
                      f"{name} {key} {f}: prompt non-empty")
                check(isinstance(c.get("completion"), str) and c["completion"].strip(),
                      f"{name} {key} {f}: completion non-empty")
                check(c.get("label") in LABELS_OK, f"{name} {key} {f}: label valid", str(c.get("label")))
                check(c.get("fact_id") == fid, f"{name} {key} {f}: inner fact_id consistent")
                check(c.get("model") == r.get("model_full"), f"{name} {key} {f}: inner model consistent")
                check(c.get("model_short") == model, f"{name} {key} {f}: inner model_short consistent")
                check(c.get("category") == r.get("category"), f"{name} {key} {f}: inner category consistent")
                check(c.get("is_paper1_bridge") in (True, False, None),
                      f"{name} {key} {f}: is_paper1_bridge valid", str(c.get("is_paper1_bridge")))
                check(isinstance(c.get("sample_idx"), int) and c.get("sample_idx") >= 0,
                      f"{name} {key} {f}: sample_idx int", str(c.get("sample_idx")))
                check(isinstance(c.get("seed"), int), f"{name} {key} {f}: seed int", str(c.get("seed")))
                check(isinstance(c.get("source_file"), str) and c["source_file"],
                      f"{name} {key} {f}: source_file present")
                check(isinstance(c.get("source_id"), str) and c["source_id"],
                      f"{name} {key} {f}: source_id present")

    # --- cross-split checks --------------------------------------------------
    def fact_set(name):
        return {r["fact_id"] for r in data[name]}

    fs = {n: fact_set(n) for n in FILES}
    check(len(fs["train"] & fs["validation"]) == 0, "no train/validation fact overlap",
          str(sorted(fs["train"] & fs["validation"])))
    check(len(fs["train"] & fs["test"]) == 0, "no train/test fact overlap",
          str(sorted(fs["train"] & fs["test"])))
    check(len(fs["validation"] & fs["test"]) == 0, "no validation/test fact overlap",
          str(sorted(fs["validation"] & fs["test"])))

    all_keys = []
    for records in data.values():
        all_keys += [(r["fact_id"], r["model"]) for r in records]
    check(len(all_keys) == len(set(all_keys)), "no duplicate (fact_id, model) dataset-wide",
          f"{len(all_keys)} records, {len(set(all_keys))} unique")

    # --- total counts / manifest ---------------------------------------------
    expected = {"train": 30 * 8, "validation": 10 * 8, "test": 10 * 8}
    for n in FILES:
        check(len(data[n]) == expected[n], f"{n} unit count == {expected[n]}",
              f"found {len(data[n])}")
        check(manifest[f"{n}_unit_count"] if n != "validation" else manifest["validation_unit_count"]
              == len(data[n]),
              f"manifest {n}_unit_count matches file", str(len(data[n])))
    total = sum(len(data[n]) for n in FILES)
    check(total == manifest["total_unit_count"], "manifest total_unit_count matches",
          f"{total} vs {manifest['total_unit_count']}")
    check(total == expected["train"] + expected["validation"] + expected["test"],
          "total == 400", str(total))
    check(set(fs["train"] | fs["validation"] | fs["test"]) == set(manifest["train_fact_ids"]
                                                                  + manifest["validation_fact_ids"]
                                                                  + manifest["test_fact_ids"]),
          "manifest fact sets == dataset facts")
    check(len(fs["train"]) == manifest["train_fact_count"]
          and len(fs["validation"]) == manifest["validation_fact_count"]
          and len(fs["test"]) == manifest["test_fact_count"],
          "manifest fact counts match")

    # --- summary ---------------------------------------------------------------
    labels = {n: {} for n in FILES}
    for n in FILES:
        counts = {}
        for r in data[n]:
            for f, c in r["framings"].items():
                counts[c["label"]] = counts.get(c["label"], 0) + 1
        labels[n] = counts

    print("\n=== SycAudit Dataset v1 - construction summary ===")
    print(f"  units: train {len(data['train'])} | validation {len(data['validation'])} "
          f"| test {len(data['test'])} | total {total}")
    print(f"  facts: train {len(fs['train'])} | validation {len(fs['validation'])} "
          f"| test {len(fs['test'])}")
    print(f"  framing completeness: 5/5 per unit ({len(FRAMINGS)} framings x {total} units = "
          f"{len(FRAMINGS) * total} T=0 responses)")
    total_labels = sum(sum(v.values()) for v in labels.values())
    print(f"  label distribution (all splits): {total_labels} labeled responses -> "
          + ", ".join(f"{k}={sum(labels[n].get(k, 0) for n in FILES)}" for k in ["S1", "S2", "C", "H", "R"]))
    for n in FILES:
        print(f"    {n}: " + ", ".join(f"{k}={v}" for k, v in sorted(labels[n].items())))
    models = sorted({r["model"] for records in data.values() for r in records})
    print(f"  models per split: {len(models)} ({', '.join(models)})")

    if fails:
        print(f"\nFAILED ({len(fails)} check(s)):")
        for label, detail in fails:
            print(f"  - {label}: {detail}")
        raise SystemExit(1)
    print(f"\nALL {total_checks} VALIDATION CHECKS PASSED.")


if __name__ == "__main__":
    main()