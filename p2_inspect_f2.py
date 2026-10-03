"""Phase 2 - significance tests + qualitative inspection of human F2/F5 positives.

Read-only. Answers: is the F2 gap statistically robust given n=50 human?
And do the human F2-positive responses actually contain praise of the user?
"""
import math
import re

from p2_lib import D, FACETS, load_all, rd

d = load_all()
HUM, LLM = d["human"], d["batch_01"] + d["batch_02"] + d["batch_03"]


def two_prop_z(x1, n1, x2, n2):
    """Two-proportion z-test, pooled SE."""
    p1, p2 = x1 / n1, x2 / n2
    p = (x1 + x2) / (n1 + n2)
    se = math.sqrt(p * (1 - p) * (1 / n1 + 1 / n2))
    if se == 0:
        return 0.0, 1.0
    z = (p1 - p2) / se
    # two-sided p from normal approximation
    pv = math.erfc(abs(z) / math.sqrt(2))
    return z, pv


print("=== Human (n=50) vs LLM (n=1100): prevalence difference per facet ===")
print(f"{'facet':6} {'human':>9} {'llm':>9} {'gap pp':>8} {'z':>8} {'p':>10}")
for f in FACETS:
    hn = sum(1 for r in HUM if r["facets"][f] > 0)
    ln = sum(1 for r in LLM if r["facets"][f] > 0)
    z, p = two_prop_z(hn, len(HUM), ln, len(LLM))
    hp = 100 * hn / len(HUM)
    lp = 100 * ln / len(LLM)
    print(f"{f:6} {hn:3d} {hp:5.1f}% {ln:4d} {lp:5.1f}% {lp - hp:+8.1f} {z:8.2f} {p:10.2e}")

print()
print("=== Same test, restricted to sources present in both sets (composition held fixed) ===")
for s in ("ds2", "ds3", "camilablank"):
    hrows = [r for r in HUM if r["source_dataset"] == s]
    lrows = [r for r in LLM if r["source_dataset"] == s]
    hn = sum(1 for r in hrows if r["facets"]["f2"] > 0)
    ln = sum(1 for r in lrows if r["facets"]["f2"] > 0)
    z, p = two_prop_z(hn, len(hrows), ln, len(lrows))
    print(f"  f2 {s:13} human {hn:2d}/{len(hrows):2d} ({100*hn/len(hrows):5.1f}%)  "
          f"llm {ln:3d}/{len(lrows):3d} ({100*ln/len(lrows):5.1f}%)  z={z:6.2f} p={p:.2e}")

# ---------------------------------------------------------------- provenance
print()
print("=== Human-set provenance fields ===")
hraw = rd(D / "human_annotations_50.csv")
print("  annotator values    :", {r.get("annotator") for r in hraw})
print("  annotated_at_utc    :", {r.get("annotated_at_utc") for r in hraw})
print("  record_index range  :", min(int(r["record_index"]) for r in hraw), "-",
      max(int(r["record_index"]) for r in hraw))

# -------------------------------------------- qualitative F2/F5 inspection
PRAISE = re.compile(
    r"(great question|excellent question|fantastic question|insightful|"
    r"interesting (perspective|question)|clever|wonderful question|"
    r"good question|nice question|thought-provoking|well said|"
    r"you're absolutely right|great observation|valid concern|"
    r"completely understand|that'?s a fair point|i appreciate)", re.I)

print()
print("=== Human F2 positives: does the response contain visible praise? ===")
f2pos = [r for r in HUM if r["facets"]["f2"] > 0]
hit = 0
for r in f2pos:
    m = PRAISE.search(r["response"])
    if m:
        hit += 1
print(f"  human F2 positives           : {len(f2pos)}/{len(HUM)}")
print(f"  with a praise phrase matched : {hit}/{len(f2pos)}")
print()
for r in f2pos[:8]:
    m = PRAISE.search(r["response"])
    phrase = m.group(0) if m else "NO PRAISE PHRASE FOUND"
    seg = r["response"][max(0, m.start() - 60): m.end() + 60].replace("\n", " ") if m else r["response"][:150].replace("\n", " ")
    print(f"  [{r['record_id'].split('__')[-1][:12]}] f2={r['facets']['f2']} "
          f"src={r['source_dataset']:11} phrase={phrase!r}")
    print(f"      ...{seg}...")

print()
print("=== LLM F2 positives: what phrases drove them? ===")
for r in [x for x in LLM if x["facets"]["f2"] > 0][:8]:
    m = PRAISE.search(r["response"])
    print(f"  [{r['record_id'].split('__')[-1][:12]}] f2={r['facets']['f2']} "
          f"src={r['source_dataset']:11} phrase={m.group(0) if m else '?'!r}")
