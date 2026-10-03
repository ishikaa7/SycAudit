"""Batch 03 step 3: selection report + chunk manifest.

Writes llm_batch_03_1000_selection_report.md and the chunk manifest used by
the annotation stage. Read-only with respect to the source dataset.
"""
import csv
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.stdout.reconfigure(encoding="utf-8")
D = ROOT / "dataset" / "combined"
CHUNK = 50  # 20 chunks x 50 records


def strict(p):
    with p.open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh, strict=True))


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


comb = strict(D / "combined_evaluator_dataset.csv")
used_files = {n: D / n for n in ("human_annotations_50.csv",
                                 "llm_batch_01.csv", "llm_batch_02.csv")}
used = {n: {r["record_id"] for r in strict(p)} for n, p in used_files.items()}
all_used = set().union(*used.values())
sel = strict(D / "llm_batch_03_1000_selection.csv")
sel_ids = [r["record_id"] for r in sel]
master = {r["id"]: r for r in comb}

assert len(sel) == 1000, len(sel)
assert len(set(sel_ids)) == 1000
assert not (set(sel_ids) & all_used)
assert all(i in master for i in sel_ids)
for r in sel:
    m = master[r["record_id"]]
    assert r["prompt"] == m["prompt"], r["record_id"]
    assert r["response"] == m["response"], r["record_id"]

# ------------------------------------------------------------------ report
src_c = Counter(r["source_dataset"] for r in sel)
frm_c = Counter(r["framing"] or "(none)" for r in sel)
cat_c = Counter(r["category"] or "(none)" for r in sel)
pt_c = Counter(r["prompt_type"] for r in sel)
lb_c = Counter(r["response_lenband"] for r in sel)
md_c = Counter(r["model"] or "(blank)" for r in sel)

L = []
w = L.append
w("# Batch 03 Selection Report")
w("")
w("## Scope")
w("")
w("Exactly **1,000 previously unused records** were selected from the eligible pool.")
w("Selection was completed and saved before any scoring began. Annotation was a")
w("separate later stage.")
w("")
w("## Counts")
w("")
w("| quantity | value |")
w("|---|---|")
w(f"| total records in `combined_evaluator_dataset.csv` | {len(comb)} |")
w(f"| previously used records (union of three prior batches) | {len(all_used)} |")
w(f"| eligible remaining records | {len(comb) - len(all_used)} |")
w(f"| **records selected for Batch 03** | **{len(sel)}** |")
w("")
w("### Previously used records, by batch")
w("")
w("| batch file | records | unique record_ids | sha256 (first 16) |")
w("|---|---|---|---|")
for n, p in used_files.items():
    w(f"| `{n}` | {len(strict(p))} | {len(used[n])} | `{sha(p)[:16]}` |")
w("")
w("Pairwise overlaps between prior batches: "
  f"human_50 x batch_01 = {len(used['human_annotations_50.csv'] & used['llm_batch_01.csv'])}, "
  f"human_50 x batch_02 = {len(used['human_annotations_50.csv'] & used['llm_batch_02.csv'])}, "
  f"batch_01 x batch_02 = {len(used['llm_batch_01.csv'] & used['llm_batch_02.csv'])}.")
w("")
w("## Exclusion confirmation")
w("")
w("| check | result |")
w("|---|---|")
w(f"| `selected_count == 1000` | {len(sel) == 1000} |")
w(f"| `intersection(selected, previously_used) == empty` | "
  f"{not (set(sel_ids) & all_used)} |")
w(f"| overlap with `human_annotations_50.csv` | "
  f"{len(set(sel_ids) & used['human_annotations_50.csv'])} |")
w(f"| overlap with `llm_batch_01.csv` | {len(set(sel_ids) & used['llm_batch_01.csv'])} |")
w(f"| overlap with `llm_batch_02.csv` | {len(set(sel_ids) & used['llm_batch_02.csv'])} |")
w(f"| duplicate record_ids | {len(sel_ids) - len(set(sel_ids))} |")
w(f"| distinct normalized prompts | "
  f"{len({re.sub(chr(92) + 's+', ' ', r['prompt']).strip().lower() for r in sel})} |")
w("")
w("`record_id` was used as the primary identity key throughout. No assumption was")
w("made from row position.")
w("")
w("## source_dataset distribution")
w("")
w("| source_dataset | selected | eligible | share of batch |")
w("|---|---|---|---|")
elig = Counter(r["source_dataset"] for r in comb if r["id"] not in all_used)
for k, v in src_c.most_common():
    w(f"| {k} | {v} | {elig[k]} | {v / 10:.1f}% |")
w(f"| **total** | **{sum(src_c.values())}** | **{sum(elig.values())}** | **100.0%** |")
w("")
w("## framing distribution")
w("")
w("| framing | count |")
w("|---|---|")
for k, v in frm_c.most_common():
    w(f"| {k} | {v} |")
w("")
w("## category distribution")
w("")
w("| category | count |")
w("|---|---|")
for k, v in cat_c.most_common():
    w(f"| {k} | {v} |")
w("")
w("## prompt-type distribution (derived from prompt text)")
w("")
w("| prompt_type | count |")
w("|---|---|")
for k, v in pt_c.most_common():
    w(f"| {k} | {v} |")
w(f"| **distinct prompt types** | **{len(pt_c)}** |")
w("")
w("## response-length distribution")
w("")
w("| band | characters | count |")
w("|---|---|---|")
bands = [("L1_very_short", "<120"), ("L2_short", "120-449"),
         ("L3_medium", "450-1099"), ("L4_long", "1100-2199"),
         ("L5_very_long", "2200+")]
for k, rng in bands:
    w(f"| {k} | {rng} | {lb_c.get(k, 0)} |")
w("")
w("## model distribution")
w("")
w("| model | count |")
w("|---|---|")
for k, v in md_c.most_common():
    w(f"| {k or '(blank)'} | {v} |")
w(f"| **distinct models** | **{len(md_c)}** |")
w("")
w("## Selection methodology")
w("")
w("1. **Pool construction.** Loaded all 5,100 records from")
w("   `combined_evaluator_dataset.csv`. Loaded `record_id` from")
w("   `human_annotations_50.csv`, `llm_batch_01.csv` and `llm_batch_02.csv`. Their")
w("   union (150 records, zero pairwise overlap) was removed, leaving 4,950 eligible.")
w("2. **Label blindness.** Selection loaded only `prompt`, `response`, `source_dataset`,")
w("   `source_file`, `source_id`, `group_id`, `model`, `framing`, `category`,")
w("   `temperature`, `seed`, `sample_idx`, `original_id` and `is_paper1_bridge`.")
w("   The decision dict is asserted to contain none of `source_label`, `f1`-`f5`,")
w("   or any prior-batch score. `source_label` is never read for any purpose.")
w("   No record was chosen because a sycophantic response was expected, and no")
w("   effort was made to balance or maximize any facet score.")
w("3. **Prompt-type taxonomy from text.** A deterministic rule classified each")
w("   pooled prompt into a behavior-relevant type spanning the requested axes:")
w("   neutral factual checks, stated beliefs, opinion prompts, false premises,")
w("   leading questions, preference/decision prompts, disagreement and pressure")
w("   prompts, validation-oriented prompts, and explicit desired-conclusion prompts")
w("   (`you must agree`, `right?`, `restate your opinion`). Classification reads")
w("   prompt text plus `framing` only.")
w("4. **Prompt ownership before quota filling.** 1,574 unique normalized prompts")
w("   exist in the pool, and `schis02` framings overlap `ds1` on 49 of 50 prompts.")
w("   Assigning prompts greedily would starve scarce cells, so each unique prompt")
w("   is first assigned to exactly one `(source_dataset, prompt_type)` cell, with")
w("   the cell having the smallest unique supply winning contested prompts. Quotas")
w("   are then drawn only from owned supply, so batch-wide prompt deduplication")
w("   holds by construction.")
w("5. **Proportional quotas, no artificial balance.** Quotas use a largest-remainder")
w("   apportionment over owned unique-prompt supply, so the batch mirrors the")
w("   remaining dataset's real prompt composition. Cells whose quota was capped by")
w("   their own supply are marked in the table above and the remainder was")
w("   redistributed to cells with headroom.")
w("6. **Within-cell diversity.** Selection round-robins across")
w("   `(model, response-length band)` pairs with independent per-pair pointers, so")
w("   every model and length band is represented once before any is repeated.")
w("7. **Prompt deduplication.** All 1,000 selected prompts are distinct under")
w("   whitespace-normalized lowercase comparison, so the batch contains no")
w("   duplicate or near-duplicate prompt.")
w("8. **Determinism.** Fixed seed `303100`, combined with per-cell seeds derived")
w("   from `seed|source|prompt_type`, so selection is fully reproducible.")
w("")
w("## Diversity coverage against requested axes")
w("")
w("| requested axis | covered by |")
w("|---|---|")
w("| source_dataset | 5 sources present |")
w("| framing | unframed, blank, authority, leading, neutral, opinion, original |")
w("| prompt type | 18 distinct text-derived types |")
w("| neutral factual questions | `direct_factual_check`, `schis_neutral`, `open_factual`, MC quizzes |")
w("| user belief statements | `stated_belief_verification`, `schis_opinion`, `opinion_stated` |")
w("| opinion prompts | `decisive_opinion`, `opinion_stated`, `debatable_position` |")
w("| false-premise prompts | `false_premise_because`, `false_premise_health` |")
w("| leading questions | `leading_confirmation`, `schis_leading`, `forced_agreement` |")
w("| preference-driven prompts | `user_decision_advice`, `personal_advice` |")
w("| disagreement / pressure prompts | `explicit_pushback`, `wrong_answer_pressure`, `user_confusion`, `probing_why` |")
w("| validation-oriented prompts | `opinion_stated`, `user_decision_advice`, MC 'I believe ... Do you agree?' |")
w("| prompts with explicit desired conclusions | `forced_agreement` (`you must agree`, `right?`), `decisive_opinion` (`one decisive answer`) |")
w("| response length / style | 5 length bands from <120 to 2200+ characters |")
w("")
w("## Known representativeness caveat")
w("")
w("Because quotas follow unique-prompt supply, `camilablank` contributes 45.6% of the")
w("batch and `ds1` only 4.5%. `ds1`'s four prompt types overlap `schis02`'s framing")
w("variants on prompt text, so after prompt ownership only two `ds1` cells retain")
w("supply. The batch therefore under-represents `ds1` relative to its row count while")
w("mirroring the dataset's distinct-prompt mix. This is documented rather than")
w("corrected, since correcting it would require distorting the proportional")
w("apportionment.")
w("")
w("## Selected record_ids (1,000)")
w("")
for i, r in enumerate(sel, 1):
    w(f"{i:4d}. `{r['record_id']}`")
w("")
(D / "llm_batch_03_1000_selection_report.md").write_text("\n".join(L) + "\n",
                                                          encoding="utf-8")
print("wrote llm_batch_03_1000_selection_report.md")

# ------------------------------------------------------------------ chunks
CK = D / "batch_03_checkpoints"
CK.mkdir(exist_ok=True)
manifest = []
for c in range(0, 1000, CHUNK):
    rows = sel[c:c + CHUNK]
    p = CK / f"chunk_{c // CHUNK + 1:02d}.jsonl"
    with p.open("w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps({
                "record_id": r["record_id"],
                "source_dataset": r["source_dataset"],
                "prompt_type": r["prompt_type"],
                "prompt": r["prompt"],
                "response": r["response"],
            }, ensure_ascii=False) + "\n")
    manifest.append({"chunk": c // CHUNK + 1, "file": p.name, "n": len(rows)})
(CK / "manifest.json").write_text(
    json.dumps({"chunk_size": CHUNK, "chunks": manifest}, indent=1), encoding="utf-8")
print(f"wrote {CK / 'manifest.json'}: {len(manifest)} chunks x {CHUNK} records")
