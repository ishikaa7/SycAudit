"""Batch 03 step 2: select exactly 1,000 NEW records.

Design notes
------------
Batch-wide prompt dedup is required, but schis02 framings and ds1 share 49/50
identical prompts. So prompt ownership must be decided BEFORE quota filling:
every unique normalized prompt is assigned to exactly one cell (the one with
the scarcest supply wins it), and quotas are then drawn from owned supply only.

Diversity axes (all structural / observable, never label-based):
  source_dataset, framing, category, prompt_type (text-derived),
  response-length band, model.

Label blindness is enforced by assertion: the decision dict cannot contain
source_label, f1..f5, or any prior-batch score.
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

COMB = D / "combined_evaluator_dataset.csv"
SEED = 303100
TARGET = 1000
FORBIDDEN = {"f1", "f2", "f3", "f4", "f5", "source_label",
             "label", "score", "sycophantic"}


def strict(p):
    with p.open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh, strict=True))


comb = strict(COMB)
used = set()
for n in ("human_annotations_50.csv", "llm_batch_01.csv", "llm_batch_02.csv"):
    used |= {r["record_id"] for r in strict(D / n)}


def slim(r):
    d = {k: r[k] for k in ("id", "prompt", "response", "source_dataset",
                           "source_file", "source_id", "group_id", "model",
                           "framing", "category", "temperature", "seed",
                           "sample_idx", "original_id", "is_paper1_bridge")}
    assert not (set(d) & FORBIDDEN), sorted(set(d) & FORBIDDEN)
    assert "source_label" not in d
    return d


pool = [slim(r) for r in comb if r["id"] not in used]
assert len(pool) == 4950, len(pool)


def np_(t):
    return re.sub(r"\s+", " ", t).strip().lower()


def base(r):
    return np_(r["prompt"])


def ptype(r):
    p = base(r)
    src = r["source_dataset"]
    if src == "camilablank":
        if "possible answers are" in p or re.search(r"\ba\.\s", p):
            return "multiple_choice_quiz"
        if "that's wrong" in p or "acknowledge the mistake" in p:
            return "wrong_answer_pressure"
        if "provide one decisive answer" in p or "your opinion" in p \
                or "restate your opinion" in p:
            return "decisive_opinion"
        if re.search(r"\b(should i|would you|advice|what would you)\b", p):
            return "personal_advice"
        return "open_factual"
    if src == "ds1":
        if re.search(r"\b(i believe|i think|i'm certain|i'm sure|"
                     r"according to (a )?\d{4} (nature )?study|"
                     r"research (indicates|shows|demonstrates)|data (shows|confirms))\b", p):
            return "stated_belief_verification"
        if re.search(r"^(because|given that|since)\b", p):
            return "false_premise_because"
        if re.search(r"\b(right\?|, right\b|is that right|is that true|can you (confirm|elaborate))\b", p):
            return "leading_confirmation"
        return "direct_factual_check"
    if src == "ds2":
        if re.search(r"\b(i do not agree|i disagree|i'?m not convinced|"
                     r"that'?s wrong|are you sure|that can'?t be right|"
                     r"your explanation doesn'?t match|your answer doesn'?t)\b", p):
            return "explicit_pushback"
        if re.search(r"\b(i'?m not sure i follow|i don'?t understand|i don'?t get|"
                     r"could you clarify|can you explain again)\b", p):
            return "user_confusion"
        if re.search(r"\bwhy (don'?t|do|not|is|are)\b", p):
            return "probing_why"
        return "debatable_position"
    if src == "ds3":
        if re.search(r"\b(you must agree|you'?d say|obviously|so you agree|"
                     r"don'?t you think|right\?)\b", p):
            return "forced_agreement"
        if re.search(r"\b(vaccine|autism|microchip|bleach|ammonia|5g|fluoride|"
                     r"chemtrail|alkaline|cancer cell)\w*\b", p) and re.search(
                     r"\b(cause|causes|contain|track|contaminat|cure|safe|treat)\b", p):
            return "false_premise_health"
        if re.search(r"\b(quit|quitting|switching|career|rent or buy|should i|"
                     r"smart move|worth it|decision|prepare)\b", p):
            return "user_decision_advice"
        if re.search(r"\b(my|me|i)\b", p) and re.search(
                     r"\b(stress|anxiety|healthy|habits|sleep|wellbeing)\b", p):
            return "personal_wellbeing"
        return "opinion_stated"
    return f"schis_{r['framing'] or 'none'}"


def lenband(n):
    if n < 120:
        return "L1_very_short"
    if n < 450:
        return "L2_short"
    if n < 1100:
        return "L3_medium"
    if n < 2200:
        return "L4_long"
    return "L5_very_long"


for r in pool:
    r["ptype"] = ptype(r)
    r["lenband"] = lenband(len(r["response"]))

cells = defaultdict(list)
for r in pool:
    cells[(r["source_dataset"], r["ptype"])].append(r)

# ---------------------------------------------------------------- ownership
# A unique prompt shared by several cells is owned by the cell whose total
# unique supply is smallest, so scarce cells are not starved by abundant ones.
cell_supply = {k: len({np_(r["prompt"]) for r in v}) for k, v in cells.items()}
owner = {}
for r in sorted(pool, key=lambda x: (cell_supply[(x["source_dataset"],
                                                 x["ptype"])], x["id"])):
    p = np_(r["prompt"])
    if p not in owner:
        owner[p] = (r["source_dataset"], r["ptype"])
owned = defaultdict(set)
for p, k in owner.items():
    owned[k].add(p)

print("CELL SUPPLY (rows / unique prompts / owned after dedup):")
for k in sorted(cells):
    print(f"  {k[0]:12s} {k[1]:30s} rows={len(cells[k]):5d} "
          f"uniq={cell_supply[k]:4d} owned={len(owned[k]):4d}")
print(f"\n  total unique prompts in pool: {len(owner)}  target: {TARGET}")
assert len(owner) >= TARGET

# ------------------------------------------------------------------ quotas
# largest-remainder over OWNED supply, preserving the dataset's real mix
keys = sorted(owned)
tot = sum(len(owned[k]) for k in keys)
exact = {k: len(owned[k]) / tot * TARGET for k in keys}
QUOTA = {k: min(len(owned[k]), int(exact[k])) for k in keys}
rem = TARGET - sum(QUOTA.values())
for k in sorted(keys, key=lambda t: -(exact[t] - int(exact[t]))):
    while rem > 0 and QUOTA[k] < len(owned[k]):
        QUOTA[k] += 1
        rem -= 1
assert sum(QUOTA.values()) == TARGET, sum(QUOTA.values())

print("\nQUOTA (largest-remainder over owned unique-prompt supply):")
for k in sorted(keys):
    q = QUOTA[k]
    if not q:
        continue
    flag = "  <-- CAPPED" if q >= len(owned[k]) else ""
    print(f"  {k[0]:12s} {k[1]:30s} quota={q:4d} / owned={len(owned[k]):4d}{flag}")

# --------------------------------------------------------------- selection
selected, sel_ids, seen_prompts = [], set(), set()

for k in sorted(keys):
    want = QUOTA[k]
    if not want:
        continue
    src, pt = k
    cands = [r for r in cells[k] if np_(r["prompt"]) in owned[k]]
    rng = random.Random(f"{SEED}|{src}|{pt}")
    rng.shuffle(cands)

    def free(x):
        return x["id"] not in sel_ids and np_(x["prompt"]) not in seen_prompts

    by_ml = defaultdict(list)
    for r in cands:
        by_ml[(r["model"], r["lenband"])].append(r)
    mk = sorted(by_ml, key=lambda kk: (-len(by_ml[kk]), kk[0], kk[1]))
    ptr = {kk: 0 for kk in mk}
    chosen, taken_ml = [], set()

    def take(strict_pairs):
        got = 0
        for kk in mk:
            if len(chosen) >= want:
                break
            if strict_pairs and kk in taken_ml:
                continue
            bucket = by_ml[kk]
            while ptr[kk] < len(bucket):
                r = bucket[ptr[kk]]
                ptr[kk] += 1
                if not free(r):
                    continue
                chosen.append(r)
                sel_ids.add(r["id"])
                seen_prompts.add(np_(r["prompt"]))
                taken_ml.add(kk)
                got += 1
                break
        return got

    while len(chosen) < want and take(True):
        pass
    while len(chosen) < want and take(False):
        pass
    assert len(chosen) == want, (k, len(chosen), want)
    selected.extend(chosen)

# final safety net: top up from any remaining eligible record, dedup enforced
if len(selected) < TARGET:
    rest = [r for r in pool
            if r["id"] not in sel_ids and np_(r["prompt"]) not in seen_prompts]
    rest.sort(key=lambda r: r["id"])
    rng = random.Random(SEED)
    rng.shuffle(rest)
    for r in rest[: TARGET - len(selected)]:
        selected.append(r)
        sel_ids.add(r["id"])
        seen_prompts.add(np_(r["prompt"]))

assert len(selected) == TARGET, len(selected)
assert len(sel_ids) == TARGET
assert not (sel_ids & used), sorted(sel_ids & used)[:5]
assert len({np_(r["prompt"]) for r in selected}) == TARGET

print(f"\nSELECTED {TARGET}")
print(f"  source_dataset : {dict(Counter(r['source_dataset'] for r in selected))}")
print(f"  framing        : {dict(Counter(r['framing'] or '(none)' for r in selected))}")
print(f"  category       : {dict(Counter(r['category'] or '(none)' for r in selected))}")
print(f"  lenband        : {dict(sorted(Counter(r['lenband'] for r in selected).items()))}")
print(f"  prompt_type    : {len(set(r['ptype'] for r in selected))} distinct")
print(f"  models         : {len({r['model'] for r in selected})} distinct")
print(f"  unique prompts : {len({np_(r['prompt']) for r in selected})}")
print(f"  overlap used   : {len(sel_ids & used)}")

OUT = D / "llm_batch_03_1000_selection.csv"
FIELDS = ["record_id", "original_id", "source_dataset", "source_file", "source_id",
          "group_id", "model", "framing", "category", "temperature", "seed",
          "sample_idx", "is_paper1_bridge", "prompt_type", "response_lenband",
          "prompt", "response"]
with OUT.open("w", encoding="utf-8", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=FIELDS)
    w.writeheader()
    for r in selected:
        row = {k: r.get(k, "") for k in FIELDS}
        row["record_id"] = r["id"]          # slim() stores the key as "id"
        row["prompt_type"] = r["ptype"]
        row["response_lenband"] = r["lenband"]
        w.writerow(row)
print(f"\nwrote {OUT.name} ({OUT.stat().st_size} bytes, {len(selected)} rows)")
