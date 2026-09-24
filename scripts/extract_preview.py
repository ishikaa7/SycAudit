#!/usr/bin/env python3
"""EXTRACTION PREVIEW builder (READ-ONLY versus all original dataset files).

Purpose
-------
Before any final 500-per-source sampling or annotation, determine how each of
the 5 source datasets under ``dataset/`` can be converted into a clean
``prompt -> response`` example per our minimal schema:

    id, source_dataset, source_id, prompt, response, f1, f2, f3, f4, f5

This script:
  * reuses the existing inspection utilities (``inspect_datasets.read_text_lenient``)
  * applies one explicit extraction rule per source (see SOURCE_SPECS)
  * produces DETERMINISTIC, representative preview examples D  (no random sampling,
    no final training-data selection)
  * classifies every scanned record into: extracted / rejected / ambiguous /
    malformed / duplicate
  * NEVER modifies, deletes, renames or transforms any file under ``dataset/``
  * does NOT populate f1..f5
  * does NOT merge the final datasets

Outputs (created under ``dataset/``):
    dataset/extraction_preview.jsonl   (preview records)
    dataset/extraction_preview.csv     (same, CSV)
    dataset/extraction_preview_report.md (per-source validation report + verdicts)

Sources that cannot provide a genuine ``prompt -> model response`` pair are
reported as such and contribute 0 preview records; nothing is fabricated.

Usage:
    python scripts/extract_preview.py [--preview-size 20]
"""
from __future__ import annotations

import argparse
import csv
import json
import pathlib
import sys
from collections import Counter, defaultdict

REPO = pathlib.Path(__file__).resolve().parent.parent
DATASET = REPO / "dataset"

# reuse the lenient reader + truncator from the existing inspection script
sys.path.insert(0, str(REPO / "scripts"))
from inspect_datasets import read_text_lenient, truncate  # noqa: E402

PREVIEW_PER_SOURCE = 20       # ~20 representative examples per usable source
MAX_SAME_PROMPT = 4           # max preview records sharing one prompt (multi-model variety)

OUT_JSONL = DATASET / "extraction_preview.jsonl"
OUT_CSV = DATASET / "extraction_preview.csv"
OUT_MD = DATASET / "extraction_preview_report.md"


# --------------------------------------------------------------------------- generic record I/O
def iter_records(path: pathlib.Path):
    """Yield (record, line_no) for every parseable record; (None, line_no) for malformed lines.

    Supports .jsonl/.ndjson/.jsonlines line-by-line and .json (array / dict-of-dicts /
    flat object). Deliberately NOT a full parser — malformed records yield None so the
    caller can count them without silently discarding.
    """
    text, _ = read_text_lenient(path)
    suffix = path.suffix.lower()
    if suffix in (".jsonl", ".ndjson", ".jsonlines"):
        for i, line in enumerate(text.splitlines(), 1):
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line), i
            except json.JSONDecodeError:
                yield None, i
        return
    if suffix == ".json":
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            yield None, 1
            return
        if isinstance(data, list):
            for i, item in enumerate(data, 1):
                yield item, i
        elif isinstance(data, dict):
            if data and all(isinstance(v, dict) for v in data.values()):
                for i, item in enumerate(data.values(), 1):
                    yield item, i
            else:
                yield data, 1


# --------------------------------------------------------------------------- record -> (prompt, response) builders
def build_prompt_completion(rec: dict, file_stem: str):
    """Rule A (schis02/sycophancy-false-premises): prompt -> completion.

    The clean families (phase3 labeled / phase4 completions+labeled / cross_judge)
    store the raw model completion under 'completion'. The template-embedded
    families (gpt4o_labels_all, human_validation_*, ablation/full_ablation_labels)
    are NOT used because their 'completion' field re-echoes the chat template —
    they are reported as ambiguous/unsupported instead.
    """
    prompt = rec.get("prompt")
    completion = rec.get("completion")
    if not isinstance(prompt, str) or not prompt.strip():
        return ("rejected", "missing/empty 'prompt'")
    if not isinstance(completion, str) or not completion.strip():
        return ("rejected", "missing/empty 'completion'")
    rid = rec.get("id")
    if not isinstance(rid, (str, int)):
        rid = rec.get("fact_id") or rec.get("prompt_id") or "no-id"
    source_id = f"{file_stem}::{rid}::{rec.get('model', '?')}::{rec.get('sample_idx', '?')}"
    return ("extracted", (prompt.strip(), completion.strip(), source_id))


def build_conversation(rec: dict, file_stem: str):
    """Rule B (camilablank/sycophancy-datasets): the target response is the FINAL
    model turn ('bot') of 'history'; the prompt is the fully rendered preceding
    conversation (previous user+bot turns, ending with the final user message).

    Reasoning: these records are generated dialogues; the final bot response is the
    genuine model output under sycophantic pressure, and the earlier turns are the
    context that response lives in. Neither 'expected_answer' nor 'sycophancy_label'
    nor 'sycophancy_rating' is ever used as a response.
    """
    hist = rec.get("history")
    if not isinstance(hist, list) or not hist:
        return ("rejected", "missing/empty 'history'")
    for i, turn in enumerate(hist):
        if not isinstance(turn, dict):
            return ("ambiguous", f"turn {i} is not an object")
        if not isinstance(turn.get("user"), str) or not turn["user"].strip():
            return ("rejected", f"turn {i} has no 'user' text")
        bot = turn.get("bot")
        if not (isinstance(bot, str) and bot.strip()):
            if i < len(hist) - 1:
                return ("rejected", f"intermediate turn {i} has no 'bot' text")
            return ("rejected", "final turn has no 'bot' response")
    parts = []
    for i, turn in enumerate(hist[:-1]):
        parts.append(f"User: {turn['user'].strip()}\nAssistant: {turn['bot'].strip()}")
    parts.append(f"User: {hist[-1]['user'].strip()}")
    rid = rec.get("id")
    if not isinstance(rid, (str, int)):
        rid = "no-id"
    source_id = f"{file_stem}::{rid}"
    return ("extracted", ("\n\n".join(parts), hist[-1]["bot"].strip(), source_id))


def build_unsupported_no_response(rec: dict, file_stem: str):
    """meg-tong/sycophancy-eval: everything is a prompt + reference answers; there is
    NO model-generated response anywhere in the record."""
    return ("ambiguous", "no model-generated response field present")


def build_unsupported_mcq(rec: dict, file_stem: str):
    """Anthropic/model-written-evals (sycophancy subset): 'answer_matching_behavior'
    / 'answer_not_matching_behavior' are answer-choice labels of a multiple-choice
    prompt, not model responses."""
    return ("ambiguous", "multiple-choice; answer fields are choice labels, not model responses")


# --------------------------------------------------------------------------- source specifications
class SourceSpec:
    def __init__(self, key, display, files, build, rule, mapping, suitability, unresolved, excluded):
        self.key = key            # value used in the source_dataset column
        self.display = display
        self.files = files        # relative paths of CANDIDATE files (inspected)
        self.build = build        # callable(rec, file_stem) -> (status, payload)
        self.rule = rule
        self.mapping = mapping
        self.suitability = suitability
        self.unresolved = unresolved
        self.excluded = excluded  # (rel path, reason) not scanned as candidates


FALSE_PREMISES_CLEAN = [
    "sycophancy-false-premises/phase3_distributional/Llama-3.1-8B-Instruct_labeled.jsonl",
    "sycophancy-false-premises/phase3_distributional/Meta-Llama-3-8B-Instruct_labeled.jsonl",
    "sycophancy-false-premises/phase3_distributional/Mistral-7B-Instruct-v0.1_labeled.jsonl",
    "sycophancy-false-premises/phase3_distributional/Mistral-7B-Instruct-v0.2_labeled.jsonl",
    "sycophancy-false-premises/phase3_distributional/Qwen1.5-7B-Chat_labeled.jsonl",
    "sycophancy-false-premises/phase3_distributional/Qwen2.5-7B-Instruct_labeled.jsonl",
    "sycophancy-false-premises/phase3_distributional/cross_judge_gpt4o_labels.jsonl",
    "sycophancy-false-premises/phase4_scale/Llama-3.1-70B-Instruct_completions.jsonl",
    "sycophancy-false-premises/phase4_scale/Llama-3.1-70B-Instruct_labeled.jsonl",
    "sycophancy-false-premises/phase4_scale/Qwen2.5-72B-Instruct_completions.jsonl",
    "sycophancy-false-premises/phase4_scale/Qwen2.5-72B-Instruct_labeled.jsonl",
]

FALSE_PREMISES_EXCLUDED = [
    ("sycophancy-false-premises/gpt4o_labels_all.json", "completion re-echoes the chat template ([INST] ... [/INST]); not a clean response"),
    ("sycophancy-false-premises/human_validation_sample.json", "same template-embedded completion style"),
    ("sycophancy-false-premises/human_validation_results.json", "aggregate statistics (no prompt/completion)"),
    ("sycophancy-false-premises/ablation_labels.json", "completion re-echoes system/user/assistant template"),
    ("sycophancy-false-premises/full_ablation_labels.json", "completion re-echoes system/user/assistant template"),
    ("sycophancy-false-premises/v1_nf4_quantized/ablation_labels.json", "template-embedded completion"),
    ("sycophancy-false-premises/v1_nf4_quantized/full_ablation_labels.json", "template-embedded completion"),
    ("sycophancy-false-premises/v1_nf4_quantized/dual_label_wrong_results.json", "label-only records (no completion)"),
    ("sycophancy-false-premises/dual_label_wrong_results.json", "label-only records (no completion)"),
    ("sycophancy-false-premises/full_ablation_prompts.json", "prompt variants only (no completion)"),
    ("sycophancy-false-premises/phase3_distributional/entropy_results.json", "analysis results (no completion)"),
    ("sycophancy-false-premises/phase3_distributional/kdg_results.json", "analysis results (no completion)"),
    ("sycophancy-false-premises/phase4_scale/phase4_kdg_comparison.json", "analysis results (no completion)"),
]

CAMI_CANDIDATE = [
    "sycophancy-datasets/mmlu_single_turn.jsonl",
    "sycophancy-datasets/mmlu_rated.jsonl",
    "sycophancy-datasets/mmlu_reiterated_turn2.jsonl",
    "sycophancy-datasets/mmlu_turn3_rated.jsonl",
    "sycophancy-datasets/triviaqa_rated.jsonl",
    "sycophancy-datasets/political_opinions_turn2_response_restate.jsonl",
]

CAMI_EXCLUDED = [
    ("sycophancy-datasets/mmlu_rated_500.jsonl", "exact subset of mmlu_rated.jsonl (500 ids overlap); redundant"),
]

MEGTONG_FILES = [
    "sycophancy-eval/answer.jsonl",
    "sycophancy-eval/are_you_sure.jsonl",
    "sycophancy-eval/feedback.jsonl",
    "sycophancy-eval/mimicry.jsonl",
]

ANTHROPIC_SYCOPHANCY = [
    "model-written-evals/sycophancy/sycophancy_on_nlp_survey.jsonl",
    "model-written-evals/sycophancy/sycophancy_on_philpapers2020.jsonl",
    "model-written-evals/sycophancy/sycophancy_on_political_typology_quiz.jsonl",
]

SOURCE_SPECS = [
    SourceSpec(
        key="schis02/sycophancy-false-premises",
        display="schis02/sycophancy-false-premises",
        files=FALSE_PREMISES_CLEAN,
        build=build_prompt_completion,
        rule=("prompt -> completion (raw model output). Only the clean-completion families "
              "(phase3 *_labeled, phase4 *_completions / *_labeled, cross_judge) are candidates; "
              "template-embedded families are excluded as ambiguous."),
        mapping="source prompt -> 'prompt' ; model response -> 'completion' ; "
                "source_id -> <file>::<id|fact_id|prompt_id>::<model>::<sample_idx>",
        suitability=("USABLE - genuine prompt -> model-response pairs (multiple models per fact). "
                     "Requires a final decision on train/eval splitting by fact_id to avoid leakage."),
        unresolved=[
            "Whether template-embedded families (gpt4o_labels_all, ablation_labels, ...) should be cleaned by stripping the chat template and merged in (needs explicit approval).",
            "Whether each (fact, model, framing) row is a separate training example or whether completions should be aggregated per prompt.",
            "Some completions start with the chat template echo only in the EXCLUDED families; the clean families were verified template-free, but should be re-validated at scale before the final sample.",
        ],
        excluded=FALSE_PREMISES_EXCLUDED,
    ),
    SourceSpec(
        key="camilablank/sycophancy-datasets",
        display="camilablank/sycophancy-datasets",
        files=CAMI_CANDIDATE,
        build=build_conversation,
        rule=("history reconstruction: response = FINAL 'bot' turn of 'history'; "
              "prompt = prior turns rendered as 'User: ...\\nAssistant: ...' plus the final 'User:' message "
              "(previous turns kept as conversational context). expected_answer / sycophancy_label / "
              "sycophancy_rating are NEVER used as response."),
        mapping="source prompt -> rendered conversation (all but final bot turn) ; "
                "model response -> history[-1].bot ; source_id -> <file>::<record id>",
        suitability=("USABLE with special extraction - genuine model responses exist as 'bot' turns. "
                     "Caveat: many single-turn responses are trivial yes/no; sycophancy_label(/rating) "
                     "fields are available later as f1..f5 signal, not as response."),
        unresolved=[
            "Whether the final response should be the last bot turn (current rule) or the first bot turn after the leading question.",
            "whether single-turn (mmlu_single_turn) with only a yes/no response is useful for facet scoring or should be down-weighted.",
            "A small number of lines are malformed in the SOURCE files (verbatim) - decide whether to drop them permanently (they are dropped in the preview).",
        ],
        excluded=CAMI_EXCLUDED,
    ),
    SourceSpec(
        key="meg-tong/sycophancy-eval",
        display="meg-tong/sycophancy-eval",
        files=MEGTONG_FILES,
        build=build_unsupported_no_response,
        rule=("NO rule - no field contains a model-generated response. 'prompt' is a rendered chat prompt; "
              "'base.answer' is a LIST of reference answers; 'correct_answer'/'incorrect_answer' are labels."),
        mapping="NO field mapping: no genuine response field exists.",
        suitability=("NOT usable as-is for a prompt -> model response pool (violates the genuine-response "
                     "constraint). Only usable as a prompt-GENERATION source (query the model ourselves later)."),
        unresolved=[
            "Whether to keep meg-tong as a source of prompts for later live generation (a separate generation task).",
        ],
        excluded=[(f, "prompt-only benchmark wrapper; no model response field") for f in MEGTONG_FILES],
    ),
    SourceSpec(
        key="Anthropic/model-written-evals",
        display="Anthropic/model-written-evals",
        files=ANTHROPIC_SYCOPHANCY,
        build=build_unsupported_mcq,
        rule=("NO rule - sycophancy subset is multiple-choice: 'question' + "
              "'answer_matching_behavior' / 'answer_not_matching_behavior' are answer-choice labels "
              "(e.g. '(A)' / '(B)'), i.e. a label, not a model response. persona/advanced-ai-risk and "
              "winogenerated are excluded from the sycophancy scope."),
        mapping="NO field mapping: answer fields are choice labels, not model responses.",
        suitability=("NOT usable for this pool (multiple-choice only). The repository's sycophancy "
                     "data does not contain genuine model responses."),
        unresolved=[
            "Whether to keep Anthropic/model-written-evals as a separate MULTIPLE-CHOICE eval set (out of scope of this supervised pool).",
            "winogenerated (occupation/pronoun cloze) is NOT sycophancy data and remains excluded.",
        ],
        excluded=[(f, "synonym multiple-choice variant of the 3 files above") for f in ANTHROPIC_SYCOPHANCY[1:]]
        + [("model-written-evals/winogenerated/", "not sycophancy; excluded per task instructions")],
    ),
    SourceSpec(
        key="EleutherAI/sycophancy",
        display="EleutherAI/sycophancy",
        files=[],
        build=None,
        rule=("NO rule - the clone contains only 'sycophancy.py', a Hugging Face dataset LOADER that "
              "downloads sycophancy_on_nlp_survey / philpapers2020 / political_typology_quiz from "
              "anthropics/evals at load time. No local record files exist."),
        mapping="NO field mapping: no local data.",
        suitability=("REDUNDANT / NOT AN INDEPENDENT SOURCE - its 3 subsets are already present under "
                     "Anthropic/model-written-evals/sycophancy/. Do not ingest as a separate source_dataset."),
        unresolved=["None - remove from the candidate pool."],
        excluded=[("sycophancy/sycophancy.py", "HF loader script, points to anthropics/evals (no local data)")],
    ),
]


# --------------------------------------------------------------------------- scanning
def scan_source(spec: SourceSpec):
    stats = {
        "inspected": 0, "extracted": 0, "rejected": 0,
        "ambiguous": 0, "malformed": 0, "duplicates": 0,
        "rejected_reasons": Counter(), "ambiguous_reasons": Counter(),
    }
    pool: list[dict] = []
    seen_pairs: set[tuple[str, str]] = set()

    for rel in spec.files:
        path = DATASET / rel
        file_stem = rel.replace("\\", "/").split("/")[-1].rsplit(".", 1)[0]
        for rec, line_no in iter_records(path):
            if rec is None:
                stats["malformed"] += 1
                continue
            stats["inspected"] += 1
            status, payload = spec.build(rec, file_stem)
            if status == "extracted":
                prompt, response, source_id = payload
                dup_key = (prompt, response)
                if dup_key in seen_pairs:
                    stats["duplicates"] += 1
                    continue
                seen_pairs.add(dup_key)
                pool.append({
                    "source_id": source_id, "prompt": prompt, "response": response,
                    "file": rel.replace("\\", "/"), "row": line_no,
                })
                stats["extracted"] += 1
            elif status == "rejected":
                stats["rejected"] += 1
                stats["rejected_reasons"][payload] += 1
            else:
                stats["ambiguous"] += 1
                stats["ambiguous_reasons"][payload] += 1
    return stats, pool


def downsample(pool: list[dict], files: list[str], target: int = PREVIEW_PER_SOURCE):
    """Deterministic, varied preview selection: even spread per file, exact-duplicate
    and same-prompt caps. No randomness - never selects the final training data."""
    if not pool:
        return []
    by_file: dict[str, list[dict]] = defaultdict(list)
    for r in pool:
        by_file[r["file"]].append(r)
    groups = [(f, by_file[f]) for f in files if f in by_file]
    for f, recs in groups:
        recs.sort(key=lambda r: (r["prompt"], r["row"]))

    per_file = target // len(groups)
    remainder = target - per_file * len(groups)
    chosen: list[dict] = []
    prompt_count: Counter = Counter()

    for gi, (f, recs) in enumerate(groups):
        n = len(recs)
        quota = per_file + (1 if gi < remainder else 0)
        if quota <= 0:
            continue
        selected = 0
        offset = 0
        while selected < quota and offset < n:
            idx = min(n - 1, int((selected + 0.5) * n / quota) + offset)
            cand = recs[idx]
            if prompt_count[cand["prompt"]] >= MAX_SAME_PROMPT:
                offset += 1
                continue
            prompt_count[cand["prompt"]] += 1
            chosen.append(cand)
            selected += 1
            offset = 0
    return chosen


# --------------------------------------------------------------------------- output assembly
def preview_record(spec: SourceSpec, r: dict, ordinal: int) -> dict:
    return {
        "id": f"preview::{spec.key}::{ordinal}",
        "source_dataset": spec.key,
        "source_id": r["source_id"],
        "prompt": r["prompt"],
        "response": r["response"],
        "f1": None, "f2": None, "f3": None, "f4": None, "f5": None,
    }


def build_report(results: list[tuple[SourceSpec, dict, list[dict]]]) -> str:
    md = []
    md += ["# Extraction Preview Report", ""]
    md += ["_Generated by `scripts/extract_preview.py` (read-only versus original dataset files). "
           "f1..f5 are intentionally empty. No final sampling/annotation performed._", ""]
    md += ["**Duplicate semantics**: the `duplicates` count below is the number of rows whose content "
           "(prompt, response) is identical to a row already seen. This arises (a) in schis02 when the same "
           "completion is repeated across `sample_idx`/seed rows (temperature 0 produces identical text), and "
           "(b) in camilablank because some source files literally repeat identical lines (e.g. `triviaqa_rated` "
           "repeats rows sharing the same `id` and identical `history`). One representative record per unique "
           "(prompt, response) pair is kept in the valid pool; content duplicates are never double-counted as "
           "final candidates.", ""]

    md += ["## 1. Decision matrix", ""]
    md += ["| source_dataset | candidates inspected | extracted (valid pool) | preview extracted | rejected | ambiguous | malformed | duplicates | verdict |",
           "|---|---|---:|---:|---:|---:|---:|---:|---|"]
    for spec, stats, preview in results:
        md += [
            f"| `{spec.key}` | {stats['inspected']:,} | {stats['extracted']:,} | {len(preview)} "
            f"| {stats['rejected']} | {stats['ambiguous']} | {stats['malformed']} | {stats['duplicates']} | {spec.suitability.split(' - ')[0]} |"
        ]
    md += [""]

    md += ["## 2. Per-dataset detail", ""]
    for spec, stats, preview in results:
        md += [f"### {spec.display}", ""]
        md += [
            "1. **Dataset**: `{0}`".format(spec.key),
            "2. **Candidate records inspected**: {0:,}".format(stats["inspected"]),
            "3. **Successfully extracted (valid pool)**: {0:,}  (preview shows {1} representative records)".format(stats["extracted"], len(preview)),
            "4. **Rejected**: {0}".format(stats["rejected"]),
            "5. **Ambiguous**: {0}".format(stats["ambiguous"]),
            "6. **Malformed**: {0}".format(stats["malformed"]),
            "7. **Duplicates (exact prompt+response)**: {0}".format(stats["duplicates"]),
            "8. **Extraction rule used**: {0}".format(spec.rule),
            "9. **Example field mapping**: {0}".format(spec.mapping),
            "10. **Suitable for final training pool?**: {0}".format(spec.suitability),
            "11. **Unresolved questions**:",
        ]
        for q in spec.unresolved:
            md += [f"    - {q}"]
        if stats["rejected_reasons"]:
            md += ["", "    - rejected reasons:"]
            for reason, cnt in stats["rejected_reasons"].most_common():
                md += [f"        - {reason}: {cnt}"]
        if stats["ambiguous_reasons"]:
            md += ["", "    - ambiguous reasons (top 5):"]
            for reason, cnt in stats["ambiguous_reasons"].most_common(5):
                md += [f"        - {reason}: {cnt}"]
        if spec.excluded:
            md += ["", "    - files excluded from candidates:"]
            for rel, why in spec.excluded:
                md += [f"        - `{rel}` — {why}"]
        if preview:
            md += ["", "    - preview examples (ids):"]
            for r in preview:
                md += [f"        - {r['source_id']}"]
        md += [""]
    return "\n".join(md)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the extraction preview (read-only)")
    parser.add_argument("--preview-size", type=int, default=PREVIEW_PER_SOURCE, help="preview records per usable source")
    args = parser.parse_args()

    results = []
    for spec in SOURCE_SPECS:
        if spec.build is None:
            results.append((spec, {"inspected": 0, "extracted": 0, "rejected": 0,
                                   "ambiguous": 0, "malformed": 0, "duplicates": 0,
                                   "rejected_reasons": Counter(), "ambiguous_reasons": Counter()}, []))
            continue
        stats, pool = scan_source(spec)
        preview = downsample(pool, spec.files, target=args.preview_size)
        results.append((spec, stats, preview))

    records = []
    for spec, _stats, preview in results:
        for i, r in enumerate(preview, start=1):
            records.append(preview_record(spec, r, i))

    # ---- write jsonl
    with open(OUT_JSONL, "w", encoding="utf-8", newline="") as fh:
        for rec in records:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")

    # ---- write csv
    with open(OUT_CSV, "w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(records[0].keys()) if records else
                                ["id", "source_dataset", "source_id", "prompt", "response",
                                 "f1", "f2", "f3", "f4", "f5"])
        writer.writeheader()
        for rec in records:
            writer.writerow({k: ("" if v is None else v) for k, v in rec.items()})

    # ---- write markdown report
    OUT_MD.write_text(build_report(results), encoding="utf-8")

    # ---- terminal summary + A-F
    print("=" * 92)
    print("EXTRACTION PREVIEW - concise summary (read-only, no final sampling)")
    print("=" * 92)
    verdict = {}
    for spec, stats, preview in results:
        print(f"\n[{spec.key}]")
        print(f"  inspected={stats['inspected']:,}  extracted={stats['extracted']:,}  "
              f"rejected={stats['rejected']}  ambiguous={stats['ambiguous']}  "
              f"malformed={stats['malformed']}  duplicates={stats['duplicates']}  "
              f"preview={len(preview)}")
        if spec.build is None:
            print("  -> no local candidate files (HF loader only)")
        elif not preview and spec in (SOURCE_SPECS[2], SOURCE_SPECS[3]):
            print("  -> NOT extracted: no genuine model-response field (see report)")
        elif not preview:
            print("  -> no valid prompt->response records extracted")
        verdict[spec.key] = spec.suitability

    print("\n" + "=" * 92)
    print("A) CLEANLY USABLE")
    print("   - schis02/sycophancy-false-premises (phase3/phase4 clean-completion families)")
    print("   - camilablank/sycophancy-datasets (with conversation-reconstruction rule)")
    print("B) REQUIRE SPECIAL EXTRACTION")
    print("   - camilablank/sycophancy-datasets (multi-turn history -> final bot turn as response)")
    print("C) SHOULD NOT BE USED (as prompt->response pool)")
    print("   - Anthropic/model-written-evals (multiple-choice; answers are choice labels)")
    print("   - EleutherAI/sycophancy (REDUNDANT: HF loader only, data == Anthropic subset)")
    print("   - meg-tong/sycophancy-eval (no model response; only a prompt-generation source)")
    print("D) POTENTIAL REPLACEMENTS FOR AN UNUSABLE SOURCE")
    print("   - camilablank mmlu_* can cover the MMLU-style probing that Anthropic's MCQ subset covers")
    print("   - EleutherAI is fully replaced by Anthropic/model-written-evals/sycophancy/ (identical subsets)")
    print("   - meg-tong cannot replace anything for this pool (no responses); usable only if we generate responses")
    print("E) PROPOSED FIELD MAPPINGS")
    print("   schis02/sycophancy-false-premises:   prompt -> 'prompt' ;  response -> 'completion' ;      source_id -> <file>::<id|fact_id>::<model>::<sample_idx>")
    print("   camilablank/sycophancy-datasets:     prompt -> rendered history (all but final bot) ;  response -> history[-1].bot ;  source_id -> <file>::<record id>")
    print("F) actual extracted preview examples are in dataset/extraction_preview.jsonl/.csv (40 records: 20 per usable source).")
    print(f"\nWrote:")
    print(f"  {OUT_JSONL}")
    print(f"  {OUT_CSV}")
    print(f"  {OUT_MD}")


if __name__ == "__main__":
    main()