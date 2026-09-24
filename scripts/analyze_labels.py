#!/usr/bin/env python3
"""READ-ONLY label-behavior statistics for the schis02 pool (compute layer).

Everything here is descriptive analysis of existing source labels (gpt4o_label).
Nothing is modified, sampled, re-labeled, split or deleted. Statistical tests
(exact McNemar / binomial, Wilcoxon signed-rank) are applied only to (fact,
model)-paired T=0 labels where within-unit pairing is legitimate.

Views:
  POOL   - the existing extracted pool (7,455 unique (prompt, completion) pairs);
           the 4,462 phase-3 rows carry the source gpt4o_label.
  SOURCE - raw phase-3 labeled files (all records incl. stochastic draws) plus
           phase-4 labeled files, read only to quantify T=0 vs stochastic-draw
           label variability (the pool collapses identical completions).

Outputs (new files only):
    dataset/schis02_label_analysis.json
Run `render_label_report.py` to also produce the markdown report.
"""
from __future__ import annotations

import json
import math
import pathlib
import statistics
import sys
from collections import Counter, defaultdict

import numpy as np
from scipy import stats as sps

REPO = pathlib.Path(__file__).resolve().parent.parent
DATASET = REPO / "dataset"
sys.path.insert(0, str(REPO / "scripts"))
from group_inspect import reconstitute_pool, MODEL_SHORT, FRAMINGS  # noqa: E402
from extract_preview import iter_records, FALSE_PREMISES_CLEAN  # noqa: E402

LABELS = ["S1", "S2", "C", "H", "R"]
PHASE3_LABELED = FALSE_PREMISES_CLEAN[:6]
PHASE4_LABELED = [FALSE_PREMISES_CLEAN[8], FALSE_PREMISES_CLEAN[10]]

AGREE_PHRASES = ("i agree", "you're correct", "you are correct", "you're right",
                 "you are right", "yes, that", "yes, it is", "that is correct",
                 "correct,", "great question", "a fair point",
                 "you raise a good point", "that's a good point", "yes, great")
REFUSE_PHRASES = ("i can't", "i cannot", "cannot provide", "i'm sorry", "i am sorry",
                  "i am not able", "i'm not able", "not able to provide", "i don't have",
                  "i do not have information", "can't help", "cannot answer",
                  "i won't", "safety")


def rate(cnt, n):
    return (100.0 * cnt / n) if n else 0.0


def lab_dist(rows):
    c = Counter(r["label"] for r in rows)
    n = sum(c.values())
    return {k: {"count": c.get(k, 0), "rate": rate(c.get(k, 0), n)} for k in LABELS}, n


def fmt_p(p):
    return f"{p:.4f}" if p >= 0.0001 else f"{p:.2e}"


def load_source_labeled(rel_paths):
    out = []
    for rel in rel_paths:
        file_stem = rel.replace("\\", "/").split("/")[-1].rsplit(".", 1)[0]
        for rec, _ in iter_records(DATASET / rel):
            if rec is None:
                continue
            lbl = rec.get("gpt4o_label")
            if lbl not in LABELS:
                continue
            out.append({
                "fact_id": rec.get("fact_id"),
                "framing": rec.get("framing"),
                "model_short": MODEL_SHORT.get(rec.get("model") or "", str(rec.get("model"))),
                "temperature": rec.get("temperature"),
                "sample_idx": rec.get("sample_idx"),
                "label": lbl,
                "category": rec.get("category"),
                "completion": (rec.get("completion") or "").strip(),
            })
    return out


def two_sided_p(b, c):
    n = b + c
    if n == 0:
        return None, 0
    return float(sps.binomtest(c, n, 0.5, alternative="two-sided").pvalue), n


def compute():
    pool, _, _ = reconstitute_pool()
    pool_rows = []
    for r in pool:
        lbl = r.get("gpt4o_label")
        if lbl not in LABELS:
            continue
        pool_rows.append({
            "fact_id": r["fact_id"], "framing": r["framing"], "model_short": r["model_short"],
            "temperature": r["temperature"], "label": lbl, "category": r["category"],
            "completion": r["completion"],
        })
    pool_labeled = len(pool_rows)

    src3 = load_source_labeled(PHASE3_LABELED)
    src4 = load_source_labeled(PHASE4_LABELED)
    src_all = src3 + src4
    src3_tg = [r for r in src3 if float(r["temperature"]) > 0.0]

    J = {"_meta": {"pool_labeled_rows": pool_labeled, "source_phase3_records": len(src3),
                   "source_phase4_records": len(src4)}}

    # 1. framing distribution -------------------------------------------------
    framing_pool, framing_src = {}, {}
    for f in FRAMINGS:
        dist, n = lab_dist([r for r in pool_rows if r["framing"] == f])
        framing_pool[f] = {"labeled_pool_rows": n, **dist}
        dist, n = lab_dist([r for r in src_all if r["framing"] == f])
        framing_src[f] = {"source_labeled_records": n, **dist}
    J["framing_label_distribution_pool"] = framing_pool
    J["framing_label_distribution_source_all"] = framing_src

    # 1b. model x framing, SOURCE all temps ----------------------------------
    model_framing = {}
    for m in sorted({r["model_short"] for r in src_all}):
        model_framing[m] = {}
        for f in FRAMINGS:
            rows = [r for r in src_all if r["model_short"] == m and r["framing"] == f]
            dist, n = lab_dist(rows)
            model_framing[m][f] = {"n": n, "S1_pct": dist["S1"]["rate"],
                                   "C_pct": dist["C"]["rate"], "H_pct": dist["H"]["rate"],
                                   "R_pct": dist["R"]["rate"]}
    J["model_x_framing_source_alltemps"] = model_framing
    for m in model_framing:
        model_framing[m]["_delta_S1_authority_minus_neutral_pp"] = (
            model_framing[m]["authority"]["S1_pct"] - model_framing[m]["neutral"]["S1_pct"])

    # 1c. model x framing, POOL ----------------------------------------------
    pool_models = sorted({r["model_short"] for r in pool_rows})
    model_framing_pool = {}
    for m in pool_models:
        model_framing_pool[m] = {}
        for f in FRAMINGS:
            rows = [r for r in pool_rows if r["model_short"] == m and r["framing"] == f]
            dist, n = lab_dist(rows)
            model_framing_pool[m][f] = {"n": n, "S1_pct": dist["S1"]["rate"],
                                        "C_pct": dist["C"]["rate"]}
    J["model_x_framing_pool"] = model_framing_pool

    model_overall = {}
    for m in pool_models:
        rows = [r for r in pool_rows if r["model_short"] == m]
        dist, n = lab_dist(rows)
        model_overall[m] = {"pool_rows": n, "S1_pct": dist["S1"]["rate"],
                            "C_pct": dist["C"]["rate"]}
    J["model_overall_pool_S1_C"] = model_overall
    s1rates = [model_overall[m]["S1_pct"] for m in pool_models]

    # chi2 (model, S1) shortcut check over pool rows --------------------------
    tab = [[model_overall[m]["pool_rows"] * model_overall[m]["S1_pct"] / 100,
            model_overall[m]["pool_rows"] * (1 - model_overall[m]["S1_pct"] / 100)]
           for m in pool_models]
    chi2_model = None
    try:
        cs, p, dof, _ = sps.chi2_contingency(np.array(tab))
        chi2_model = {"chi2": float(cs), "p": fmt_p(p), "dof": int(dof)}
    except Exception:
        pass
    J["model_identity_confounder"] = {
        "S1_rate_range_pp": [round(min(s1rates), 1), round(max(s1rates), 1)],
        "S1_rate_spread_pp": round(max(s1rates) - min(s1rates), 1),
        "chi2_model_vs_S1": chi2_model}

    # 2. within-fact framing comparison (POOL) --------------------------------
    by_fact_pool = defaultdict(list)
    for r in pool_rows:
        by_fact_pool[r["fact_id"]].append(r)
    facts_pool = sorted(by_fact_pool)
    fact_framing = {}
    for g in facts_pool:
        fact_framing[g] = {}
        for f in FRAMINGS:
            rows = [r for r in by_fact_pool[g] if r["framing"] == f]
            dist, n = lab_dist(rows)
            fact_framing[g][f] = {"n": n, **{k: v["rate"] for k, v in dist.items()}}
    J["fact_framing_label_rates_pool"] = fact_framing

    both_s1_non = sum(1 for g in facts_pool
                      if any(r["label"] == "S1" for r in by_fact_pool[g])
                      and any(r["label"] != "S1" for r in by_fact_pool[g]))

    fact_s1shift = {}
    for g in facts_pool:
        nS, aS = fact_framing[g]["neutral"], fact_framing[g]["authority"]
        fact_s1shift[g] = {
            "neutral_S1_rate": nS["S1"], "authority_S1_rate": aS["S1"],
            "delta_S1_ntoa_pp": aS["S1"] - nS["S1"],
            "delta_C_ntoa_pp": aS["C"] - nS["C"],
            "delta_CH_ntoa_pp": (aS["C"] + aS["H"]) - (nS["C"] + nS["H"]),
        }
    J["fact_s1shift_neutral_vs_authority_pool"] = fact_s1shift
    deltas = [v["delta_S1_ntoa_pp"] for v in fact_s1shift.values()]

    multi_label_cells = 0
    tot_cells = 0
    for g in facts_pool:
        for f in FRAMINGS:
            rows = [r for r in by_fact_pool[g] if r["framing"] == f]
            if not rows:
                continue
            tot_cells += 1
            if len({r["label"] for r in rows}) >= 2:
                multi_label_cells += 1

    J["facts_stats"] = {
        "n_facts": len(facts_pool),
        "facts_with_both_S1_and_nonS1": both_s1_non,
        "facts_with_S1_at_neutral": sum(1 for g in facts_pool if fact_framing[g]["neutral"]["S1"] > 0),
        "facts_with_S1_at_authority": sum(1 for g in facts_pool if fact_framing[g]["authority"]["S1"] > 0),
        "facts_delta_S1_ntoa_up_gt0p5pp": sum(1 for v in fact_s1shift.values() if v["delta_S1_ntoa_pp"] > 0.5),
        "facts_delta_S1_ntoa_down_lt0p5pp": sum(1 for v in fact_s1shift.values() if v["delta_S1_ntoa_pp"] < -0.5),
        "fact_framing_cells_total": tot_cells,
        "fact_framing_cells_with_multiple_labels": multi_label_cells,
        "median_delta_S1_ntoa_pp": round(statistics.median(deltas), 2),
        "min_delta_S1_ntoa_pp": round(min(deltas), 2),
        "max_delta_S1_ntoa_pp": round(max(deltas), 2),
    }

    # 4. T=0 vs stochastic -----------------------------------------------------
    t0_ph3 = {}
    for r in src3:
        if float(r["temperature"]) == 0.0:
            t0_ph3[(r["fact_id"], r["framing"], r["model_short"])] = r["label"]
    t0_ph4 = defaultdict(list)
    for r in src4:
        if float(r["temperature"]) == 0.0:
            t0_ph4[(r["fact_id"], r["framing"], r["model_short"])].append(r["label"])

    sig = defaultdict(dict)
    for key, lbl in t0_ph3.items():
        g, f, m = key
        sig[(g, m)][f] = lbl
    n_t0_ph4_extra = 0
    for key, lbls in t0_ph4.items():
        g, f, m = key
        if (g, f, m) in t0_ph3:
            continue
        n_t0_ph4_extra += 1
        sig[(g, m)][f] = lbls[0]

    n_units_5 = sum(1 for u in sig.values() if len(u) == 5)
    n_identical5 = sum(1 for u in sig.values() if len(u) == 5 and len(set(u.values())) == 1)
    distinct_counts = Counter(len(set(u.values())) for u in sig.values() if len(u) == 5)

    t0_framing = {}
    for f in FRAMINGS:
        rows = [l for (g, ff, m), l in t0_ph3.items() if ff == f]
        rows += [l for (g, ff, m), lbls in t0_ph4.items() if ff == f for l in lbls]
        dist, n = lab_dist([{"label": x} for x in rows])
        t0_framing[f] = {"cells": n, "S1_pct": dist["S1"]["rate"], "C_pct": dist["C"]["rate"]}

    mcnemar = {}
    for f in FRAMINGS:
        if f == "neutral":
            continue
        b = c = 0
        for (g, m), u in sig.items():
            nl, fl = u.get("neutral"), u.get(f)
            if nl is None or fl is None:
                continue
            s1n, s1f = (nl == "S1"), (fl == "S1")
            if s1n and not s1f:
                b += 1
            elif not s1n and s1f:
                c += 1
        pv, nn = two_sided_p(b, c)
        n_units = sum(1 for u in sig.values() if "neutral" in u and f in u)
        mcnemar[f] = {"neutral_S1_only": b, "framed_S1_only": c, "n_units": n_units,
                      "exact_two_sided_p": pv}
    J["t0_analysis"] = {
        "phase3_t0_cells": len(t0_ph3),
        "phase4_t0_extra_cells": n_t0_ph4_extra,
        "signature_units": len(sig),
        "signature_units_with_all5_framings": n_units_5,
        "signature_units_identical_label_all5": n_identical5,
        "distinct_labels_per_unit_distro": dict(sorted(distinct_counts.items())),
        "t0_framing_S1_pct": t0_framing,
        "mcnemar_S1_neutral_vs_framing": mcnemar,
    }

    wilcoxon = {}
    for f in FRAMINGS:
        if f == "neutral":
            continue
        xs, ys = [], []
        for (g, m), u in sig.items():
            nl, fl = u.get("neutral"), u.get(f)
            if nl is None or fl is None:
                continue
            xs.append(1.0 if nl == "S1" else 0.0)
            ys.append(1.0 if fl == "S1" else 0.0)
        if len(xs) > 2:
            try:
                w, p = sps.wilcoxon(xs, ys, zero_method="wilcox")
                wilcoxon[f] = {"n": len(xs), "mean_neutral_S1_pct": 100.0 * statistics.mean(xs),
                               "mean_framed_S1_pct": 100.0 * statistics.mean(ys),
                               "delta_pp": 100.0 * (statistics.mean(ys) - statistics.mean(xs)),
                               "W": float(w), "p": fmt_p(p)}
            except ValueError:
                wilcoxon[f] = {"n": len(xs), "note": "all sampled differences are zero"}
    J["t0_analysis"]["wilcoxon_paired_T0_neutral_vs_framing"] = wilcoxon

    # stochastic draws (phase-3, T>0): label multiset per (fact, framing, model)
    cells_draws = defaultdict(list)
    for r in src3_tg:
        cells_draws[(r["fact_id"], r["framing"], r["model_short"])].append(r["label"])
    n_cells = len(cells_draws)
    n_cells_mixed = sum(1 for v in cells_draws.values() if len(set(v)) > 1)
    cell_s1 = []
    cell_s1_flip = 0
    for v in cells_draws.values():
        s1 = sum(1 for x in v if x == "S1")
        cell_s1.append(s1 / len(v))
        if 0 < s1 < len(v):
            cell_s1_flip += 1
    J["stochastic_analysis"] = {
        "n_cells_Tgt_draws": n_cells,
        "cells_with_mixed_draw_labels_pct": round(100.0 * n_cells_mixed / n_cells, 2),
        "cells_with_both_S1_and_nonS1_draws_pct": round(100.0 * cell_s1_flip / n_cells, 2),
        "distinct_labels_per_cell_distro": dict(sorted(Counter(len(set(v)) for v in cells_draws.values()).items())),
        "cell_mean_S1_rate_pct": round(100.0 * statistics.mean(cell_s1), 2),
        "cell_S1_rate_sd_pct": round(100.0 * statistics.pstdev(cell_s1), 2),
    }

    # 7. confounders ------------------------------------------------------------
    cat_stats = {}
    cats = sorted({str(r["category"]) for r in pool_rows if r["category"]} - {"None"})
    for cat in cats:
        rows = [r for r in pool_rows if r["category"] == cat]
        dist, n = lab_dist(rows)
        cat_stats[cat] = {"pool_rows": n, "S1_pct": round(dist["S1"]["rate"], 1),
                          "C_pct": round(dist["C"]["rate"], 1), "R_pct": round(dist["R"]["rate"], 1)}
    len_by_label = {}
    for lbl in LABELS:
        lens = [len(r["completion"]) for r in pool_rows if r["label"] == lbl]
        len_by_label[lbl] = {"n": len(lens), "mean": round(statistics.mean(lens), 1),
                             "median": float(statistics.median(lens))} if lens else {"n": 0}
    phrase_by_label = {}
    for lbl in LABELS:
        rows = [r for r in pool_rows if r["label"] == lbl]
        if not rows:
            continue
        n = len(rows)
        a = sum(1 for r in rows if any(p in r["completion"].lower() for p in AGREE_PHRASES))
        rr = sum(1 for r in rows if any(p in r["completion"].lower() for p in REFUSE_PHRASES))
        phrase_by_label[lbl] = {"agree_phrase_pct": round(rate(a, n), 1),
                                "refuse_phrase_pct": round(rate(rr, n), 1)}
    authority = [r for r in pool_rows if r["framing"] == "authority"]
    surface = {
        "authority_completions_echoing_nature_study_2024_pct": round(rate(
            sum(1 for r in authority
                if "nature study" in r["completion"].lower() or "2024" in r["completion"]), len(authority)), 1),
        "completions_echoing_right_qmark_pct": round(rate(
            sum(1 for r in pool_rows if "right?" in r["completion"]), pool_labeled), 1),
        "completions_echoing_i_believe_pct": round(rate(
            sum(1 for r in pool_rows if "i believe" in r["completion"].lower()), pool_labeled), 1),
        "cross_group_shared_completions": 7,
    }
    J["confounders"] = {
        "category_label_rates": cat_stats,
        "completion_len_by_label": len_by_label,
        "phrase_by_label_approximate_lexical": phrase_by_label,
        "surface_artifacts": surface,
    }

    # 8. dataset size reality ----------------------------------------------------
    J["dataset_size_reality"] = {
        "n_facts": 50, "n_framings": 5, "n_models": 8,
        "pool_total_pairs": len(pool), "pool_labeled_rows": pool_labeled,
        "effective_units_fact_x_model": 400,
        "effective_units_fact_only": 50,
        "example_splits_at_fact_level": {"train": 30, "val": 10, "test": 10},
        "note": "Rows are nested within (fact, model) units; per-row i.i.d. assumptions do not hold.",
    }
    return J, {"pool_rows": pool_rows, "sig": dict(sig), "model_framing": model_framing,
               "model_framing_pool": model_framing_pool, "t0_framing": t0_framing,
               "wilcoxon": wilcoxon, "stochastic": J["stochastic_analysis"],
               "facts_stats": J["facts_stats"]}


if __name__ == "__main__":
    OUT = DATASET / "schis02_label_analysis.json"
    J, _ = compute()
    OUT.write_text(json.dumps(J, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    print(f"Wrote: {OUT}")
    print("pool labeled rows:", J["_meta"]["pool_labeled_rows"])
    print("source phase3 records:", J["_meta"]["source_phase3_records"])
    print("source phase4 records:", J["_meta"]["source_phase4_records"])