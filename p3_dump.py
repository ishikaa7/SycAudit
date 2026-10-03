"""Phase 3 - dump human F2/F5 positives with full text for manual adjudication.

Read-only. Writes only to the rubric_adjudication output dir.
"""
import json

from p2_lib import D, FACETS, VAL, rd, SOURCES

OUT = D / "rubric_adjudication"
H = rd(SOURCES["human_50"])


def facets(r):
    return {f: int(r[f]) for f in FACETS}


rows = [{"record_id": r["record_id"], "facets": facets(r),
         "prompt": r.get("prompt", ""), "response": r.get("response", ""),
         "source_dataset": r.get("source_dataset", ""),
         "annotator": r.get("annotator", "")} for r in H]

f2 = [r for r in rows if r["facets"]["f2"] > 0]
f5 = [r for r in rows if r["facets"]["f5"] > 0]
(OUT / "_f2_dump.json").write_text(json.dumps(f2, indent=1, ensure_ascii=False), encoding="utf-8")
(OUT / "_f5_dump.json").write_text(json.dumps(f5, indent=1, ensure_ascii=False), encoding="utf-8")
print(f"F2 positives: {len(f2)}   F5 positives: {len(f5)}")
print(f"F2+F5 both:   {sum(1 for r in rows if r['facets']['f2']>0 and r['facets']['f5']>0)}")
print()
for i, r in enumerate(f2, 1):
    fs = r["facets"]
    print(f"[{i:2}] {r['record_id']:42} f2={fs['f2']} "
          f"f1={fs['f1']} f3={fs['f3']} f4={fs['f4']} f5={fs['f5']}  "
          f"resp={len(r['response'])}c")
print()
for i, r in enumerate(f5, 1):
    fs = r["facets"]
    print(f"[{i:2}] {r['record_id']:42} f5={fs['f5']} "
          f"f1={fs['f1']} f2={fs['f2']} f3={fs['f3']} f4={fs['f4']}  "
          f"resp={len(r['response'])}c")
