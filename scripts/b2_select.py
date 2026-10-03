"""Batch 02 step 3: select exactly 50 NEW records, stratified for behavioral
diversity using ONLY observable prompt text + structural metadata.

Hard rules honoured here:
  * ids from human_annotations_50.csv and llm_batch_01.csv are excluded
  * source_label is NEVER read into any decision variable (asserted below)
  * no f1..f5 field exists in combined, and no label field is consulted
  * prompts are deduplicated (normalized) across the whole batch
  * deterministic seed
"""
import csv
import random
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.stdout.reconfigure(encoding="utf-8")
D = ROOT / "dataset" / "combined"

SEED = 20250
FACETS = ("f1", "f2", "f3", "f4", "f5")
FORBIDDEN = set(FACETS) | {"source_label"}


def strict(p):
    with p.open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh, strict=True))


comb = strict(D / "combined_evaluator_dataset.csv")
human_ids = {r["record_id"] for r in strict(D / "human_annotations_50.csv")}
b01_ids = {r["record_id"] for r in strict(D / "llm_batch_01.csv")}
used = human_ids | b01_ids

# decision fields: prompt text + structural metadata ONLY.
# source_label is intentionally never loaded into this dict.
def slim(r):
    d = {k: r[k] for k in ("id", "prompt", "response", "source_dataset",
                            "framing", "category", "model", "group_id",
                            "source_id", "original_id")}
    assert not (set(d) & FORBIDDEN), sorted(set(d) & FORBIDDEN)
    return d


pool = [slim(r) for r in comb if r["id"] not in used]
assert len(pool) == 5000, len(pool)


def norm_prompt(t):
    return re.sub(r"\s+", " ", t).strip().lower()


def base(r):
    return re.sub(r"\s+", " ", r["prompt"]).strip().lower()


# ---------------------------------------------------------------- taxonomy
def ptype(r):
    """Behavior-relevant prompt type from observable text only."""
    p = base(r)
    src = r["source_dataset"]

    if src == "camilablank":
        if "possible answers are" in p or re.search(r"\ba\.\s", p):
            return "multiple_choice_quiz"
        if "that's wrong" in p or "acknowledge the mistake" in p:
            return "wrong_answer_pressure"
        if "provide one decisive answer" in p or "your opinion" in p:
            return "decisive_opinion"
        if re.search(r"\b(should i|would you|advice|what would you)\b", p):
            return "personal_advice"
        return "open_factual"

    if src == "ds1":
        if re.search(r"\b(i believe|i think|i'm certain|according to (a )?\d{4} study|"
                     r"research (indicates|shows|demonstrates))\b", p):
            return "stated_belief_verification"
        if re.search(r"^(because|given that|since)\b", p):
            return "false_premise_because"
        if re.search(r"\b(right\?|, right\b|is that right|is that true)\b", p):
            return "leading_confirmation"
        return "direct_factual_check"

    if src == "ds2":
        if re.search(r"\b(i do not agree|i disagree|that'?s wrong|are you sure|"
                     r"that can'?t be right|your explanation doesn'?t match)\b", p):
            return "explicit_pushback"
        if re.search(r"\b(i'?m not sure i follow|i don'?t understand|"
                     r"could you clarify|can you explain again)\b", p):
            return "user_confusion"
        if re.search(r"\bwhy (don'?t|do|not)\b", p):
            return "probing_why"
        return "debatable_position"

    if src == "ds3":
        if re.search(r"\b(you must agree|you'?d say|obviously|so you agree|"
                     r"don'?t you think)\b", p):
            return "forced_agreement"
        if re.search(r"\b(vaccine|autism|microchip|bleach|ammonia|5g|"
                     r"fluoride|chemtrail)\w*\b", p) and re.search(
                     r"\b(cause|causes|contain|track|contaminat|cancer|safe)\b", p):
            return "false_premise_health"
        if re.search(r"\b(quit|quitting|switching|career|rent or buy|"
                     r"should i|smart move|worth it|decision)\b", p):
            return "user_decision_advice"
        if re.search(r"\b(my|me|i)\b", p) and re.search(r"\b(stress|anxiety|"
                                                        r"healthy|habits|sleep)\b", p):
            return "personal_wellbeing"
        return "opinion_stated"

    # schis02 -> use the dataset's own structural framing
    return f"schis_{r['framing'] or 'none'}"


for r in pool:
    r["ptype"] = ptype(r)

print("=" * 78)
print("POOL BEHAVIOR TAXONOMY (prompt-text derived, no labels used)")
print("=" * 78)
tax = defaultdict(Counter)
for r in pool:
    tax[r["source_dataset"]][r["ptype"]] += 1
for s in sorted(tax):
    print(f"\n{s}")
    for k, v in tax[s].most_common():
        print(f"    {k:32s} {v:5d}")

# ---------------------------------------------------------------- quotas
# 10 per source; within-source spread across behavioral prompt types so the
# batch covers: false premises, leading questions, user pressure/disagreement,
# preference-driven prompts, validation-seeking, neutral factual, quizzes.
# quotas are derived from the observed taxonomy counts printed above; only
# types with ample supply are used, and each source sums to exactly 10.
QUOTA = {
    "camilablank": {"multiple_choice_quiz": 4, "wrong_answer_pressure": 3,
                    "decisive_opinion": 3},
    "ds1": {"stated_belief_verification": 3, "false_premise_because": 3,
            "leading_confirmation": 2, "direct_factual_check": 2},
    "ds2": {"explicit_pushback": 3, "user_confusion": 2, "probing_why": 3,
            "debatable_position": 2},
    "ds3": {"forced_agreement": 2, "false_premise_health": 3,
            "user_decision_advice": 3, "opinion_stated": 2},
    "schis02": {"schis_authority": 2, "schis_leading": 2, "schis_neutral": 2,
                "schis_opinion": 2, "schis_original": 2},
}
for _s, _q in QUOTA.items():
    assert sum(_q.values()) == 10, (_s, sum(_q.values()))

selected: list[dict] = []
taken_prompts: set[str] = set()
log = []

def norm_prompt(t):
    return re.sub(r"\s+", " ", t).strip().lower()


def topic_key(t):
    """Content-word signature, used only to spread blank-model sources
    (camilablank / ds3) across subject matter instead of across model names."""
    w = re.findall(r"[a-z]{4,}", t.lower())
    stop = {"that", "this", "with", "what", "which", "does", "your", "from",
            "have", "will", "were", "they", "their", "there", "would", "could",
            "should", "about", "into", "when", "user", "assistant", "possible",
            "answers", "following", "statement", "following", "true", "false"}
    ws = [x for x in w if x not in stop]
    return tuple(sorted(set(ws))[:4])


sel_ids: set[str] = set()
batch_models: Counter = Counter()
batch_topics: set = set()

for src in sorted(QUOTA):
    by_type = defaultdict(list)
    for r in pool:
        if r["source_dataset"] == src:
            by_type[r["ptype"]].append(r)

    for ptype_name, want in sorted(QUOTA[src].items()):
        cands = [r for r in by_type.get(ptype_name, [])
                 if r["id"] not in used
                 and r["id"] not in sel_ids
                 and norm_prompt(r["prompt"]) not in taken_prompts]
        rng = random.Random(f"{SEED}|{src}|{ptype_name}")
        rng.shuffle(cands)

        # Round-robin across models so a cell with many models (ds1, schis02)
        # yields one record per model before any model repeats.
        by_model = defaultdict(list)
        for r in cands:
            by_model[r["model"]].append(r)
        model_order = sorted(by_model, key=lambda m: (-len(by_model[m]), m))

        chosen: list[dict] = []
        rounds = max(len(by_model[m]) for m in model_order) if model_order else 0
        for i in range(rounds):
            for m in model_order:
                if len(chosen) >= want:
                    break
                bucket = by_model[m]
                if i >= len(bucket):
                    continue
                # re-check both id and prompt uniqueness: taken_prompts grows
                # inside this same cell as we take multiple records.
                def free(x):
                    return (x["id"] not in sel_ids
                            and norm_prompt(x["prompt"]) not in taken_prompts)

                r = next((x for x in bucket[i:] if free(x)), None)
                if r is None:
                    continue
                # for blank-model sources, spread across content topics too
                if not r["model"] and topic_key(r["prompt"]) in batch_topics:
                    alt = next((x for x in bucket[i:]
                                if free(x)
                                and topic_key(x["prompt"]) not in batch_topics), None)
                    if alt is None:
                        continue
                    r = alt
                chosen.append(r)
                sel_ids.add(r["id"])
                taken_prompts.add(norm_prompt(r["prompt"]))
                batch_models[r["model"]] += 1
                if not r["model"]:
                    batch_topics.add(topic_key(r["prompt"]))
            if len(chosen) >= want:
                break

        assert len(chosen) == want, (src, ptype_name, len(chosen), want)
        selected.extend(chosen)
        log.append((src, ptype_name, want, len(chosen)))

assert len(selected) == 50, len(selected)
ids = [r["id"] for r in selected]
assert len(set(ids)) == 50
assert not (set(ids) & used), sorted(set(ids) & used)[:5]
assert len({norm_prompt(r["prompt"]) for r in selected}) == 50

print("\n" + "=" * 78)
print("SELECTION: 50 records")
print("=" * 78)
for s, t, w, g in log:
    print(f"  {s:14s} {t:30s} quota={w} got={g}")
print(f"\n  source: {dict(Counter(r['source_dataset'] for r in selected))}")
print(f"  framing: {dict(Counter(r['framing'] or '(none)' for r in selected))}")
print(f"  category: {dict(Counter(r['category'] or '(none)' for r in selected))}")
print(f"  distinct models: {len({r['model'] for r in selected})}")
print(f"  distinct prompts: {len({norm_prompt(r['prompt']) for r in selected})}")
print(f"  overlap human_50: {len(set(ids) & human_ids)}")
print(f"  overlap batch_01: {len(set(ids) & b01_ids)}")

# ---------------------------------------------------------------- write selection
OUT = D / "llm_batch_02_selection.csv"
FIELDS = ["record_id", "original_id", "source_dataset", "source_id", "group_id",
          "model", "framing", "category", "prompt_type", "prompt", "response"]
with OUT.open("w", encoding="utf-8", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=FIELDS)
    w.writeheader()
    for r in selected:
        w.writerow({"record_id": r["id"], "original_id": r["original_id"],
                    "source_dataset": r["source_dataset"], "source_id": r["source_id"],
                    "group_id": r["group_id"], "model": r["model"],
                    "framing": r["framing"], "category": r["category"],
                    "prompt_type": r["ptype"], "prompt": r["prompt"],
                    "response": r["response"]})
print(f"\nwrote {OUT.relative_to(ROOT)}  ({OUT.stat().st_size} bytes, 50 rows)")

# json sidecar of ids for later steps
import json
(D / "llm_batch_02_selection_ids.json").write_text(
    json.dumps({"seed": SEED, "ids": ids}, indent=1), encoding="utf-8")
