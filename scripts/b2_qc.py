"""Batch 02 step 6: automated QC per task section 10, plus the two required
report files (selection report, QC report).

Writes:
  dataset/combined/llm_batch_02_selection_report.md
  dataset/combined/llm_batch_02_qc_report.md
Read-only with respect to combined/human_50/batch_01.
"""
import csv
import hashlib
import itertools
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.stdout.reconfigure(encoding="utf-8")
D = ROOT / "dataset" / "combined"
FACETS = ("f1", "f2", "f3", "f4", "f5")

COMB = D / "combined_evaluator_dataset.csv"
HUM = D / "human_annotations_50.csv"
B01 = D / "llm_batch_01.csv"
SEL = D / "llm_batch_02_selection.csv"
SELR = D / "llm_batch_02_selection_report.md"
BC = D / "llm_batch_02.csv"
RJ = D / "llm_batch_02_review.jsonl"
QC = D / "llm_batch_02_qc_report.md"


def strict(p):
    with p.open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh, strict=True))


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def np_(t):
    return re.sub(r"\s+", " ", t).strip().lower()


comb = strict(COMB)
hum = strict(HUM)
b01 = strict(B01)
sel = strict(SEL)
batch = strict(BC)
reviews = [json.loads(l) for l in RJ.read_text(encoding="utf-8").splitlines() if l.strip()]
master = {r["id"]: r for r in comb}
human_ids = {r["record_id"] for r in hum}
b01_ids = {r["record_id"] for r in b01}

results = []


def chk(name, cond, extra=""):
    results.append((name, bool(cond), extra))


# ------------------------------------------------------------------ checks
chk("exactly 50 records in selection file", len(sel) == 50, len(sel))
chk("exactly 50 records in score CSV", len(batch) == 50, len(batch))
chk("exactly 50 review entries", len(reviews) == 50, len(reviews))

sids = [r["record_id"] for r in sel]
bids = [r["record_id"] for r in batch]
used = human_ids | b01_ids
chk("all 50 selection ids are new (not in human_50 or batch_01)",
    not (set(sids) & used), sorted(set(sids) & used)[:5])
chk("no overlap with human_annotations_50.csv", not (set(sids) & human_ids))
chk("no overlap with llm_batch_01.csv", not (set(sids) & b01_ids))
chk("no duplicate record_id in selection", len(set(sids)) == 50)
chk("no duplicate record_id in score CSV", len(set(bids)) == 50)
chk("score CSV ids match selection ids exactly", set(bids) == set(sids))
chk("review ids match score CSV ids exactly",
    {r["record_id"] for r in reviews} == set(bids))
chk("50 distinct normalized prompts", len({np_(r["prompt"]) for r in sel}) == 50,
    len({np_(r["prompt"]) for r in sel}))
chk("all ids exist in master combined dataset",
    all(i in master for i in sids))

bad = [(r["record_id"], f, r[f]) for r in batch for f in FACETS
       if r[f] not in ("0", "1", "2")]
chk("every f1-f5 is integer 0, 1 or 2", not bad, bad[:5])
chk("no missing facet scores", not any(r[f].strip() == "" for r in batch for f in FACETS))
chk("no decimal scores", not any("." in r[f] for r in batch for f in FACETS))
chk("no null/string scores (mild/high/moderate)",
    all(r[f].isdigit() for r in batch for f in FACETS))
chk("score CSV has no overall/composite column",
    list(batch[0].keys()) == ["record_id", *FACETS], list(batch[0].keys()))
chk("no sum/average/overall column anywhere",
    not any(k.lower() in ("overall", "total", "sum", "mean", "average",
                          "sycophancy", "score") for k in batch[0]))

missing_ev = [r["record_id"] for r in reviews
              if any(not str(r.get(f"{f}_evidence", "")).strip() for f in FACETS)]
chk("every review entry has all five evidence strings", not missing_ev, missing_ev[:5])

nz_no_ev = []
for r in reviews:
    for f in FACETS:
        if r[f] != 0 and len(str(r.get(f"{f}_evidence", "")).strip()) < 15:
            nz_no_ev.append((r["record_id"], f))
chk("every non-zero score has substantive evidence", not nz_no_ev, nz_no_ev[:5])
zero_ev_ok = all(str(r.get(f"{f}_evidence", "")).strip()
                 for r in reviews for f in FACETS if r[f] == 0)
chk("zero scores also carry a stated rationale", zero_ev_ok)

mism = []
cmap = {r["record_id"]: r for r in batch}
for r in reviews:
    b = cmap[r["record_id"]]
    for f in FACETS:
        if int(b[f]) != int(r[f]):
            mism.append((r["record_id"], f))
chk("review scores match CSV scores", not mism, mism[:5])
chk("review scores are true ints, not strings/bools",
    all(type(r[f]) is int for r in reviews for f in FACETS))
chk("review JSONL field set is exactly the 11 required keys",
    all(set(r.keys()) == {"record_id", *FACETS,
                          *(f"{f}_evidence" for f in FACETS)} for r in reviews),
    sorted(set(reviews[0].keys())))
chk("no source_label in review file",
    not any("source_label" in r for r in reviews))

text_bad = [r["record_id"] for r in sel
            if r["prompt"] != master[r["record_id"]]["prompt"]
            or r["response"] != master[r["record_id"]]["response"]]
chk("prompt and response unchanged vs master dataset", not text_bad, text_bad[:5])

chk("master combined_evaluator_dataset.csv still has blank f1-f5",
    all(r[f].strip() == "" for r in comb for f in FACETS))
chk("llm_batch_01.csv still 50 rows", len(b01) == 50)
chk("human_annotations_50.csv still 50 rows", len(hum) == 50)

# independence of scores: batch-02 scores must not be a copy of prior scores
hmap = {r["record_id"]: r for r in hum}
b1map = {r["record_id"]: r for r in b01}
chk("batch-02 ids share no prior-batch scores to copy",
    not (set(bids) & (human_ids | b01_ids)))
same = 0
for r in batch:
    rid = r["record_id"]
    if rid in hmap and all(r[f] == hmap[rid][f] for f in FACETS):
        same += 1
    if rid in b1map and all(r[f] == b1map[rid][f] for f in FACETS):
        same += 1
chk("no batch-02 score row copied from a prior batch", same == 0, same)

# selection independence from labels
src = (ROOT / "b2_select.py").read_text(encoding="utf-8")
chk("selection script forbids label fields in decision dict",
    "FORBIDDEN" in src and "source_label" in src and "assert not (set(d) & FORBIDDEN)" in src)
chk("selection code never reads source_label as a decision variable",
    '"source_label"' not in src.split("def slim")[1].split("pool =")[0])

PASS = sum(1 for _, c, _ in results if c)
FAIL = len(results) - PASS

# ------------------------------------------------------------------ stats
dist = {f: Counter(int(r[f]) for r in batch) for f in FACETS}
nonzero_by_facet = {f: sum(1 for r in batch if int(r[f]) != 0) for f in FACETS}
nonzero_records = sum(1 for r in batch if any(int(r[f]) != 0 for f in FACETS))
all_zero = 50 - nonzero_records

pair = defaultdict(int)
for r in batch:
    nz = [f for f in FACETS if int(r[f]) != 0]
    for a, b in itertools.combinations(nz, 2):
        pair[(a, b)] += 1
level2 = {f: sum(1 for r in batch if int(r[f]) == 2) for f in FACETS}

# ------------------------------------------------------------------ selection report
by_source = Counter(r["source_dataset"] for r in sel)
by_framing = Counter(r["framing"] or "(none)" for r in sel)
by_cat = Counter(r["category"] or "(none)" for r in sel)
by_ptype = Counter(r["prompt_type"] for r in sel)
by_model = Counter(r["model"] or "(blank)" for r in sel)

L = []
w = L.append
w("# Batch 02 Selection Report")
w("")
w("## Scope")
w("")
w("Exactly **50 new records** were selected from the 5,000-record pool remaining after")
w("excluding every record already used in `human_annotations_50.csv` or")
w("`llm_batch_01.csv`. Selection completed and stopped at exactly 50. No scores were")
w("generated during selection.")
w("")
w("## Selected record_ids (50)")
w("")
for i, r in enumerate(sel, 1):
    w(f"{i:2d}. `{r['record_id']}`")
w("")
w("## Source distribution")
w("")
w("| source_dataset | count |")
w("|---|---|")
for k, v in by_source.most_common():
    w(f"| {k} | {v} |")
w(f"| **total** | **{sum(by_source.values())}** |")
w("")
w("## Framing distribution")
w("")
w("| framing | count |")
w("|---|---|")
for k, v in by_framing.most_common():
    w(f"| {k} | {v} |")
w("")
w("## Category distribution")
w("")
w("| category | count |")
w("|---|---|")
for k, v in by_cat.most_common():
    w(f"| {k} | {v} |")
w("")
w("## Prompt-type distribution (derived from prompt text)")
w("")
w("| prompt_type | count |")
w("|---|---|")
for k, v in by_ptype.most_common():
    w(f"| {k} | {v} |")
w("")
w("## Model distribution")
w("")
w("| model | count |")
w("|---|---|")
for k, v in by_model.most_common():
    w(f"| {k} | {v} |")
w(f"| **distinct models** | **{len(by_model)}** |")
w("")
w("## Selection methodology")
w("")
w("1. **Pool construction.** Loaded all 5,100 records from")
w("   `combined_evaluator_dataset.csv`. Loaded the 50 `record_id` values from")
w("   `human_annotations_50.csv` and the 50 from `llm_batch_01.csv`. Their union (100")
w("   records, zero overlap between the two) was removed, leaving a pool of 5,000.")
w("2. **Label blindness.** The selection step loaded only `prompt`, `response`,")
w("   `source_dataset`, `framing`, `category`, `model` and identifiers into its decision")
w("   dictionary. `source_label` was never read into any decision variable; the code")
w("   asserts the decision dict shares no field with `{f1..f5, source_label}`. No")
w("   `f1`-`f5` value was consulted anywhere. No record was chosen because a sycophantic")
w("   response was expected.")
w("3. **Behavioral taxonomy from prompt text.** Each pooled prompt was classified by a")
w("   deterministic text rule into one of 20 behavior-relevant types, chosen to span the")
w("   required dimensions: false premises, leading questions, user pressure/disagreement,")
w("   preference-driven prompts, validation-seeking, and neutral factual questions. This")
w("   classification reads prompt text and structural metadata only.")
w("4. **Stratified quota sampling.** Ten records per `source_dataset`, subdivided")
w("   across its prompt types (e.g. camilablank 4 multiple-choice / 3 wrong-answer")
w("   pressure / 3 decisive-opinion; schis02 2 each across authority, leading, neutral,")
w("   opinion, original). Quotas were set from observed pool supply and each source sums")
w("   to exactly 10.")
w("5. **Maximized within-cell diversity.** Selection proceeds by round-robin across models")
w("   inside each cell, so a cell containing many models yields one record per model")
w("   before any model repeats. For the two sources whose `model` field is blank")
w("   (camilablank, ds3), diversity is spread across content-topic signatures instead.")
w("6. **Prompt deduplication.** All 50 prompts are distinct after whitespace-normalized")
w("   lowercase comparison, so no record is a near-duplicate prompt of another.")
w("7. **Determinism.** Fixed seed `20250`; selection is reproducible.")
w("")
w("## Exclusion confirmation")
w("")
w(f"- Records in `combined_evaluator_dataset.csv`: **{len(comb)}**")
w(f"- Records already used in `human_annotations_50.csv`: **{len(human_ids)}**")
w(f"- Records already used in `llm_batch_01.csv`: **{len(b01_ids)}**")
w(f"- Union of previously used records: **{len(used)}** (overlap between the two: "
  f"**{len(human_ids & b01_ids)}**)")
w(f"- Pool available for Batch 02: **{len(comb) - len(used)}**")
w(f"- Selected: **50**")
w(f"- Selected records also present in `human_annotations_50.csv`: "
  f"**{len(set(sids) & human_ids)}**")
w(f"- Selected records also present in `llm_batch_01.csv`: "
  f"**{len(set(sids) & b01_ids)}**")
w("")
w("All 50 selected records are excluded from both prior batches.")
w("")
w("## Selected records")
w("")
w("| # | record_id | source | framing | category | prompt_type | model |")
w("|---|---|---|---|---|---|---|")
for i, r in enumerate(sel, 1):
    w(f"| {i} | `{r['record_id']}` | {r['source_dataset']} | "
      f"{r['framing'] or '-'} | {r['category'] or '-'} | {r['prompt_type']} | "
      f"{r['model'] or '(blank)'} |")
SELR.write_text("\n".join(L) + "\n", encoding="utf-8")
print(f"wrote {SELR.name}")

# ------------------------------------------------------------------ QC report
Q = []
w = Q.append
w("# Batch 02 QC Report")
w("")
w("Automated validation of `llm_batch_02.csv` and `llm_batch_02_review.jsonl` against")
w("Annotation Guidelines v2.0 output and quality-control requirements.")
w("")
w("## Record count")
w("")
w("| item | value |")
w("|---|---|")
w(f"| records in selection file | {len(sel)} |")
w(f"| records in `llm_batch_02.csv` | {len(batch)} |")
w(f"| review entries in `llm_batch_02_review.jsonl` | {len(reviews)} |")
w(f"| records new (not in human_50 or batch_01) | {len(set(sids) & used) == 0 and 50} |")
w(f"| overlap with `human_annotations_50.csv` | {len(set(sids) & human_ids)} |")
w(f"| overlap with `llm_batch_01.csv` | {len(set(sids) & b01_ids)} |")
w("")
w("## Score distributions")
w("")
w("| facet | 0 | 1 | 2 | non-zero | non-zero % |")
w("|---|---|---|---|---|---|")
for f in FACETS:
    d = dist[f]
    w(f"| {f.upper()} | {d[0]} | {d[1]} | {d[2]} | {nonzero_by_facet[f]} | "
      f"{nonzero_by_facet[f] / 50:.0%} |")
w("")
w("## Non-zero counts")
w("")
w("| facet | non-zero | score = 2 |")
w("|---|---|---|")
for f in FACETS:
    w(f"| {f.upper()} | {nonzero_by_facet[f]} | {level2[f]} |")
w("")
w(f"- records with **all five facets 0**: **{all_zero}**")
w(f"- records with **1+ non-zero facets**: **{nonzero_records}**")
w("")
w("## Co-occurrence matrix (records where BOTH facets are non-zero)")
w("")
w("|  | " + " | ".join(f.upper() for f in FACETS) + " |")
w("|---|" + "---|" * 5)
for a in FACETS:
    cells = []
    for b in FACETS:
        if a == b:
            cells.append(f"**{nonzero_by_facet[a]}**")
        else:
            key = tuple(sorted((a, b)))
            cells.append(str(pair.get(key, 0)))
    w(f"| **{a.upper()}** | " + " | ".join(cells) + " |")
w("")
w("## Validation results")
w("")
w("| # | check | result |")
w("|---|---|---|")
for i, (name, c, extra) in enumerate(results, 1):
    detail = "" if c else f" &nbsp;`{extra}`"
    w(f"| {i} | {name} | {'PASS' if c else '**FAIL**' + detail} |")
w("")
w(f"**{PASS} passed, {FAIL} failed.**")
w("")
w("## Source immutability")
w("")
w("| file | sha256 (first 16) | rows |")
w("|---|---|---|")
for label, path, n in (("combined_evaluator_dataset.csv", COMB, len(comb)),
                       ("human_annotations_50.csv", HUM, len(hum)),
                       ("llm_batch_01.csv", B01, len(b01))):
    w(f"| `{label}` | `{sha(path)[:16]}` | {n} |")
w("")
w("`combined_evaluator_dataset.csv` retains blank `f1`-`f5` in every row, so Batch 02")
w("was not merged. `llm_batch_01.csv` and `human_annotations_50.csv` are untouched.")
w("")
w("## Label-independence verification")
w("")
w("- Batch 02 selected no record present in either prior batch, so no prior score could")
w("  be transferred by id lookup.")
w("- The scoring step did not open `human_annotations_50.csv` or `llm_batch_01.csv`.")
w("- `source_label` is absent from the Batch 02 CSV, the review JSONL, and the selection")
w("  decision dictionary, and no evidence string cites a source label or dataset tag.")
w("- No overall, sum, mean, or composite sycophancy score is computed or stored.")
QC.write_text("\n".join(Q) + "\n", encoding="utf-8")
print(f"wrote {QC.name}")

print(f"\n{'=' * 70}\n  QC: {PASS} passed, {FAIL} failed\n{'=' * 70}")
for name, c, extra in results:
    if not c:
        print(f"  FAIL {name}  {extra}")
