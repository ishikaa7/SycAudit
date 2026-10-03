"""Phase 2 - composition-controlled human-vs-LLM comparison.

The human 50 and the LLM 1,100 have different source_dataset mixes, so a raw
prevalence gap can be composition or drift. This script computes:

  1. per-facet prevalence by source_dataset for human and LLM separately
  2. LLM rates reweighted to the human 50's source composition
     (direct standardisation), so the comparison is like-for-like
  3. per-facet human vs standardised-LLM gap

Writes dataset/combined/validation/p2_controlled.json and prints a table.
No matched pairs are required, and no label is modified.
"""
import json

from p2_lib import FACETS, VAL, load_all

d = load_all()
HUM, LLM = d["human"], d["batch_01"] + d["batch_02"] + d["batch_03"]

# human composition
hsrc = {}
for r in HUM:
    hsrc[r["source_dataset"]] = hsrc.get(r["source_dataset"], 0) + 1
lsrc = {}
for r in LLM:
    lsrc[r["source_dataset"]] = lsrc.get(r["source_dataset"], 0) + 1
sources = sorted(set(hsrc) | set(lsrc))

out = {"sources": sources,
       "human_comp": hsrc, "llm_comp": lsrc,
       "by_source": {}, "standardised": {}}

print(f"{'source':14} {'n_h':>4} {'n_l':>5}", end="")
for f in FACETS:
    print(f"  {f}: h/l", end="")
print()
print("-" * 92)

for f in FACETS:
    out["standardised"][f] = {}
    for s in sources:
        hrows = [r for r in HUM if r["source_dataset"] == s]
        lrows = [r for r in LLM if r["source_dataset"] == s]
        hn = sum(1 for r in hrows if r["facets"][f] > 0)
        ln = sum(1 for r in lrows if r["facets"][f] > 0)
        hr = 100 * hn / len(hrows) if hrows else None
        lr = 100 * ln / len(lrows) if lrows else None
        out["by_source"].setdefault(s, {})[f] = {
            "human_n": len(hrows), "human_pos": hn, "human_rate": hr,
            "llm_n": len(lrows), "llm_pos": ln, "llm_rate": lr,
        }

    # Direct standardisation: weight each source's LLM rate by the HUMAN share.
    num = den = 0.0
    for s in sources:
        if not hsrc.get(s):
            continue
        lrows = [r for r in LLM if r["source_dataset"] == s]
        if not lrows:
            continue
        lr = sum(1 for r in lrows if r["facets"][f] > 0) / len(lrows)
        w = hsrc[s] / sum(hsrc.values())
        num += w * lr
        den += w
    std = 100 * num / den if den else None

    hrows = HUM
    hrate = 100 * sum(1 for r in hrows if r["facets"][f] > 0) / len(hrows)
    lraw = 100 * sum(1 for r in LLM if r["facets"][f] > 0) / len(LLM)
    out["standardised"][f] = {
        "human_rate": hrate,
        "llm_raw_rate": lraw,
        "llm_standardised_rate": std,
        "gap_raw_pp": lraw - hrate,
        "gap_standardised_pp": (std - hrate) if std is not None else None,
    }

for s in sources:
    print(f"{s:14} {hsrc.get(s,0):4d} {lsrc.get(s,0):5d}", end="")
    for f in FACETS:
        b = out["by_source"][s][f]
        h = f"{b['human_rate']:5.1f}" if b["human_rate"] is not None else "  -  "
        l = f"{b['llm_rate']:5.1f}" if b["llm_rate"] is not None else "  -  "
        print(f" {h}/{l}", end="")
    print()

print()
print(f"{'facet':6} {'human':>8} {'LLM raw':>8} {'LLM std':>8} {'gap std':>9}")
for f in FACETS:
    b = out["standardised"][f]
    std = f"{b['llm_standardised_rate']:.1f}" if b["llm_standardised_rate"] is not None else "n/a"
    gap = f"{b['gap_standardised_pp']:+.1f}" if b["gap_standardised_pp"] is not None else "n/a"
    print(f"{f:6} {b['human_rate']:7.1f}% {b['llm_raw_rate']:7.1f}% {std:>7}% {gap:>8}pp")

p = VAL / "p2_controlled.json"
p.write_text(json.dumps(out, indent=2), encoding="utf-8")
print(f"\nwrote {p}")
