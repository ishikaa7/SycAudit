"""Merge Batch 03 chunk checkpoints into the final llm_batch_03_1000.csv.

Reads the 20 approved chunk outputs in batch_03_checkpoints/, verifies the
result against the locked selection, and writes:

  dataset/combined/llm_batch_03_1000.csv   record_id,f1,f2,f3,f4,f5

Output schema and ordering match the earlier batches
(llm_batch_01.csv, llm_batch_02.csv): one row per record, selection order.
The merged file carries scores only; per-facet evidence stays in the
batch_03_checkpoints/chunk_NN.jsonl files and the review sheets.
"""
import csv
import json

from b3_chunk_lib import (
    CK, FACETS, SEL_PATH, chunk_slice, load_selection, sha,
    EXPECTED_SEL_HASH, EXPECTED_MASTER_HASH, MASTER,
)

OUT = CK.parent / "llm_batch_03_1000.csv"
CHUNKS = list(range(1, 21))


def main():
    sel = load_selection()
    if len(sel) != 1000:
        raise SystemExit(f"selection has {len(sel)} rows, expected 1000")

    rows = []
    for n in CHUNKS:
        p = CK / f"chunk_{n:02d}.jsonl"
        if not p.exists():
            raise SystemExit(f"missing checkpoint: {p}")
        part = [json.loads(ln) for ln in
                p.read_text(encoding="utf-8").splitlines() if ln.strip()]
        if len(part) != len(chunk_slice(sel, n)):
            raise SystemExit(f"chunk {n}: {len(part)} rows, wrong count")
        # Each checkpoint must carry its own slice of the selection, in order.
        for obj, s in zip(part, chunk_slice(sel, n)):
            if obj["record_id"] != s["record_id"]:
                raise SystemExit(f"chunk {n}: id mismatch {obj['record_id']} != {s['record_id']}")
        rows.extend(part)

    if len(rows) != 1000:
        raise SystemExit(f"expected 1000 rows, got {len(rows)}")

    with OUT.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["record_id", *FACETS])
        for r in rows:
            w.writerow([r["record_id"], *(str(r[f]) for f in FACETS)])

    # Re-read what was written and verify it round-trips against the checkpoints.
    written = list(csv.DictReader(OUT.open(encoding="utf-8")))
    if len(written) != 1000:
        raise SystemExit(f"wrote {len(written)} rows")
    for i, (out, src) in enumerate(zip(written, rows), 1):
        if out["record_id"] != src["record_id"]:
            raise SystemExit(f"row {i}: id mismatch after write")
        for f in FACETS:
            if out[f] != str(src[f]):
                raise SystemExit(f"row {i} ({src['record_id']}): {f} {out[f]} != {src[f]}")

    # Global order must equal the locked selection order.
    for i, (out, s) in enumerate(zip(written, sel), 1):
        if out["record_id"] != s["record_id"]:
            raise SystemExit(f"row {i}: selection order mismatch "
                             f"{out['record_id']} != {s['record_id']}")

    ids = [r["record_id"] for r in written]
    if len(set(ids)) != 1000:
        raise SystemExit("duplicate record_id in merged output")
    for f in FACETS:
        vals = {r[f] for r in written}
        if not vals <= {"0", "1", "2"}:
            raise SystemExit(f"{f} has out-of-range values: {sorted(vals)}")

    # Locked inputs must still be untouched.
    for label, path, want in (
        ("selection", SEL_PATH, EXPECTED_SEL_HASH),
        ("master", MASTER, EXPECTED_MASTER_HASH),
    ):
        got = sha(path)
        # The library stores truncated digests; compare on the same prefix.
        if not got.startswith(want):
            raise SystemExit(f"{label} hash changed: {got[:16]} != {want}")

    print(f"wrote {OUT}")
    print(f"  rows: {len(written)}  unique ids: {len(set(ids))}")
    print(f"  chunks merged: {len(CHUNKS)}")
    print(f"  selection hash: {sha(SEL_PATH)} (unchanged)")
    print(f"  master hash:    {sha(MASTER)} (unchanged)")


if __name__ == "__main__":
    main()
