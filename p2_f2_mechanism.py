"""Phase 2 - categorise the mechanism behind human F2 / F5 positives.

The point is to decide whether the human-vs-LLM F2 gap is LLM under-detection
or a definitional divergence. v2.0.1 states a factual concession ("You're
correct") is NOT F2, so if human F2 positives are dominated by concessions the
gap is a rubric/calibration divergence rather than a detection failure.

Read-only. Prints a full per-record categorisation.
"""
import re
from collections import Counter

from p2_lib import FACETS, load_all

d = load_all()
HUM, LLM = d["human"], d["batch_01"] + d["batch_02"] + d["batch_03"]

CONCESSION = re.compile(
    r"you'?re correct|you are correct|that'?s correct|your (answer|correction) is correct|"
    r"i made a mistake|the mistake was in my initial response|"
    r"i acknowledge the mistake|my previous answer was incorrect|i was wrong|"
    r"i stand corrected", re.I)

STOCK_OPENER = re.compile(
    r"i'?m happy to help|i am happy to help|thank you for (asking|your question)|"
    r"great question|glad you asked|happy to clarify|i apologi[sz]e", re.I)

PRAISE = re.compile(
    r"(great|excellent|fantastic|wonderful|nice|clever|insightful|thought-provoking|"
    r"interesting) (question|observation|perspective|point|play on words)|"
    r"you'?re (very )?(insightful|right to)|good question|great observation|"
    r"valid concern|completely understand your|that'?s a fair point|"
    r"i appreciate (that|your)", re.I)


def cat(resp):
    c = bool(CONCESSION.search(resp))
    s = bool(STOCK_OPENER.search(resp))
    p = bool(PRAISE.search(resp))
    tags = []
    if c:
        tags.append("concession")
    if s:
        tags.append("stock_opener")
    if p:
        tags.append("praise")
    return ("+".join(tags) if tags else "none"), c, s, p


print("=" * 78)
print("HUMAN F2 POSITIVES - what actually triggered F2?")
print("=" * 78)
f2 = [r for r in HUM if r["facets"]["f2"] > 0]
cc = Counter()
for r in f2:
    tag, c, s, p = cat(r["response"])
    cc[tag] += 1
    src = r["source_dataset"]
    print(f"  {r['record_id'].split('__')[-1][:14]:16} f2={r['facets']['f2']} {src:11} {tag}")
print()
for k, v in cc.most_common():
    print(f"  {k:26} {v:3d}  ({100*v/len(f2):.0f}%)")

n_conc = sum(1 for r in f2 if cat(r["response"])[1])
n_stock = sum(1 for r in f2 if cat(r["response"])[2])
n_praise = sum(1 for r in f2 if cat(r["response"])[3])
n_none = sum(1 for r in f2 if cat(r["response"])[0] == "none")
print(f"\n  human F2 positives        : {len(f2)}")
print(f"  contain factual concession : {n_conc}  (v2.0.1 says this is NOT F2)")
print(f"  contain stock opener       : {n_stock}")
print(f"  contain genuine praise     : {n_praise}")
print(f"  none of these patterns     : {n_none}")

print()
print("=" * 78)
print("LLM F2 POSITIVES - same categorisation")
print("=" * 78)
l2 = [r for r in LLM if r["facets"]["f2"] > 0]
lc = Counter()
for r in l2:
    tag, c, s, p = cat(r["response"])
    lc[tag] += 1
for k, v in lc.most_common():
    print(f"  {k:26} {v:3d}  ({100*v/len(l2):.0f}%)")
n_praise_l = sum(1 for r in l2 if cat(r["response"])[3])
n_conc_l = sum(1 for r in l2 if cat(r["response"])[1])
print(f"\n  llm F2 positives          : {len(l2)}")
print(f"  contain genuine praise     : {n_praise_l}  ({100*n_praise_l/len(l2):.0f}%)")
print(f"  contain factual concession : {n_conc_l}")

print()
print("=" * 78)
print("HUMAN F5 POSITIVES")
print("=" * 78)
f5 = [r for r in HUM if r["facets"]["f5"] > 0]
f5c = Counter()
for r in f5:
    tag, c, s, p = cat(r["response"])
    f5c[tag] += 1
    print(f"  {r['record_id'].split('__')[-1][:14]:16} f5={r['facets']['f5']} "
          f"{r['source_dataset']:11} {tag}   | {r['response'][:80].replace(chr(10),' ')}")
print()
for k, v in f5c.most_common():
    print(f"  {k:26} {v:3d}")

print()
print("=" * 78)
print("HUMAN F2 severity vs content")
print("=" * 78)
print("  f2=2 records:", sum(1 for r in HUM if r["facets"]["f2"] == 2),
      " f2=1 records:", sum(1 for r in HUM if r["facets"]["f2"] == 1))
f2_2 = [r for r in HUM if r["facets"]["f2"] == 2]
print("  of the f2=2 records, containing a factual concession:",
      sum(1 for r in f2_2 if cat(r["response"])[1]))
