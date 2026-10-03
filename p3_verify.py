import re
from pathlib import Path

d = Path("dataset/combined/rubric_adjudication")
t = (d / "RUBRIC_ADJUDICATION_REPORT.md").read_text(encoding="utf-8")

req = [
    "## 1. F2 mismatch summary",
    "## 2. The 26 human F2-positive cases",
    "## 3. Current-rubric reproducibility",
    "## 4. F2/F5 boundary analysis",
    "## 5. Human construct vs current operational construct",
    "## 6. Three candidate F2 definitions",
    "## 7. F5 findings",
    "## 8. Recommendation for the next calibration experiment",
    "## 9. No data modification",
]
for r in req:
    print(("OK  " if r in t else "MISS"), r)

case = re.compile(r"^\| \d+ \| `")
rows = [l for l in t.splitlines() if case.match(l)]
print()
print("section 2 case rows:", len(rows))
print("candidate sections :", t.count("### Candidate"))
print("words              :", len(t.split()))

for f in ["f2_rubric_candidates.md", "f5_rubric_analysis.md"]:
    s = (d / f).read_text(encoding="utf-8")
    print(f"{f:28s} words={len(s.split()):5d} lines={len(s.splitlines()):4d}")
