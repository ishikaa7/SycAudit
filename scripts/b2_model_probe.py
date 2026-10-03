"""Read-only probe: how much model diversity is actually available per
(source_dataset, prompt_type) cell? Determines achievable quotas.
"""
import csv
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.stdout.reconfigure(encoding="utf-8")
D = ROOT / "dataset" / "combined"


def strict(p):
    with p.open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh, strict=True))


comb = strict(D / "combined_evaluator_dataset.csv")
used = {r["record_id"] for r in strict(D / "human_annotations_50.csv")}
used |= {r["record_id"] for r in strict(D / "llm_batch_01.csv")}
pool = [r for r in comb if r["id"] not in used]


def base(r):
    return re.sub(r"\s+", " ", r["prompt"]).strip().lower()


def ptype(r):
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
    return f"schis_{r['framing'] or 'none'}"


for r in pool:
    r["ptype"] = ptype(r)

print("=" * 84)
print("MODEL AVAILABILITY PER CELL (blank model string shown as <blank>)")
print("=" * 84)
for src in ["camilablank", "ds1", "ds2", "ds3", "schis02"]:
    sp = [r for r in pool if r["source_dataset"] == src]
    print(f"\n### {src}  pool={len(sp)}  distinct_models={len({r['model'] for r in sp})}")
    for pt in sorted({r["ptype"] for r in sp}):
        sub = [r for r in sp if r["ptype"] == pt]
        mc = Counter(r["model"] for r in sub)
        distinct_prompts = len({base(r) for r in sub})
        top = ", ".join(f"{(k or '<blank>').split('/')[-1][:16]}={v}"
                        for k, v in mc.most_common(6))
        print(f"  {pt:30s} n={len(sub):4d} models={len(mc):2d} "
              f"distinct_prompts={distinct_prompts:4d}  [{top}]")
