"""Stage 2: readable dumps of the human-annotated 50 for qualitative analysis."""
import csv
import sys
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.stdout.reconfigure(encoding="utf-8")
HUM = ROOT / "dataset" / "combined" / "human_annotations_50.csv"
FACETS = ("f1", "f2", "f3", "f4", "f5")


def strict(p):
    with p.open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh, strict=True))


hum = strict(HUM)
MODE = sys.argv[1] if len(sys.argv) > 1 else "compact"


def show(i, r, full=False, resp_chars=1400):
    sc = " ".join(f"{f.upper()}={r[f]}" for f in FACETS)
    print(f"\n[{i:02d}] {r['record_id']}   {sc}")
    print(f"     src={r.get('source_dataset','')} framing={r.get('framing','')!r} cat={r.get('category','')}")
    print(f"     PROMPT ({len(r['prompt'])} ch):")
    for ln in textwrap.wrap(r["prompt"], 108)[:14]:
        print(f"       | {ln}")
    resp = r["response"]
    shown = resp if full else resp[:resp_chars]
    print(f"     RESPONSE ({len(resp)} ch{' [TRUNCATED FOR VIEW]' if not full and len(resp) > resp_chars else ''}):")
    for ln in textwrap.wrap(shown, 108):
        print(f"       | {ln}")
    if not full and len(resp) > resp_chars:
        print(f"       | ...[+{len(resp)-resp_chars} ch omitted]")


if MODE == "compact":
    print("=" * 120)
    print("  ALL 50 HUMAN-ANNOTATED RECORDS (compact)")
    print("=" * 120)
    for i, r in enumerate(hum):
        sc = " ".join(f"{f[-1]}={r[f]}" for f in FACETS)
        p = r["prompt"].replace("\n", " / ")
        print(f"[{i:02d}] {sc}  ({len(r['prompt'])}p/{len(r['response'])}r)  {r['record_id']}")
        print(f"      P: {p[:190]}")

elif MODE.startswith("f"):
    # s2.py f1 2  -> records where f1 == 2
    facet = MODE[1]
    want = sys.argv[2] if len(sys.argv) > 2 else "2"
    sel = [(i, r) for i, r in enumerate(hum) if r[facet] == want]
    print("=" * 110)
    print(f"  RECORDS WHERE {facet.upper()} == {want}   ({len(sel)} records)")
    print("=" * 110)
    for i, r in sel:
        show(i, r, full=True)

elif MODE == "pair":
    a, b, want = sys.argv[2], sys.argv[3], sys.argv[4]
    sel = [(i, r) for i, r in enumerate(hum)
           if (r.get(a, "0") or "0") != "0" and (r.get(b, "0") or "0") != "0"
           and (want == "nz" or r.get(a) == want or r.get(b) == want)]
    print("=" * 110)
    print(f"  RECORDS WITH {a.upper()},{b.upper()} BOTH NON-ZERO  ({len(sel)})")
    print("=" * 110)
    for i, r in sel:
        show(i, r, full=True)

elif MODE == "rec":
    n = int(sys.argv[2])
    show(n - 1, hum[n - 1], full=True)

elif MODE == "recs":
    for tok in sys.argv[2].split(","):
        n = int(tok)
        show(n - 1, hum[n - 1], full=True)

elif MODE == "all":
    for i, r in enumerate(hum):
        show(i, r, full=True)