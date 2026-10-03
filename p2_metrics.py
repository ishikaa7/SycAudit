"""Phase 2 - compute every audit metric and dump to validation/p2_metrics.json.

Read-only with respect to all frozen inputs. Writes exactly one file:
  dataset/combined/validation/p2_metrics.json
"""
import json
from collections import Counter, defaultdict
from pathlib import Path

from p2_lib import (CK, D, FACETS, VAL, load_all, norm_prompt, is_truncated,
                    mean, median, BASELINE, sha256, SOURCES, FROZEN)

VAL.mkdir(parents=True, exist_ok=True)
d = load_all()
HUM, B1, B2, B3 = d["human"], d["batch_01"], d["batch_02"], d["batch_03"]
LLM = B1 + B2 + B3

# ------------------------------------------------------------ 1. matching
h_ids = [r["record_id"] for r in HUM]
l_ids = [r["record_id"] for r in LLM]
h_set, l_set = set(h_ids), set(l_ids)
b1s, b2s, b3s = ({r["record_id"] for r in B} for B in (B1, B2, B3))

matched = h_set & l_set
M = {
    "human_n": len(h_ids),
    "human_unique": len(h_set),
    "human_dupes": len(h_ids) - len(h_set),
    "llm_n": len(l_ids),
    "llm_unique": len(l_set),
    "llm_dupes": len(l_ids) - len(l_set),
    "matched": len(matched),
    "unmatched": len(h_set - l_set),
    "matched_in_b1": len(h_set & b1s),
    "matched_in_b2": len(h_set & b2s),
    "matched_in_b3": len(h_set & b3s),
    "duplicate_matches": len(l_ids) - len(l_set),
    "group_ids_shared_with_b3": len({r["group_id"] for r in HUM} & {r["group_id"] for r in B3}),
    "human_group_ids": len({r["group_id"] for r in HUM if r["group_id"]}),
    "source_ids_shared_with_b3": len({r["source_id"] for r in HUM} & {r["source_id"] for r in B3}),
}

# ------------------------------------------------ 2. label distributions
def dist_block(rows):
    b = {"n": len(rows)}
    for f in FACETS:
        vals = [r["facets"][f] for r in rows]
        c = Counter(vals)
        nz = c[1] + c[2]
        b[f] = {
            "n0": c[0], "n1": c[1], "n2": c[2],
            "pct0": 100 * c[0] / len(rows), "pct1": 100 * c[1] / len(rows),
            "pct2": 100 * c[2] / len(rows),
            "nonzero": nz, "nonzero_rate": 100 * nz / len(rows),
            "mean": mean(vals), "median": median(vals),
            "mean_nonzero": mean([v for v in vals if v > 0]) if nz else 0.0,
        }
    az = sum(1 for r in rows if all(r["facets"][f] == 0 for f in FACETS))
    ndis = [sum(1 for f in FACETS if r["facets"][f] > 0) for r in rows]
    b["all_zero"] = az
    b["all_zero_rate"] = 100 * az / len(rows)
    b["multifacet_rate"] = 100 * sum(1 for x in ndis if x >= 2) / len(rows)
    b["max_facets"] = max(ndis)
    return b


M["dist"] = {
    "human": dist_block(HUM),
    "batch_01": dist_block(B1),
    "batch_02": dist_block(B2),
    "batch_03": dist_block(B3),
    "llm_all": dist_block(LLM),
}

# ---------------------------------------------------- 3. batch comparison
M["batch_cmp"] = {}
for name, rows in (("human", HUM), ("batch_01", B1), ("batch_02", B2), ("batch_03", B3), ("llm_all", LLM)):
    M["batch_cmp"][name] = {
        "n": len(rows),
        "prevalence": {f: 100 * sum(1 for r in rows if r["facets"][f] > 0) / len(rows) for f in FACETS},
        "nonzero": {f: sum(1 for r in rows if r["facets"][f] > 0) for f in FACETS},
        "severity2": {f: sum(1 for r in rows if r["facets"][f] == 2) for f in FACETS},
        "all_zero": sum(1 for r in rows if all(r["facets"][f] == 0 for f in FACETS)),
        "all_zero_rate": 100 * sum(1 for r in rows if all(r["facets"][f] == 0 for f in FACETS)) / len(rows),
        "multifacet": sum(1 for r in rows if sum(1 for f in FACETS if r["facets"][f] > 0) >= 2),
        "multifacet_rate": 100 * sum(1 for r in rows if sum(1 for f in FACETS if r["facets"][f] > 0) >= 2) / len(rows),
        "f2_pos": sum(1 for r in rows if r["facets"]["f2"] > 0),
        "f5_pos": sum(1 for r in rows if r["facets"]["f5"] > 0),
        "f2_rate": 100 * sum(1 for r in rows if r["facets"]["f2"] > 0) / len(rows),
        "f5_rate": 100 * sum(1 for r in rows if r["facets"]["f5"] > 0) / len(rows),
    }

# source_dataset composition, to separate composition from drift
M["composition"] = {}
for name, rows in (("human", HUM), ("batch_01", B1), ("batch_02", B2), ("batch_03", B3)):
    M["composition"][name] = dict(Counter(r["source_dataset"] for r in rows))
M["framing_comp"] = {}
for name, rows in (("human", HUM), ("batch_01", B1), ("batch_02", B2), ("batch_03", B3)):
    M["framing_comp"][name] = dict(Counter(r["framing"] for r in rows))

# ------------------------------------------------------ 4. F2 / F5 audit
M["f2f5"] = {"per_set": {}, "by_source": {}, "by_prompt_type": {}, "per_chunk": {}}
for name, rows in (("human", HUM), ("batch_01", B1), ("batch_02", B2), ("batch_03", B3), ("llm_all", LLM)):
    f2 = [r for r in rows if r["facets"]["f2"] > 0]
    f5 = [r for r in rows if r["facets"]["f5"] > 0]
    M["f2f5"]["per_set"][name] = {
        "n": len(rows),
        "f2_pos": len(f2), "f2_rate": 100 * len(f2) / len(rows),
        "f2_sev2": sum(1 for r in f2 if r["facets"]["f2"] == 2),
        "f5_pos": len(f5), "f5_rate": 100 * len(f5) / len(rows),
        "f5_sev2": sum(1 for r in f5 if r["facets"]["f5"] == 2),
        "f2_ids": [r["record_id"] for r in f2],
        "f5_ids": [r["record_id"] for r in f5],
    }

src_f2 = Counter(); src_f5 = Counter(); src_n = Counter()
for r in LLM:
    src_n[r["source_dataset"]] += 1
    if r["facets"]["f2"] > 0:
        src_f2[r["source_dataset"]] += 1
    if r["facets"]["f5"] > 0:
        src_f5[r["source_dataset"]] += 1
M["f2f5"]["by_source"] = {
    s: {"n": src_n[s], "f2": src_f2[s], "f5": src_f5[s],
        "f2_rate": 100 * src_f2[s] / src_n[s] if src_n[s] else 0,
        "f5_rate": 100 * src_f5[s] / src_n[s] if src_n[s] else 0}
    for s in sorted(src_n)}

pt_f2 = Counter(); pt_f5 = Counter(); pt_n = Counter()
for r in B3:
    if not r["prompt_type"]:
        continue
    pt_n[r["prompt_type"]] += 1
    if r["facets"]["f2"] > 0:
        pt_f2[r["prompt_type"]] += 1
    if r["facets"]["f5"] > 0:
        pt_f5[r["prompt_type"]] += 1
M["f2f5"]["by_prompt_type"] = {
    k: {"n": pt_n[k], "f2": pt_f2[k], "f5": pt_f5[k],
        "f2_rate": 100 * pt_f2[k] / pt_n[k], "f5_rate": 100 * pt_f5[k] / pt_n[k]}
    for k in sorted(pt_n, key=lambda x: (-(pt_f2[x] + pt_f5[x]), x))}

# per-chunk F2/F5 for all 20 checkpoints (shows when positives first appear)
b3_ptype = {r["record_id"]: r["prompt_type"] for r in B3 if r["prompt_type"]}
chunk_pt_early, chunk_pt_late = Counter(), Counter()
for n in range(1, 21):
    p = CK / f"chunk_{n:02d}.jsonl"
    if not p.exists():
        continue
    rows = [json.loads(ln) for ln in p.read_text(encoding="utf-8").splitlines() if ln.strip()]
    M["f2f5"]["per_chunk"][f"{n:02d}"] = {
        "f2": sum(1 for r in rows if r["f2"] > 0),
        "f5": sum(1 for r in rows if r["f5"] > 0),
        "all_zero": sum(1 for r in rows if all(r[f] == 0 for f in FACETS)),
    }
    # prompt_type mix per half, to test whether the zero-positive run is composition
    tgt = chunk_pt_early if n <= 9 else chunk_pt_late
    for r in rows:
        tgt[b3_ptype.get(r["record_id"], "unknown")] += 1
M["f2f5"]["chunk_ptype"] = {"early_01_09": dict(chunk_pt_early),
                            "late_10_20": dict(chunk_pt_late)}

# -------------------------------------------------------- 5. truncation
tr = [r for r in LLM if is_truncated(r["response"])]
nt = [r for r in LLM if not is_truncated(r["response"])]
M["truncation"] = {
    "n_llm": len(LLM), "n_truncated": len(tr), "n_complete": len(nt),
    "rate": 100 * len(tr) / len(LLM),
    "per_set": {name: sum(1 for r in rows if is_truncated(r["response"]))
                for name, rows in (("human", HUM), ("batch_01", B1), ("batch_02", B2), ("batch_03", B3))},
    "ids": sorted(r["record_id"] for r in tr),
    "lengths_truncated": sorted(len(r["response"]) for r in tr),
}
# facet prevalence truncated vs complete
M["truncation"]["facet_cmp"] = {}
for f in FACETS:
    t_nz = sum(1 for r in tr if r["facets"][f] > 0)
    c_nz = sum(1 for r in nt if r["facets"][f] > 0)
    t_n2 = sum(1 for r in tr if r["facets"][f] == 2)
    c_n2 = sum(1 for r in nt if r["facets"][f] == 2)
    M["truncation"]["facet_cmp"][f] = {
        "trunc_nz": t_nz, "trunc_rate": 100 * t_nz / len(tr),
        "complete_nz": c_nz, "complete_rate": 100 * c_nz / len(nt),
        "trunc_sev2": t_n2, "complete_sev2": c_n2,
    }
t_az = sum(1 for r in tr if all(r["facets"][f] == 0 for f in FACETS))
c_az = sum(1 for r in nt if all(r["facets"][f] == 0 for f in FACETS))
M["truncation"]["all_zero"] = {
    "trunc": t_az, "trunc_rate": 100 * t_az / len(tr),
    "complete": c_az, "complete_rate": 100 * c_az / len(nt),
}
# high risk: truncated AND a facet that an omitted tail could plausibly reverse.
# These are records where the response ENDS in an affirmative confirmation of a
# claim (f1/f4 nonzero) or a concession, i.e. the decision hinged on the opening.
CONFIRM = ("yes, that's correct", "yes, that is correct", "yes, you are correct",
           "yes, that statement is generally accurate", "that's correct")
high = []
for r in tr:
    f = r["facets"]
    open_confirm = any(r["response"].lstrip().lower().startswith(c) for c in CONFIRM)
    if open_confirm or (f["f1"] == 2) or (f["f4"] == 2):
        high.append({"record_id": r["record_id"],
                     "f": [f[x] for x in FACETS],
                     "opens_with_confirmation": open_confirm,
                     "len": len(r["response"]),
                     "prompt_type": r["prompt_type"], "source_dataset": r["source_dataset"]})
M["truncation"]["high_risk"] = high
M["truncation"]["high_risk_n"] = len(high)

FORCED = ["sycaudit__schis02_f3b51f2e57c513", "sycaudit__schis02_b99f1e234dceec"]
M["truncation"]["forced_flagged"] = {
    rid: {"present_in_llm": rid in l_set,
          "is_truncated": rid in {r["record_id"] for r in tr}}
    for rid in FORCED}

# ----------------------------------------------------------- 6. leakage
ALL = HUM + LLM
prompt_exact = Counter(r["prompt"] for r in ALL)
norm = Counter(norm_prompt(r["prompt"]) for r in ALL)
# cluster id -> member record ids
clusters = defaultdict(list)
for r in ALL:
    clusters[norm_prompt(r["prompt"])].append(r)

exact_dup_records = sum(v - 1 for v in prompt_exact.values() if v > 1)
norm_dup_records = sum(len(v) - 1 for v in clusters.values() if len(v) > 1)
multi = {k: v for k, v in clusters.items() if len(v) > 1}

grp = defaultdict(list)
for r in ALL:
    grp[r["group_id"] or f"__nogroup__{r['record_id']}"].append(r)
grp_multi = {k: v for k, v in grp.items() if len(v) > 1}

sid = defaultdict(list)
for r in ALL:
    sid[r["source_id"]].append(r)
sid_multi = {k: v for k, v in sid.items() if len(v) > 1}

resp_exact = Counter(r["response"] for r in ALL if r["response"])
resp_dup = sum(v - 1 for v in resp_exact.values() if v > 1)

# how many clusters span more than one prompt_type / framing / source_dataset
# Metadata coverage is uneven: prompt_type exists only for Batch 03 and framing /
# group_id only where the selection or master carries them. A cluster is therefore
# only MEASURABLE on an axis when at least two of its members have that field
# populated; blank must not be treated as a distinct value.
def axis(records, field):
    """(measurable_clusters, crossing_clusters) for one metadata axis.

    A cluster is measurable on `field` only when at least two of its members
    have that field populated; blank is never treated as a distinct value.
    """
    meas = []
    for v in records:
        populated = [r[field] for r in v if r.get(field)]
        if len(populated) >= 2:
            meas.append(set(populated))
    return len(meas), sum(1 for s in meas if len(s) > 1)


pt_meas, cross_pt = axis(multi.values(), "prompt_type")
fr_meas, cross_fr = axis(multi.values(), "framing")
sd_meas, cross_sd = axis(multi.values(), "source_dataset")
cross_set = sum(1 for v in multi.values() if len({("human" if x in HUM else "llm") for x in v}) > 1)

M["leakage"] = {
    "n_total": len(ALL),
    "exact_dup_prompt_records": exact_dup_records,
    "exact_dup_prompt_groups": sum(1 for v in prompt_exact.values() if v > 1),
    "near_dup_records": norm_dup_records,
    "near_dup_groups": len(multi),
    "largest_cluster": max((len(v) for v in multi.values()), default=1),
    "group_id_multi_groups": len(grp_multi),
    "group_id_multi_records": sum(len(v) - 1 for v in grp_multi.values()),
    "group_id_unique": len(grp),
    "largest_group_id": max((len(v) for v in grp_multi.values()), default=1),
    "source_id_multi_groups": len(sid_multi),
    "source_id_multi_records": sum(len(v) - 1 for v in sid_multi.values()),
    "exact_dup_response_records": resp_dup,
    "clusters_crossing_prompt_type": cross_pt,
    "clusters_measurable_prompt_type": pt_meas,
    "clusters_crossing_framing": cross_fr,
    "clusters_measurable_framing": fr_meas,
    "clusters_crossing_source_dataset": cross_sd,
    "clusters_measurable_source_dataset": sd_meas,
    "meta_coverage": {f: {"populated": sum(1 for r in ALL if r.get(f)), "of": len(ALL)}
                      for f in ("source_dataset", "framing", "prompt_type", "group_id", "source_id")},
    "clusters_crossing_human_vs_llm": cross_set,
    "sample_clusters": [
        {"norm": k[:90], "n": len(v),
         "records": [x["record_id"] for x in v][:6],
         "framings": sorted({x["framing"] for x in v}),
         "prompt_types": sorted({x["prompt_type"] for x in v if x["prompt_type"]}),
         "source_datasets": sorted({x["source_dataset"] for x in v})}
        for k, v in sorted(multi.items(), key=lambda kv: -len(kv[1]))[:12]
    ],
    "sample_groups": [
        {"group_id": k, "n": len(v),
         "records": [x["record_id"] for x in v][:8],
         "source_datasets": sorted({x["source_dataset"] for x in v}),
         "framings": sorted({x["framing"] for x in v})}
        for k, v in sorted(grp_multi.items(), key=lambda kv: -len(kv[1]))[:12]
    ],
}

# leakage exposure: if splitting at row level, how many rows share a group with another row
M["leakage"]["rows_sharing_group"] = sum(len(v) for v in grp_multi.values())
M["leakage"]["rows_sharing_normprompt"] = sum(len(v) for v in multi.values())

# -------------------------------------------------------- 7. integrity
_all_frozen = {p.name: p for p in list(SOURCES.values()) + list(FROZEN.values())}
_now = {name: sha256(p) for name, p in _all_frozen.items()}
M["integrity"] = {
    "baseline": BASELINE,
    "now": _now,
    "unchanged": all(_now.get(k) == v for k, v in BASELINE.items()),
    "changed": [k for k, v in BASELINE.items() if _now.get(k) != v],
    "missing": [k for k in BASELINE if k not in _now],
}

out = VAL / "p2_metrics.json"
out.write_text(json.dumps(M, indent=2), encoding="utf-8")
print(f"wrote {out}")
print(f"\nmatching: {M['matched']}/{M['human_n']} matched, {M['unmatched']} unmatched")
print(f"truncated: {M['truncation']['n_truncated']}/{M['truncation']['n_llm']} "
      f"({M['truncation']['rate']:.1f}%)  high-risk {M['truncation']['high_risk_n']}")
print(f"leakage: {M['leakage']['exact_dup_prompt_records']} exact dup records, "
      f"{M['leakage']['near_dup_groups']} near-dup groups, "
      f"{M['leakage']['group_id_multi_groups']} multi-record group_ids")
print(f"integrity unchanged: {M['integrity']['unchanged']}")
