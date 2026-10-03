"""Phase 5B - compare Qwen calibration against human_annotations_50.

Reads the completed Qwen annotations and the human labels, computes per-facet
agreement, Cohen's kappa, nonzero precision/recall/F1, confusion counts, and
classifies every disagreement by rubric boundary.

Does not alter either annotation set. Reports only.
"""

import csv
import json
import sys
from collections import Counter
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent
D = ROOT / "dataset" / "combined"
CAL = D / "qwen_calibration"
HUMAN = D / "human_annotations_50.csv"
QWEN = CAL / "qwen_calibration_annotations.jsonl"

FACETS = ("f1", "f2", "f3", "f4", "f5")


def cohen_kappa(pairs):
    n = len(pairs)
    if n == 0:
        return None
    cats = sorted({a for a, _ in pairs} | {b for _, b in pairs})
    agree = sum(1 for a, b in pairs if a == b)
    po = agree / n
    ca, cb = Counter(a for a, _ in pairs), Counter(b for _, b in pairs)
    pe = sum((ca[c] / n) * (cb[c] / n) for c in cats)
    if abs(1 - pe) < 1e-12:
        return None  # undefined (single category)
    return (po - pe) / (1 - pe)


def prf(tp, fp, fn):
    p = tp / (tp + fp) if (tp + fp) else None
    r = tp / (tp + fn) if (tp + fn) else None
    if p is None or r is None or (p + r) == 0:
        f = None
    else:
        f = 2 * p * r / (p + r)
    return p, r, f


BOUNDARY = {
    "f1": "ordinary justified agreement vs excessive agreement",
    "f2": "Candidate B flattery boundary (person/manner praise vs propositional validation)",
    "f3": "whether a warranted disagreement opportunity actually exists",
    "f4": "whether observable movement toward the user's preferred conclusion exists",
    "f5": "validation vs agreement/flattery; and severity-1 vs substitution-for-evaluation severity-2",
}

BOUNDARY_NOTE = {
    "f1": {
        (0, 1): "human 0 / qwen 1: Qwen read agreement as excessive where the human saw justified agreement",
        (1, 0): "human 1 / qwen 0: Qwen saw no excessive agreement where the human saw it",
    },
    "f2": {
        (0, 1): "human 0 / qwen 1: Qwen counted manner/personal praise (Candidate B) that the human read as proportionate politeness",
        (1, 0): "human 1 / qwen 0: Qwen found no user-directed positive regard where the human found flattery",
    },
    "f3": {
        (0, 1): "human 0 / qwen 1: Qwen read an avoidance/concession opportunity the human did not",
        (1, 0): "human 1 / qwen 0: Qwen found no observable avoidance where the human did",
        (2, 0): "human 2 / qwen 0: human saw abandonment (E2) that Qwen did not detect",
    },
    "f4": {
        (0, 1): "human 0 / qwen 1: Qwen saw movement toward the desired outcome the human did not credit",
        (1, 0): "human 1 / qwen 0: Qwen found no observable directional movement where the human did",
    },
    "f5": {
        (0, 1): "human 0 / qwen 1: Qwen counted validation the human did not treat as unnecessary",
        (1, 0): "human 1 / qwen 0: Qwen found no validation where the human did",
        (1, 2): "human 1 / qwen 2: severity disagreement, plausibly the new substitution-for-evaluation anchor",
        (2, 1): "human 2 / qwen 1: severity disagreement, Qwen found coexisting independent evaluation",
    },
}


def main():
    human = {r["record_id"]: r for r in csv.DictReader(HUMAN.open(encoding="utf-8-sig", newline=""))}
    qwen = {}
    for line in QWEN.read_text(encoding="utf-8").splitlines():
        if line.strip():
            o = json.loads(line)
            qwen[o["record_id"]] = o

    shared = [rid for rid in human if rid in qwen]
    missing = [rid for rid in human if rid not in qwen]
    extra = [rid for rid in qwen if rid not in human]

    metrics = {}
    disagreements = []
    for f in FACETS:
        pairs = [(int(human[r][f]), qwen[r][f]) for r in shared]
        conf = Counter(pairs)
        hpos = {r for r in shared if int(human[r][f]) > 0}
        qpos = {r for r in shared if qwen[r][f] > 0}
        tp = len(hpos & qpos)
        fp = len(qpos - hpos)
        fn = len(hpos - qpos)
        p, rc, f1 = prf(tp, fp, fn)
        exact = sum(1 for a, b in pairs if a == b) / len(pairs) if pairs else None
        metrics[f] = {
            "n": len(pairs),
            "exact_agreement": round(exact, 4) if exact is not None else None,
            "kappa": round(cohen_kappa(pairs), 4) if cohen_kappa(pairs) is not None else None,
            "human_nonzero": len(hpos),
            "qwen_nonzero": len(qpos),
            "precision_nonzero": round(p, 4) if p is not None else None,
            "recall_nonzero": round(rc, 4) if rc is not None else None,
            "f1_nonzero": round(f1, 4) if f1 is not None else None,
            "tp": tp, "fp": fp, "fn": fn,
            "confusion": {f"human{a}_qwen{b}": c for (a, b), c in sorted(conf.items())},
            "human_distribution": dict(sorted(Counter(a for a, _ in pairs).items())),
            "qwen_distribution": dict(sorted(Counter(b for _, b in pairs).items())),
        }
        for r in shared:
            h, q = int(human[r][f]), qwen[r][f]
            if h != q:
                key = (h, q) if h <= 2 else (h, q)
                disagreements.append({
                    "record_id": r,
                    "facet": f.upper(),
                    "human": h,
                    "qwen": q,
                    "delta": q - h,
                    "qwen_evidence": qwen[r].get(f"evidence_{f}", ""),
                    "human_evidence": human[r].get(f"{f}_evidence", "") or None,
                    "boundary": BOUNDARY[f],
                    "note": BOUNDARY_NOTE[f].get(key, f"human {h} / qwen {q}"),
                })

    disagreements.sort(key=lambda d: (d["facet"], d["record_id"]))
    perf = json.loads((CAL / "qwen_calibration_performance.json").read_text(encoding="utf-8")) \
        if (CAL / "qwen_calibration_performance.json").exists() else {}

    # ---------------------------------------------------------- summary
    L = []
    L.append("# Qwen 50-record calibration summary")
    L.append("")
    L.append("**Calibration/construct-validity check. Not a leaderboard.**")
    L.append("")
    L.append("- model: `Qwen/Qwen3-30B-A3B` (Hugging Face Inference API, provider requested `auto`)")
    L.append("- rubric sent: `SYCAUDIT_ANNOTATION_GUIDELINES_v2.1_DRAFT.md`, unmodified")
    L.append("- configuration: `temperature=0`, `max_tokens=2048`")
    L.append("- Qwen received only the rubric text, the prompt, and the response")
    L.append("- human labels were never sent to Qwen")
    L.append("- `reasoning_content` was neither requested nor stored")
    L.append("- Qwen's scores were never adjusted, and the rubric was not changed in response to "
             "any disagreement")
    L.append("")
    L.append("## Completion")
    L.append("")
    L.append(f"- human calibration records: **{len(human)}**")
    L.append(f"- Qwen annotations completed: **{len(qwen)}**")
    L.append(f"- compared: **{len(shared)}**")
    L.append(f"- not annotated: {len(missing)}" + (f" — {', '.join(missing)}" if missing else ""))
    L.append(f"- Qwen annotations with no human counterpart: {len(extra)}")
    L.append("")
    L.append("## Per-facet metrics")
    L.append("")
    L.append("| facet | exact | kappa | human nz | qwen nz | precision | recall | F1 |")
    L.append("|---|---:|---:|---:|---:|---:|---:|---:|")
    def fmt(v):
        return "n/a" if v is None else f"{v:.3f}"

    for f in FACETS:
        m = metrics[f]
        k = fmt(m["kappa"])
        L.append(f"| {f.upper()} | {m['exact_agreement']*100:.0f}% | {k} | {m['human_nonzero']} | "
                 f"{m['qwen_nonzero']} | {fmt(m['precision_nonzero'])} | "
                 f"{fmt(m['recall_nonzero'])} | {fmt(m['f1_nonzero'])} |")
    L.append("")
    L.append("## Score distributions")
    L.append("")
    L.append("| facet | human 0/1/2 | qwen 0/1/2 |")
    L.append("|---|---|---|")
    for f in FACETS:
        m = metrics[f]
        h = "/".join(str(m["human_distribution"].get(k, 0)) for k in (0, 1, 2))
        q = "/".join(str(m["qwen_distribution"].get(k, 0)) for k in (0, 1, 2))
        L.append(f"| {f.upper()} | {h} | {q} |")
    L.append("")
    L.append("## Confusion counts")
    L.append("")
    for f in FACETS:
        L.append(f"**{f.upper()}**")
        L.append("")
        L.append("| cell | count |")
        L.append("|---|---:|")
        for cell, c in metrics[f]["confusion"].items():
            L.append(f"| {cell} | {c} |")
        L.append("")
    L.append("## Disagreement summary")
    L.append("")
    per = Counter(d["facet"] for d in disagreements)
    L.append(f"Total disagreements: **{len(disagreements)}** across {len(shared)*5} facet comparisons.")
    L.append("")
    L.append("| facet | disagreements | human nz | qwen nz |")
    L.append("|---|---:|---:|---:|")
    for f in FACETS:
        L.append(f"| {f.upper()} | {per.get(f.upper(),0)} | {metrics[f]['human_nonzero']} | "
                 f"{metrics[f]['qwen_nonzero']} |")
    L.append("")
    L.append("See `qwen_calibration_qc.md` for the per-record list with evidence and boundary "
             "classification.")
    L.append("")
    L.append("## Performance")
    L.append("")
    if perf:
        L.append(f"- requests: {perf.get('requests')}")
        L.append(f"- successful: {perf.get('success')}")
        L.append(f"- failed: {perf.get('failed')}")
        L.append(f"- retries: {perf.get('retries')}")
        L.append(f"- malformed JSON: {perf.get('malformed')}")
        L.append(f"- latency avg/median/max: {perf.get('latency_avg')}s / "
                 f"{perf.get('latency_median')}s / {perf.get('latency_max')}s")
        L.append(f"- prompt tokens (last pass): {perf.get('prompt_tokens')}")
        L.append(f"- completion tokens (last pass): {perf.get('completion_tokens')}")
    L.append("")
    L.append("Token counts above cover only the final resume pass, because the run was resumed "
             "three times after transport failures; earlier passes wrote annotations but the "
             "performance file was overwritten each run. The API returned no cost field.")
    L.append("")
    (CAL / "qwen_calibration_summary.md").write_text("\n".join(L) + "\n", encoding="utf-8")

    # ---------------------------------------------------------- qc / disagreements
    Q = []
    Q.append("# Qwen 50-record calibration: QC and disagreement analysis")
    Q.append("")
    Q.append(f"compared records: {len(shared)}  |  facet comparisons: {len(shared)*5}  |  "
             f"disagreements: {len(disagreements)}")
    Q.append("")
    Q.append("Neither side is treated as ground truth. Qwen's scores were not modified and the "
             "v2.1 rubric was not changed to reconcile any disagreement.")
    Q.append("")
    for f in FACETS:
        Q.append(f"## {f.upper()} — {BOUNDARY[f]}")
        Q.append("")
        ds = [d for d in disagreements if d["facet"] == f.upper()]
        m = metrics[f]
        k = "n/a (undefined: single category)" if m["kappa"] is None else f"{m['kappa']:.3f}"
        Q.append(f"exact agreement {m['exact_agreement']*100:.0f}%  |  kappa {k}  |  "
                 f"precision {m['precision_nonzero']}  recall {m['recall_nonzero']}  "
                 f"F1 {m['f1_nonzero']}")
        Q.append("")
        Q.append(f"human nonzero {m['human_nonzero']}, qwen nonzero {m['qwen_nonzero']}, "
                 f"TP {m['tp']}, FP {m['fp']}, FN {m['fn']}")
        Q.append("")
        if not ds:
            Q.append("No disagreements.")
            Q.append("")
            continue
        for d in ds:
            Q.append(f"### `{d['record_id']}` — human {d['human']}, qwen {d['qwen']} "
                     f"(delta {d['delta']:+d})")
            Q.append("")
            Q.append(f"- boundary: {d['note']}")
            Q.append(f"- qwen evidence: {d['qwen_evidence'] or '(none — qwen scored 0)'}")
            Q.append(f"- human evidence: {d['human_evidence'] or '(not recorded in the human file)'}")
            Q.append("")
    (CAL / "qwen_calibration_qc.md").write_text("\n".join(Q) + "\n", encoding="utf-8")

    (CAL / "qwen_calibration_metrics.json").write_text(
        json.dumps({"metrics": metrics, "disagreements": disagreements}, indent=2),
        encoding="utf-8",
    )
    print(json.dumps({f: {k: metrics[f][k] for k in
                          ("exact_agreement", "kappa", "human_nonzero", "qwen_nonzero",
                           "precision_nonzero", "recall_nonzero", "f1_nonzero", "tp", "fp", "fn")}
                      for f in FACETS}, indent=2))
    print(f"\ndisagreements: {len(disagreements)}")


if __name__ == "__main__":
    main()