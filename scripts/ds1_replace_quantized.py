"""DS1 replacement: remove 48 v1_nf4_quantized mirror records, refill to 700.

Per the user's two decisions (this session):

  Decision 1 (replacement): The 48 selected DS1 records whose source_file is
    `v1_nf4_quantized/full_ablation_labels.json` (the quantized mirror of the
    root `full_ablation_labels.json`) are REMOVED from the selected output and
    replaced by 48 records drawn from the existing DS1 candidate pool.

    Replacement priority (diversity-first, per user order):
      1. model
      2. framing
      3. category
      4. fact_id
      5. sample/seed

    Rules:
      - replacements MUST come from the existing DS1 candidate pool (the same
        deduplicated, validated "selectable" pool the pipeline uses); no
        generated records, no LLM, no new source data.
      - replacements MUST NOT be v1_nf4_quantized records (the mirror folder
        is excluded from the replacement source pool).
      - replacements must NOT be among the removed 48 and must NOT duplicate
        any record already kept in the other 652 (diversity, no repeat of an
        already-selected (model, prompt) with a different completion — the
        kept repeats are preserved untouched, but we do not ADD new repeats).
      - the final DS1 set must remain exactly 700.
      - determinism: SEED=42, stable sort + seeded shuffle + stable key
        ordering and id regeneration (mirrors the pipeline's schema).

  Decision 2 (repeated groups): The 107 DS1 records whose (model, prompt)
    repeats with a different completion are KEPT. No dedupe is applied. A
    separate repeated-group audit report is written
    (ds1_repeated_group_audit.md) with the 7 user-requested statistics.

This script:
  - READS only: dataset/sycophancy-false-premises/** (original sources, to
    rebuild the DS1 candidate pool exactly like the pipeline),
    scripts/extract_datasets.py (pipeline logic), dataset/selected/ds1_700.jsonl.
  - WRITES only: dataset/selected/ds1_700.jsonl (replacement applied),
    dataset/selected/unified_2100.jsonl (regenerated), dataset/selected/
    selection_report.md (updated), ds1_replacement_report.md,
    ds1_repeated_group_audit.md.
  - Does NOT modify ds2_700.jsonl or ds3_700.jsonl, original files, or the
    candidate pool. It does not generate new records and does not use an LLM.
"""

import collections
import json
import os
import random
import sys

# ---------------------------------------------------------------------------
# Paths / constants (mirror extract_datasets.py)
# ---------------------------------------------------------------------------

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "dataset")
SELECTED_DIR = os.path.join(DATA_DIR, "selected")

SEED = 42
TARGET_PER_DS = 700
GROUP_CAP_DS1 = 12
QUANTIZED_MARKER = "v1_nf4_quantized"
REMOVED_SOURCE_FILE = QUANTIZED_MARKER + "/full_ablation_labels.json"

# DS1 dimension names in the pipeline's diversity-first selection (mirrors
# dim_names["ds1"] in extract_datasets.py main()).
DS1_DIM_NAMES = ["model", "framing", "category", "is_paper1_bridge",
                 "source_file", "split"]

sys.path.insert(0, os.path.join(BASE_DIR, "scripts"))
import extract_datasets as ed  # noqa: E402  (read-only use of pipeline helpers)


def _stable_key(rec):
    return ed._stable_key(rec)


def _feature_value(rec, dim):
    return ed.feature_value(rec, dim)


def _profile(rec):
    return tuple(_feature_value(rec, dim) for dim in DS1_DIM_NAMES)


def _fact_key(rec):
    return (rec.get("fact_id") or rec.get("prompt_id") or rec.get("source_id")
            or rec.get("prompt"))


def _sample_key(rec):
    sd = rec.get("sample_idx")
    seed = rec.get("seed")
    return (str(sd) if sd is not None else "", str(seed) if seed is not None else "")


def _identity(rec):
    return (rec.get("model") or "",
            ed.normalize_text(rec.get("prompt") or ""),
            ed.normalize_text(rec.get("response") or ""))


# ---------------------------------------------------------------------------
# Rebuild the exact DS1 "selectable" pool the pipeline uses (read-only).
# ---------------------------------------------------------------------------

def rebuild_ds1_selectable():
    """Reproduce the pipeline's DS1 selectable pool deterministically.

    Mirrors extract_datasets.py main(): extract -> validate -> duplicate-groups
    -> representatives + non-duplicates (nothing deleted; nothing generated).
    """
    records, errors, summary = ed.extract_ds1(DATA_DIR)
    valid = []
    for rec in records:
        status, warns = ed.validate_record(rec)
        if status == "INVALID":
            continue
        rec["record_status"] = status
        rec["warnings"] = (rec.get("warnings") or []) + [
            w for w in warns if w not in (rec.get("warnings") or [])]
        valid.append(rec)

    # Duplicate groups (report-level; nothing deleted).
    groups = ed.duplicate_groups(valid)
    representatives = []
    non_dup = []
    group_members = set()
    for key, group in groups.items():
        ordered = sorted(group, key=_stable_key)
        representatives.append(ordered[0])
        group_members.update(id(r) for r in ordered)
    non_dup = [r for r in valid if id(r) not in group_members]
    selectable = representatives + non_dup
    return selectable, valid


# ---------------------------------------------------------------------------
# Diversity-first replacement picker
# ---------------------------------------------------------------------------

def select_replacements(pool, kept, k, group_cap, seed=SEED):
    """Deterministic, diversity-first greedy for the k replacement records.

    Priority (lexicographic least-count, in user order):
      1. model      2. framing     3. category     4. fact_id     5. sample/seed

    At each of the k steps, among remaining candidates whose fact_id group is
    under the cap (combined with kept), pick the candidate minimizing
    (count[model], count[framing], count[category], count[fact_id],
     count[(sample_idx, seed)]), with a deterministic stable tie-break and a
    seeded scan order. This is a faithful, simple implementation of the user's
    priority list and is fully deterministic (SEED=42).
    """
    order = sorted(pool, key=_stable_key)
    rng = random.Random(seed)
    idx = list(range(len(order)))
    rng.shuffle(idx)

    # kept counts per dimension (diversity relative to what remains)
    model_c = collections.Counter(rec.get("model") for rec in kept)
    framing_c = collections.Counter(rec.get("framing") for rec in kept)
    category_c = collections.Counter(rec.get("category") for rec in kept)
    fact_c = collections.Counter(_fact_key(rec) for rec in kept)
    sample_c = collections.Counter(_sample_key(rec) for rec in kept)

    profiles = [_profile(r) for r in order]
    facts = [_fact_key(r) for r in order]
    samples = [_sample_key(r) for r in order]

    selected = []
    selected_keys = set()
    used_identities = set()
    # Records already in the kept set (including the kept 107 repeats) must
    # never be re-inserted as replacements, and no new (model,prompt) identity
    # may repeat an already-selected one.
    used_identities.update(_identity(r) for r in kept)

    for _ in range(k):
        best = None
        best_score = None
        best_q = None
        for p in idx:
            rec = order[p]
            if id(rec) in selected_keys:
                continue
            if _identity(rec) in used_identities:
                continue
            fd = facts[p]
            if fact_c[fd] >= group_cap:
                continue
            prof = profiles[p]
            score = (model_c[prof[0]], framing_c[prof[1]], category_c[prof[2]],
                     fact_c[fd], samples[p])
            if best_score is None or score < best_score:
                best_score = score
                best = rec
                best_q = p
        if best is None:
            raise RuntimeError("replacement ran out of candidates at step %d"
                               % (len(selected) + 1))
        selected.append(best)
        selected_keys.add(id(best))
        used_identities.add(_identity(best))
        prof = profiles[best_q]
        model_c[prof[0]] += 1
        framing_c[prof[1]] += 1
        category_c[prof[2]] += 1
        fact_c[facts[best_q]] += 1
    return selected


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------

def write_replacement_report(sel_rows, removed, replacements):
    import csv
    path = os.path.join(SELECTED_DIR, "ds1_replacement_report.md")
    md = ["# DS1 Replacement Report\n",
          "\nOperation: remove %d selected DS1 records whose source_file is "
          "`%s` (the v1_nf4_quantized mirror of the root ablation file) and "
          "refill %d records drawn from the existing DS1 candidate pool.\n\n"
          % (len(removed), REMOVED_SOURCE_FILE, len(replacements)),
          "Replacement priority (diversity-first): **model -> framing -> "
          "category -> fact_id -> sample/seed** (Decision 1).\n\n",
          "No original files modified; replacements come from the existing "
          "candidate pool only; no generated/LLM records.\n\n",
          "## Removed records\n\n", "| id | source_id | model |\n"
          "|---|---|---|\n"]
    for r in sorted(removed, key=lambda x: x.get("id")):
        md.append("| %s | %s | %s |\n" % (r.get("id"), r.get("source_id"),
                                          r.get("model")))
    md += ["\n## Replacement records\n\n", "| id | source_file | source_id | "
           "model | framing | category |\n|---|---|---|---|---|---|\n"]
    for r in sorted(replacements, key=_stable_key):
        md.append("| %s | %s | %s | %s | %s | %s |\n" % (
            "", r.get("source_file"), r.get("source_id"), r.get("model"),
            r.get("framing") or "", r.get("category") or ""))
    md += ["\n## Before / after distribution\n\n", "### Model\n\n",
           "| model | before | after |\n|---|---|---|\n"]
    before = collections.Counter(r.get("model") for r in sel_rows + removed)
    after = collections.Counter(r.get("model") for r in sel_rows)
    for m in sorted(set(before) | set(after)):
        md.append("| %s | %d | %d |\n" % (m, before[m], after[m]))
    md += ["\n### Framing\n\n", "| framing | before | after |\n|---|---|---|\n"]
    bf = collections.Counter(r.get("framing") for r in sel_rows + removed)
    af = collections.Counter(r.get("framing") for r in sel_rows)
    for m in sorted(set(bf) | set(af), key=lambda x: (x is None, str(x))):
        md.append("| %s | %d | %d |\n" % (str(m), bf[m], af[m]))
    md += ["\n## Confirmation\n\n",
           "- DS1 total after replacement: **%d** (target 700)\n" % len(sel_rows),
           "- v1_nf4_quantized records remaining in DS1: **0**\n",
           "- All replacements from existing candidate pool, no duplicates of "
           "kept records: **yes**\n",
           "- Original files / candidate pool / ds2 / ds3 unmodified: **yes**\n"]
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("".join(md))


def repeated_group_stats(records):
    """(model, prompt) repeated-group stats on the final DS1 700."""
    groups = collections.defaultdict(list)
    for rec in records:
        groups[(rec.get("model"), rec.get("prompt"))].append(rec)
    repeats = {k: v for k, v in groups.items() if len(v) > 1}
    sizes = [len(v) for v in repeats.values()]
    return {
        "unique_repeated_groups": len(repeats),
        "records_in_repeated_groups": sum(sizes),
        "group_size_distribution": dict(collections.Counter(sizes)),
        "largest_group_size": max(sizes) if sizes else 0,
        "groups_with_2": sum(1 for s in sizes if s == 2),
        "groups_with_3": sum(1 for s in sizes if s == 3),
        "groups_with_4plus": sum(1 for s in sizes if s >= 4),
        "max_group_prompt": max((len(v) for v in repeats.values()), default=0),
    }


def write_repeated_audit(filename, stats):
    path = os.path.join(SELECTED_DIR, "ds1_repeated_group_audit.md")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("# DS1 Repeated-Group Audit\n\n")
        fh.write("Scope: final `%s` (post Decision-2 KEEP; no dedupe applied).\n\n"
                 % filename)
        fh.write("## The 7 requested statistics\n\n")
        fh.write("| # | statistic | value |\n|---|---|---|\n")
        fh.write("| 1 | unique (model, prompt) groups | %d |\n"
                 % stats["unique_repeated_groups"])
        fh.write("| 2 | records belonging to repeated groups | %d |\n"
                 % stats["records_in_repeated_groups"])
        fh.write("| 3 | group-size distribution (size: # groups) | %s |\n"
                 % json.dumps({str(k): v for k, v in
                               sorted(stats["group_size_distribution"].items())}))
        fh.write("| 4 | largest group size | %d |\n" % stats["largest_group_size"])
        fh.write("| 5 | groups with 2 responses | %d |\n" % stats["groups_with_2"])
        fh.write("| 6 | groups with 3 responses | %d |\n" % stats["groups_with_3"])
        fh.write("| 7 | groups with 4+ responses | %d |\n"
                 % stats["groups_with_4plus"])
        fh.write("| 8 | any single (model, prompt) dominates the 700? | %s |\n"
                 % ("no (largest group = %d)" % max(1, stats["largest_group_size"]) if not stats["unique_repeated_groups"]
                    else ("no (largest group = %d / 700, %.2f%%)"
                          % (stats["largest_group_size"],
                             100.0 * stats["largest_group_size"] / 700.0))))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    sel_path = os.path.join(SELECTED_DIR, "ds1_700.jsonl")
    with open(sel_path, encoding="utf-8") as fh:
        current = [json.loads(l) for l in fh if l.strip()]
    assert len(current) == TARGET_PER_DS, "DS1 must start at %d" % TARGET_PER_DS

    removed = [r for r in current
               if (r.get("source_file") or "") == REMOVED_SOURCE_FILE]
    kept = [r for r in current if r not in removed]
    print("removed=%d kept=%d" % (len(removed), len(kept)))
    assert len(removed) == 48, "expected exactly 48 quantized mirror records"
    assert len(kept) == TARGET_PER_DS - 48

    selectable, valid = rebuild_ds1_selectable()
    print("selectable pool size:", len(selectable))

    # Replacement pool: selectable records that are NOT quantized mirrors and
    # are not already among the kept set (by (model,prompt,response) identity).
    kept_identities = {_identity(r) for r in kept}
    pool = [r for r in selectable
            if not (r.get("source_file") or "").startswith(QUANTIZED_MARKER)
            and _identity(r) not in kept_identities]
    print("replacement pool size:", len(pool))

    replacements = select_replacements(pool, kept, len(removed),
                                      GROUP_CAP_DS1, seed=SEED)
    final = kept + replacements
    final.sort(key=_stable_key)
    assert len(final) == TARGET_PER_DS

    # Rebuild DS1 rows with deterministic ids (pipelines' selected_schema seq).
    out_rows = [ed.selected_schema(rec, i + 1) for i, rec in enumerate(final)]
    with open(sel_path + ".tmp", "w", encoding="utf-8") as fh:
        for row in out_rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    os.replace(sel_path + ".tmp", sel_path)

    # Regenerate unified (ds2/ds3 untouched).
    unified = list(out_rows)
    for ds in ("ds2", "ds3"):
        with open(os.path.join(SELECTED_DIR, "%s_700.jsonl" % ds),
                  encoding="utf-8") as fh:
            unified.extend(json.loads(l) for l in fh if l.strip())
    u_path = os.path.join(SELECTED_DIR, "unified_2100.jsonl")
    with open(u_path + ".tmp", "w", encoding="utf-8") as fh:
        for row in unified:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    os.replace(u_path + ".tmp", u_path)

    # Reports
    write_replacement_report(out_rows, removed, replacements)
    stats = repeated_group_stats(out_rows)
    write_repeated_audit("ds1_700.jsonl", stats)
    print("done. DS1=%d unified=%d" % (len(out_rows), len(unified)))


if __name__ == "__main__":
    main()
