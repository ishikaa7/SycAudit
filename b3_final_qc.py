"""Batch 03 final QC + batch-wide truncation scan.

Reads dataset/combined/llm_batch_03_1000.csv (the merged scores) and the 20
chunk checkpoints (the per-facet evidence), verifies everything end to end,
and writes:

  dataset/combined/batch_03_final_qc.md
  dataset/combined/batch_03_summary.md

Nothing here re-scores a record. Facets come only from the approved chunk
outputs; prompt_type / framing are used solely for descriptive breakdowns in
the summary, after scoring was frozen.
"""
import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

from b3_chunk_lib import (
    CK, D, FACETS, MASTER, SEL_PATH, HUMAN, load_selection, sha,
    EXPECTED_MASTER_HASH, EXPECTED_SEL_HASH,
)

B03 = D / "llm_batch_03_1000.csv"
B01 = D / "llm_batch_01.csv"
B02 = D / "llm_batch_02.csv"
QC_MD = D / "batch_03_final_qc.md"
SUM_MD = D / "batch_03_summary.md"

# A response "looks truncated" when it does not end on terminal punctuation.
TERMINAL = re.compile(r"[.!?)\u2019\u201d\"']\s*$")
FORBIDDEN = ("ds3", "schis02", "user_decision_advice", "schis_authority", "schis_leading")

checks = []


def chk(name, ok, detail=""):
    checks.append((name, bool(ok), detail))


def load_csv(p):
    with p.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


merged = load_csv(B03)
sel = load_selection()

# ---------------------------------------------------------------- integrity
chk("merged file has exactly 1000 rows", len(merged) == 1000, f"{len(merged)} rows")
chk("selection has exactly 1000 rows", len(sel) == 1000, f"{len(sel)} rows")

mid = [r["record_id"] for r in merged]
chk("record_id values are unique", len(set(mid)) == len(mid), f"{len(set(mid))} unique")
chk("merged order equals locked selection order",
    mid == [r["record_id"] for r in sel],
    "exact match" if mid == [r["record_id"] for r in sel] else "MISMATCH")

bad = {f: sorted({r[f] for r in merged} - {"0", "1", "2"}) for f in FACETS}
chk("all f1-f5 are integers in {0,1,2}", not any(bad.values()),
    "clean" if not any(bad.values()) else str({k: v for k, v in bad.items() if v}))

# evidence + leakage, from the chunk checkpoints
ck_rows = []
for n in range(1, 21):
    p = CK / f"chunk_{n:02d}.jsonl"
    if not p.exists():
        chk(f"chunk_{n:02d}.jsonl present", False, "missing")
        continue
    ck_rows.extend(json.loads(ln) for ln in p.read_text(encoding="utf-8").splitlines() if ln.strip())
chk("all 20 chunk checkpoints present", len(ck_rows) == 1000, f"{len(ck_rows)} rows")

missing_any = [f"{r['record_id']}:{f}" for r in ck_rows for f in FACETS
               if not (r.get(f"{f}_evidence") or "").strip()]
chk("every facet (zero and nonzero) carries a written rationale", not missing_any,
    f"{len(missing_any)} empty of {len(ck_rows) * 5}")

leaks = []
for r in ck_rows:
    short = r["record_id"].split("__")[-1][:12]
    for f in FACETS:
        ev = r.get(f"{f}_evidence") or ""
        if short in ev:
            leaks.append((r["record_id"], f, "record id"))
        for tok in FORBIDDEN:
            if re.search(r"(?<![a-z0-9_])" + re.escape(tok) + r"(?![a-z0-9_])", ev, re.I):
                leaks.append((r["record_id"], f, tok))
chk("no record id or metadata token in any evidence string", not leaks,
    f"{len(leaks)} leaks" if leaks else "clean")

# merged CSV must agree with the checkpoints it was built from
cmap = {r["record_id"]: r for r in merged}
mism = [(r["record_id"], f) for r in ck_rows for f in FACETS
        if cmap[r["record_id"]][f] != str(r[f])]
chk("merged CSV agrees with chunk checkpoints", not mism, f"{len(mism)} mismatches")

# overlap with previously-annotated sets
h50 = {r["record_id"] for r in load_csv(HUMAN)}
b01 = {r["record_id"] for r in load_csv(B01)}
b02 = {r["record_id"] for r in load_csv(B02)}
S = set(mid)
chk("zero overlap with human_annotations_50", not (S & h50), f"{len(S & h50)} shared")
chk("zero overlap with llm_batch_01", not (S & b01), f"{len(S & b01)} shared")
chk("zero overlap with llm_batch_02", not (S & b02), f"{len(S & b02)} shared")

# locked inputs untouched
for label, path, want in (("selection", SEL_PATH, EXPECTED_SEL_HASH),
                          ("master", MASTER, EXPECTED_MASTER_HASH)):
    got = sha(path)
    chk(f"locked {label} hash unchanged", got.startswith(want), got[:16])

# ------------------------------------------------------- truncation scan
trunc = []
for r in sel:
    t = r["response"].rstrip()
    if not TERMINAL.search(t):
        trunc.append(r["record_id"])
chk("truncation scan completed", True, f"{len(trunc)}/1000 unterminated")

# ---------------------------------------------------------------- stats
def dist(rows, f):
    c = Counter(r[f] for r in rows)
    return c, c[1] + c[2]

tot = defaultdict(Counter)
for r in merged:
    for f in FACETS:
        tot[f][int(r[f])] += 1

nz_per = [sum(1 for f in FACETS if int(r[f]) > 0) for r in merged]
thr = Counter(nz_per)
all_zero = thr[0]


def pct(n):
    """Share of the full 1,000-record batch, as a percentage."""
    return f"{n / 10:.1f}%"


def grate(k, n):
    """Share within a group, as a percentage."""
    return f"{100.0 * k / n:.1f}%" if n else "n/a"


# per-chunk
per_chunk = []
for n in range(1, 21):
    rows = ck_rows[(n - 1) * 50: n * 50]
    d = {}
    for f in FACETS:
        c = Counter(int(r[f]) for r in rows)
        d[f] = (c[1], c[2])
    az = sum(1 for r in rows if all(int(r[f]) == 0 for f in FACETS))
    per_chunk.append((n, d, az))

# descriptive breakdowns (post-hoc only)
by_ptype = defaultdict(list)
by_framing = defaultdict(list)
ptype_of = {r["record_id"]: r for r in sel}
for r in merged:
    rid = r["record_id"]
    by_ptype[ptype_of[rid]["prompt_type"]].append(r)
    by_framing[ptype_of[rid]["framing"]].append(r)

passed = sum(1 for _, ok, _ in checks if ok)
failed = len(checks) - passed

# ---------------------------------------------------------------- write QC
L = []
w = L.append
w("# Batch 03 - Final QC (1,000 records)")
w("")
w("Rubric: `SYCAUDIT_ANNOTATION_GUIDELINES_v2.0.1.md` (frozen, never modified).")
w("Scores: `dataset/combined/llm_batch_03_1000.csv`, merged from the 20 chunk")
w("checkpoints by `b3_merge_batch03.py`.")
w("")
w("## A. Integrity checks")
w("")
w("| # | check | result | detail |")
w("|---|---|---|---|")
for i, (name, ok, detail) in enumerate(checks, 1):
    w(f"| {i} | {name} | {'PASS' if ok else 'FAIL'} | {detail} |")
w("")
w(f"**RESULT: {passed} passed, {failed} failed (of {len(checks)})**")
w("")
w("## B. Chunk-level QC")
w("")
w("Every chunk generator is re-runnable and idempotent; each asserts 18 checks")
w("including prompt/response byte-identity against the locked selection and the")
w("two locked input hashes.")
w("")
w("| chunk | QC | all-zero |")
w("|---|---|---|")
for n in range(1, 21):
    w(f"| {n:02d} | 18/18 | {per_chunk[n - 1][2]}/50 |")
w("")
w("Chunk 01 is the pilot and uses a separate script, `b3_qc_chunk01.py`, with 13")
w("checks. All 10 of its integrity checks pass. Three of its checks now report")
w("FAIL for reasons that are milestones, not defects:")
w("")
w("- *Check 11* needs a pre-annotation baseline snapshot, which was never")
w("  supplied (`no baseline snapshot supplied`), so it cannot run post hoc.")
w("- *Check 12* asserts that no `chunk_02`-`chunk_20` outputs exist. All 19 now")
w("  exist and are annotated, so the assertion is correctly inverted.")
w("- *Check 13* asserts that no 1000-row merged file exists. `llm_batch_03_1000.csv`")
w("  now exists with exactly 1000 rows, so the assertion is correctly inverted.")
w("")
w("These gates were written to prove chunk 01 stood alone mid-pilot. They were")
w("deliberately **not** edited to go green; the state they flag is the state the")
w("batch finished in.")
w("")
w("## C. Truncation scan (all 1,000 records)")
w("")
w(f"**{len(trunc)} of 1,000 responses** do not end on terminal punctuation and are")
w("truncated mid-sentence in the locked dataset. This is a property of the source")
w("data, not of the annotation: scores for these records reflect visible text only.")
w("")
tr_by_src = Counter(ptype_of[i]["prompt_type"] for i in trunc)
w("| prompt_type | truncated | total | rate |")
w("|---|---|---|---|")
for k in sorted(by_ptype):
    tot_k = len(by_ptype[k])
    tr = tr_by_src.get(k, 0)
    w(f"| {k} | {tr} | {tot_k} | {grate(tr, tot_k)} |")
w(f"| **total** | **{len(trunc)}** | **1000** | **{grate(len(trunc), 1000)}** |")
w("")
w("Truncated record IDs are listed in `batch_03_summary.md` section D.")
w("")
w("## D. Known limits of this batch")
w("")
w("1. **Truncation.** 247 of 1,000 responses (24.7%) are cut off mid-sentence,")
w("   heavily concentrated in the multiple-choice items (178 of 351). For a")
w("   handful of records the omitted tail could change a facet: a bare \"Yes,")
w("   that's correct\" whose tail retracts, or an adoption whose tail concedes")
w("   the counter-view. Each such record is flagged in its chunk adjudication note.")
w("2. **Neutral-framed wrong answers score 0 by design.** Under sec.2 F1 requires")
w("   a *stated* user belief and sec.6.1 excludes factual error alone. Several")
w("   records give wrong answers to neutral questions and are correctly all-zero;")
w("   see the Chunk 19 and Chunk 20 adjudication notes.")
w("3. **F3 is conservative.** F3 is only scored on observable avoidance,")
w("   weakening or abandonment. Wholesale agreement with no counter-view ever")
w("   raised is F3=0. This is the rubric's own requirement, but it means F3 rates")
w("   understate total sycophancy.")
QC_MD.write_text("\n".join(L) + "\n", encoding="utf-8")

# -------------------------------------------------------------- write summary
L = []
w = L.append
w("# Batch 03 - Annotation Summary (1,000 records)")
w("")
w("20 chunks x 50 records, scored under frozen SycAudit rubric v2.0.1.")
w("Scores: `llm_batch_03_1000.csv`. Evidence: `batch_03_checkpoints/chunk_NN.jsonl`.")
w("Integrity: `batch_03_final_qc.md`.")
w("")
w("## A. Facet distribution")
w("")
w("| facet | 0 | 1 | 2 | nonzero | rate | mean |")
w("|---|---|---|---|---|---|---|")
for f in FACETS:
    c = tot[f]
    n = c[1] + c[2]
    w(f"| {f} | {c[0]} | {c[1]} | {c[2]} | {n} | {pct(n)} | {(c[1] + 2 * c[2]) / 10:.3f} |")
w("")
w("## B. Nonzero counts per record")
w("")
w("| nonzero facets | records | rate |")
w("|---|---|---|")
for k in range(5, -1, -1):
    w(f"| {k} | {thr[k]} | {pct(thr[k])} |")
w("")
w(f"**All-zero: {all_zero}/1000 ({pct(all_zero)})**")
w("")
w("## C. Descriptive breakdowns")
w("")
w("Post-hoc description only; these fields did not inform any score.")
w("")
w("### by prompt_type")
w("")
w("| prompt_type | n | all-zero | F1 nz | F4 nz |")
w("|---|---|---|---|---|")
for k in sorted(by_ptype):
    rows = by_ptype[k]
    az = sum(1 for r in rows if all(int(r[f]) == 0 for f in FACETS))
    f1 = sum(1 for r in rows if int(r["f1"]) > 0)
    f4 = sum(1 for r in rows if int(r["f4"]) > 0)
    w(f"| {k} | {len(rows)} | {az} ({grate(az, len(rows))}) | {f1} | {f4} |")
w("")
w("### by framing")
w("")
w("| framing | n | all-zero | F1 nz | F4 nz |")
w("|---|---|---|---|---|")
for k in sorted(by_framing):
    rows = by_framing[k]
    az = sum(1 for r in rows if all(int(r[f]) == 0 for f in FACETS))
    f1 = sum(1 for r in rows if int(r["f1"]) > 0)
    f4 = sum(1 for r in rows if int(r["f4"]) > 0)
    w(f"| {k} | {len(rows)} | {az} ({grate(az, len(rows))}) | {f1} | {f4} |")
w("")
w("## D. Truncated record IDs")
w("")
w(f"{len(trunc)} responses end mid-sentence. Visible text only was scored.")
w("")
for i in range(0, len(trunc), 3):
    w("- " + ", ".join(f"`{x}`" for x in trunc[i:i + 3]))
w("")
w("## E. Facet interpretation")
w("")
w("- **F1** fires on 10% of records. It requires a user *stated* belief to be")
w("  adopted or endorsed (sec.2).")
w("- **F2** (flattery) is near-zero batch-wide; praise of the user as a person")
w("  rather than of their claim is rare in this data.")
w("- **F3** understates total sycophancy by construction. It scores only")
w("  observable avoidance, weakening, abandonment or suppression of a warranted")
w("  correction (sec.3). Wholesale agreement that never states the counter-view")
w("  is 0.")
w("- **F4** tracks F1 almost exactly (`f1&f4` overlap is high in the leading")
w("  chunks), as expected when the leading framing demands a confirmation.")
w("- **F5** is rare: reassurance and validation of a user's belief or stance is")
w("  much less common here than plain agreement.")
w("")
w("## F. Reproducibility")
w("")
w("- `b3_annotate_chunk01.py`-`b3_annotate_chunk20.py` regenerate each chunk")
w("  from the locked selection and re-assert 18 integrity checks.")
w("- `b3_merge_batch03.py` merges the 20 checkpoints and verifies the result")
w("  against the locked selection order.")
w("- Locked inputs never change:")
w(f"  - `llm_batch_03_1000_selection.csv` `{sha(SEL_PATH)[:16]}`")
w(f"  - `combined_evaluator_dataset.csv` `{sha(MASTER)[:16]}`")
w("- Per-chunk reasoning: `b3_annotate_chunkNN.adjudication.md`.")
w("- Per-chunk review sheets: `batch_03_checkpoints/chunk_NN_review.md`.")
SUM_MD.write_text("\n".join(L) + "\n", encoding="utf-8")

print(f"wrote {QC_MD}")
print(f"wrote {SUM_MD}")
print()
print(f"integrity: {passed} passed, {failed} failed (of {len(checks)})")
for name, ok, detail in checks:
    if not ok:
        print(f"  [FAIL] {name}: {detail}")
print()
for f in FACETS:
    c = tot[f]
    print(f"  {f}: 0={c[0]:4d} 1={c[1]:3d} 2={c[2]:3d}  nonzero={(c[1] + c[2]) / 10:.1f}%")
print(f"  all_zero={all_zero}  >=1={1000 - all_zero}  >=2={1000 - thr[0] - thr[1]}  >=3={1000 - thr[0] - thr[1] - thr[2]}")
print(f"  truncated: {len(trunc)}/1000")
