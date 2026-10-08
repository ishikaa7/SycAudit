import { useMemo, useState } from "react";
import { useSubmissionContext } from "../components/layout/SubmissionLayout.jsx";
import PageHeader from "../components/ui/PageHeader.jsx";
import Notice from "../components/ui/Notice.jsx";
import SycophancyGauge from "../components/evaluation/SycophancyGauge.jsx";
import { buildMatrix, collectModels, collectVariants } from "../utils/scoring.js";
import { generatePrototypeAnalysis, PROTOTYPE_BASELINE_METRICS, PROTOTYPE_CONFUSION, FACET_DEFS_PROTOTYPE } from "../data/prototypeAnalysis.js";

function ScoreBar({ value, max = 100 }) {
  const pct = Math.max(0, Math.min(100, (value / max) * 100));
  return (
    <div className="h-2 w-full rounded-full bg-slate-200">
      <div className="h-2 rounded-full bg-indigo-500" style={{ width: `${pct}%` }} />
    </div>
  );
}

export default function PrototypeAnalysisPage() {
  const { submission } = useSubmissionContext();
  const rows = useMemo(() => buildMatrix(submission), [submission]);
  const variants = useMemo(() => collectVariants(submission), [submission]);
  const models = useMemo(() => collectModels(submission), [submission]);

  const scoredRows = useMemo(
    () => rows.filter((r) => r.scored && r.finalScore !== null && r.response?.response_text),
    [rows]
  );

  const [selectedIndex, setSelectedIndex] = useState(0);

  if (!submission) {
    return (
      <div className="animate-fade-up">
        <PageHeader eyebrow="Mentor Demo" title="SycAudit Analysis (Prototype)" />
        <Notice tone="warning" title="No submission loaded">
          Select an existing audit from History.
        </Notice>
      </div>
    );
  }

  if (scoredRows.length === 0) {
    return (
      <div className="animate-fade-up">
        <PageHeader eyebrow="Mentor Demo" title="SycAudit Analysis (Prototype)" />
        <div className="card p-6">
          <h2 className="text-lg font-semibold text-slate-800">Response Variants</h2>
          <p className="mt-2 text-sm text-slate-600">
            This submission has {variants.length} variant(s) and {models.length} model(s). No scored responses with text were found.
          </p>
          <pre className="mt-4 overflow-auto rounded bg-slate-50 p-4 text-xs text-slate-600">
            {JSON.stringify(
              {
                variantCount: variants.length,
                modelCount: models.length,
                totalRows: rows.length,
              },
              null,
              2
            )}
          </pre>
        </div>
      </div>
    );
  }

  const analyses = scoredRows.map((r) => generatePrototypeAnalysis(r.response?.response_text));
  const selectedRow = scoredRows[selectedIndex];
  const selectedAnalysis = analyses[selectedIndex];
  const overallRows = [...analyses].sort((a, b) => a.sycophancyScore - b.sycophancyScore);
  const recommended = overallRows[0];
  const recIdx = analyses.findIndex((a) => a === recommended);
  const recommendedRow = scoredRows[recIdx];

  return (
    <div className="animate-fade-up space-y-6">
      <PageHeader
        eyebrow="Mentor Demo"
        title="SycAudit Analysis (Prototype)"
        subtitle="REAL prompt and REAL responses from existing history. Analysis values below are PROTOTYPE demo data only."
      />
      <Notice tone="warning" title="Prototype Analysis — ML grader integration pending">
        Facet scores, evidence, ranking, trustworthiness and recommendation are temporary demo values.
      </Notice>

      <section className="card p-6">
        <h2 className="text-lg font-semibold text-slate-800">Audit Overview</h2>
        <div className="mt-4 grid gap-4 md:grid-cols-2">
          <div>
            <h3 className="text-sm font-medium text-slate-600">Original Prompt (REAL)</h3>
            <p className="mt-2 whitespace-pre-wrap text-sm leading-relaxed text-slate-800">
              {submission.original_prompt}
            </p>
          </div>
          <div className="space-y-2 text-sm text-slate-600">
            <p>Response Variants: {scoredRows.length}</p>
            <p>Models used: {models.length}</p>
            <p>Audit status: {submission.status}</p>
            <p>Analysis status: Prototype (demo)</p>
          </div>
        </div>
      </section>

      <section className="card p-6">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-slate-800">Response Comparison</h2>
          <div className="flex flex-wrap gap-2">
            {scoredRows.map((r, i) => (
              <button
                key={i}
                onClick={() => setSelectedIndex(i)}
                className={`rounded-lg px-3 py-1.5 text-sm font-medium ${
                  i === selectedIndex
                    ? "bg-indigo-600 text-white"
                    : "border border-slate-200 bg-white text-slate-600 hover:bg-slate-50"
                }`}
              >
                Response {String.fromCharCode(65 + i)}
              </button>
            ))}
          </div>
        </div>
        <div className="mt-4 grid gap-4 md:grid-cols-2">
          <div className="space-y-3">
            <div className="rounded-lg border border-slate-200 p-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-base font-semibold text-slate-800">
                    Response {String.fromCharCode(65 + selectedIndex)}
                  </h3>
                  <p className="text-sm text-slate-600">Model: {selectedRow.modelName}</p>
                </div>
                <span className="rounded bg-indigo-50 px-2 py-1 text-xs font-medium text-indigo-700">REAL</span>
              </div>
              <p className="mt-3 max-h-80 overflow-auto whitespace-pre-wrap text-sm leading-relaxed text-slate-700">
                {selectedRow.response?.response_text}
              </p>
            </div>
          </div>
          <div className="space-y-3">
            <div className="rounded-lg border border-slate-200 p-4">
              <h3 className="text-sm font-medium text-slate-600">SycAudit Score (Prototype)</h3>
              <p className="mt-1 text-2xl font-bold text-slate-800">{selectedAnalysis.sycophancyScore}/100</p>
              <div className="mt-2">
                <ScoreBar value={selectedAnalysis.sycophancyScore} />
              </div>
              <h3 className="mt-4 text-sm font-medium text-slate-600">Trustworthiness (Prototype)</h3>
              <p className="mt-1 text-2xl font-bold text-slate-800">{selectedAnalysis.trustworthinessScore}/100</p>
              <div className="mt-2">
                <ScoreBar value={selectedAnalysis.trustworthinessScore} />
              </div>
              <p className="mt-4 text-sm text-slate-600">Rank: #{selectedAnalysis.rank + 1} (prototype ranking)</p>
            </div>
          </div>
        </div>
      </section>

      <section className="card p-6">
        <h2 className="text-lg font-semibold text-slate-800">Recommended Response (Prototype)</h2>
        <div className="mt-4 rounded-lg border-2 border-emerald-200 bg-emerald-50 p-5">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-base font-semibold text-slate-800">
                Response {String.fromCharCode(65 + recIdx)}
              </h3>
              <p className="text-sm text-slate-600">Model: {recommendedRow?.modelName}</p>
            </div>
            <span className="rounded bg-white px-2 py-1 text-xs font-medium text-emerald-700">Lowest prototype sycophancy</span>
          </div>
          <p className="mt-3 whitespace-pre-wrap text-sm leading-relaxed text-slate-700">
            {recommendedRow?.response?.response_text}
          </p>
          <div className="mt-4 grid gap-3 sm:grid-cols-2">
            <div>
              <p className="text-sm text-slate-600">SycAudit Score</p>
              <p className="text-lg font-semibold text-slate-800">{recommended.sycophancyScore}/100</p>
            </div>
            <div>
              <p className="text-sm text-slate-600">Trustworthiness</p>
              <p className="text-lg font-semibold text-slate-800">{recommended.trustworthinessScore}/100</p>
            </div>
          </div>
          <p className="mt-3 text-sm text-slate-700">{recommended.recommendationRationale}</p>
          <p className="mt-2 text-xs text-slate-500">Demo — ML grader integration pending</p>
        </div>
      </section>

      <section className="card p-6">
        <h2 className="text-lg font-semibold text-slate-800">Five-Facet Sycophancy Analysis (Prototype)</h2>
        <p className="mt-1 text-sm text-slate-500">Switched by selecting a response above.</p>
        <div className="mt-4 grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {Object.entries(selectedAnalysis.facets).map(([key, f]) => {
            const def = FACET_DEFS_PROTOTYPE[key];
            const pct = f.score * 50;
            return (
              <div key={key} className="rounded-lg border border-slate-200 p-4">
                <div className="flex items-center justify-between">
                  <h3 className="text-base font-semibold text-slate-800">{def.name}</h3>
                  <span className="text-sm font-medium text-slate-600">{def.id}</span>
                </div>
                <p className="mt-1 text-sm text-slate-600">
                  Score: {f.score} — {f.label}
                </p>
                <div className="mt-2 h-2 w-full rounded-full bg-slate-200">
                  <div className="h-2 rounded-full bg-violet-500" style={{ width: `${pct}%` }} />
                </div>
                <p className="mt-3 text-sm leading-relaxed text-slate-700">{f.explanation}</p>
              </div>
            );
          })}
        </div>
      </section>

      <section className="card p-6">
        <h2 className="text-lg font-semibold text-slate-800">Response Analysis Panel (Prototype)</h2>
        <div className="mt-4 grid gap-4 md:grid-cols-2">
          <div className="space-y-3">
            <div className="rounded-lg border border-slate-200 p-4">
              <h3 className="text-sm font-medium text-slate-600">User Cue</h3>
              <p className="mt-2 text-sm leading-relaxed text-slate-700">{selectedAnalysis.detection.userCue}</p>
            </div>
            <div className="rounded-lg border border-slate-200 p-4">
              <h3 className="text-sm font-medium text-slate-600">Model Behavior</h3>
              <p className="mt-2 text-sm leading-relaxed text-slate-700">{selectedAnalysis.detection.modelBehavior}</p>
            </div>
            <div className="rounded-lg border border-slate-200 p-4">
              <h3 className="text-sm font-medium text-slate-600">Facet Detection</h3>
              <p className="mt-2 text-sm text-slate-700">
                {selectedAnalysis.detection.detectedFacets.length
                  ? selectedAnalysis.detection.detectedFacets.map((k) => FACET_DEFS_PROTOTYPE[k].id).join(", ")
                  : "None detected"}
              </p>
            </div>
          </div>
          <div className="space-y-3">
            <div className="rounded-lg border border-slate-200 p-4">
              <h3 className="text-sm font-medium text-slate-600">Severity</h3>
              <p className="mt-2 text-sm text-slate-700">{selectedAnalysis.detection.severity}</p>
            </div>
            <div className="rounded-lg border border-slate-200 p-4">
              <h3 className="text-sm font-medium text-slate-600">Overall Interpretation</h3>
              <p className="mt-2 text-sm font-medium text-slate-800">{selectedAnalysis.overallInterpretation}</p>
            </div>
            <div className="rounded-lg border border-slate-200 p-4">
              <p className="text-xs text-slate-500">Demo — ML grader integration pending</p>
            </div>
          </div>
        </div>
      </section>

      <section className="card p-6">
        <h2 className="text-lg font-semibold text-slate-800">Model Metrics — Frozen Baseline Evaluation</h2>
        <p className="mt-1 text-sm text-slate-500">Real baseline values as specified (frozen).</p>
        <div className="mt-4 grid gap-4 md:grid-cols-2">
          <div className="rounded-lg border border-slate-200 p-4">
            <h3 className="text-sm font-medium text-slate-600">Overall</h3>
            <div className="mt-2 grid grid-cols-2 gap-2 text-sm text-slate-700">
              <p>Accuracy: {PROTOTYPE_BASELINE_METRICS.overall.accuracy}</p>
              <p>Balanced Accuracy: {PROTOTYPE_BASELINE_METRICS.overall.balancedAccuracy}</p>
              <p>Macro Precision: {PROTOTYPE_BASELINE_METRICS.overall.macroPrecision}</p>
              <p>Macro Recall: {PROTOTYPE_BASELINE_METRICS.overall.macroRecall}</p>
              <p>Macro F1: {PROTOTYPE_BASELINE_METRICS.overall.macroF1}</p>
              <p>Weighted F1: {PROTOTYPE_BASELINE_METRICS.overall.weightedF1}</p>
            </div>
          </div>
          <div className="rounded-lg border border-slate-200 p-4">
            <h3 className="text-sm font-medium text-slate-600">Per-facet Macro F1</h3>
            <div className="mt-2 grid grid-cols-2 gap-2 text-sm text-slate-700">
              <p>F1 Excessive Agreement: {PROTOTYPE_BASELINE_METRICS.facetMacroF1.f1}</p>
              <p>F2 Flattery: {PROTOTYPE_BASELINE_METRICS.facetMacroF1.f2}</p>
              <p>F3 Avoiding Disagreement: {PROTOTYPE_BASELINE_METRICS.facetMacroF1.f3}</p>
              <p>F4 Preference Alignment: {PROTOTYPE_BASELINE_METRICS.facetMacroF1.f4}</p>
              <p>F5 Unnecessary Validation: {PROTOTYPE_BASELINE_METRICS.facetMacroF1.f5}</p>
            </div>
          </div>
        </div>
        <div className="mt-4 rounded-lg border border-slate-200 p-4">
          <h3 className="text-sm font-medium text-slate-600">Counts (test set n=489)</h3>
          <div className="mt-2 grid grid-cols-3 gap-2 text-sm text-slate-700">
            <p>At least one facet error: {PROTOTYPE_BASELINE_METRICS.counts.atLeastOneFacetError}/489</p>
            <p>All five facets correct: {PROTOTYPE_BASELINE_METRICS.counts.allFiveFacetsCorrect}/489</p>
            <p>Severe 0↔2 error: {PROTOTYPE_BASELINE_METRICS.counts.severeZeroToTwoError}/489</p>
          </div>
        </div>
      </section>

      <section className="card p-6">
        <h2 className="text-lg font-semibold text-slate-800">Confusion Matrices — Frozen Baseline</h2>
        <p className="mt-1 text-sm text-slate-500">Actual ↓ / Predicted → | 0 = Absent, 1 = Mild, 2 = Strong</p>
        <div className="mt-4 grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {Object.entries(PROTOTYPE_CONFUSION).map(([key, mat]) => (
            <div key={key} className="rounded-lg border border-slate-200 p-4">
<h3 className="text-sm font-medium text-slate-600">{FACET_DEFS_PROTOTYPE[key].id}
</h3>              <table className="mt-2 w-full text-xs text-slate-700">
                <tbody>
                  {mat.map((row, i) => (
                    <tr key={i}>
                      <td className="pr-2 text-slate-500">{i}</td>
                      <td className="px-1">{row[0]}</td>
                      <td className="px-1">{row[1]}</td>
                      <td className="px-1">{row[2]}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}