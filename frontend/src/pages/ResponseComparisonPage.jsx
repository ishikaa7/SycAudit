import { useMemo, useState } from "react";
import { useSubmissionContext } from "../components/layout/SubmissionLayout.jsx";
import PageHeader from "../components/ui/PageHeader.jsx";
import Notice from "../components/ui/Notice.jsx";
import {
  BACKEND_SCORE_MAX,
  FACET_DEFS,
  buildMatrix,
  formatBackScore,
  toDisplayScore,
  severityLabel,
} from "../utils/scoring.js";

function ScoreBar({ value, max = 2 }) {
  const pct = Math.max(0, Math.min(100, (value / max) * 100));
  return (
    <div className="h-2 w-full rounded-full bg-slate-200">
      <div className="h-2 rounded-full bg-indigo-500" style={{ width: `${pct}%` }} />
    </div>
  );
}

export default function ResponseComparisonPage() {
  const { submission } = useSubmissionContext();
  const rows = useMemo(() => buildMatrix(submission), [submission]);

  const scoredRows = useMemo(
    () =>
      rows
        .filter((r) => r.scored && r.finalScore !== null && r.response?.response_text)
        .map((r, idx) => ({
          key: `${r.modelName}::${r.variantKey}::${idx}`,
          modelName: r.modelName,
          variantKey: r.variantKey,
          variantDef: r.variantDef,
          provider: r.provider,
          response: r.response,
          score: r.score || {},
          finalScore: r.finalScore,
          rank: r.rank ?? null,
        })),
    [rows]
  );

  const [selectedIndex, setSelectedIndex] = useState(0);

  if (!submission) {
    return (
      <div className="animate-fade-up">
        <PageHeader eyebrow="Response Analysis" title="Response Analysis" />
        <Notice tone="warning" title="No submission loaded">
          Select an evaluation from History.
        </Notice>
      </div>
    );
  }

  if (scoredRows.length === 0) {
    return (
      <div className="animate-fade-up">
        <PageHeader eyebrow="Response Analysis" title="Response Analysis" />
        <div className="card p-6">
          <h2 className="text-lg font-semibold text-slate-800">Response Variants</h2>
          <p className="mt-2 text-sm text-slate-600">
            No scored responses with text were found for this submission.
          </p>
        </div>
      </div>
    );
  }

  const safeSelectedIdx = selectedIndex >= 0 && selectedIndex < scoredRows.length ? selectedIndex : 0;
  const selectedRow = scoredRows[safeSelectedIdx];
  const selectedFacets = selectedRow.score?.facet_scores || {};
  const selectedWobble = selectedRow.finalScore ?? null;
  const selectedSeverity = selectedWobble !== null ? toDisplayScore(selectedWobble) : null;

  const overallRows = [...scoredRows].sort((a, b) => (a.finalScore ?? 999) - (b.finalScore ?? 999));
  const recommended = overallRows[0];
  const recIdx = scoredRows.findIndex((r) => r.key === recommended.key);

  return (
    <div className="animate-fade-up space-y-6">
      <PageHeader eyebrow="Response Analysis" title="Response Analysis" subtitle="Real responses and real SycAudit evaluation data." />

      <section className="card p-6">
        <h2 className="text-lg font-semibold text-slate-800">Audit Overview</h2>
        <div className="mt-4 grid gap-4 md:grid-cols-2">
          <div>
            <h3 className="text-sm font-medium text-slate-600">Original Prompt</h3>
            <p className="mt-2 whitespace-pre-wrap text-sm leading-relaxed text-slate-800">{submission.original_prompt}</p>
          </div>
          <div className="space-y-2 text-sm text-slate-600">
            <p>Response Variants: {scoredRows.length}</p>
            <p>Models used: {Array.from(new Set(scoredRows.map((r) => r.modelName))).length}</p>
            <p>Audit status: {submission.status}</p>
          </div>
        </div>
      </section>

      <section className="card p-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-lg font-semibold text-slate-800">Response Comparison</h2>
          <div className="flex flex-wrap gap-2">
            {scoredRows.map((r, i) => (
              <button key={r.key} onClick={() => setSelectedIndex(i)} className={`rounded-lg px-3 py-1.5 text-sm font-medium ${i === safeSelectedIdx ? "bg-indigo-600 text-white" : "border border-slate-200 bg-white text-slate-600 hover:bg-slate-50"}`}>
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
                  <h3 className="text-base font-semibold text-slate-800">Response {String.fromCharCode(65 + safeSelectedIdx)}</h3>
                  <p className="text-sm text-slate-600">Model: {selectedRow.modelName}</p>
                  {selectedRow.provider && <p className="text-sm text-slate-500">Provider: {selectedRow.provider}</p>}
                </div>
                <span className="rounded bg-indigo-50 px-2 py-1 text-xs font-medium text-indigo-700">REAL</span>
              </div>
              <p className="mt-3 max-h-96 overflow-auto whitespace-pre-wrap text-sm leading-relaxed text-slate-700">{selectedRow.response?.response_text}</p>
            </div>
          </div>

          <div className="space-y-3">
            <div className="rounded-lg border border-slate-200 p-4">
              <h3 className="text-sm font-medium text-slate-600">SycAudit Analysis</h3>
              <p className="mt-1 text-xl font-semibold text-slate-800">WOBBLE: {selectedWobble !== null ? formatBackScore(selectedWobble) : "N/A"} / {BACKEND_SCORE_MAX}</p>
              <div className="mt-2"><ScoreBar value={selectedWobble ?? 0} /></div>
              <p className="mt-3 text-sm text-slate-600">Detected sycophancy severity: {selectedSeverity !== null ? `${selectedSeverity.toFixed(1)}%` : "N/A"}</p>
              <p className="mt-2 text-sm text-slate-600">Rank: {selectedRow.rank != null ? `#${selectedRow.rank}` : "N/A"}</p>
              <div className="mt-4">
                <h4 className="text-sm font-medium text-slate-600">Facet Analysis</h4>
                <div className="mt-2 space-y-2">
                  {FACET_DEFS.map((f) => {
                    const val = selectedFacets[f.key];
                    return (
                      <div key={f.key} className="flex items-center justify-between text-sm">
                        <span className="text-slate-700">{f.id} — {f.label}</span>
                        <span className="font-medium text-slate-800">{val !== null && val !== undefined ? val : "N/A"} / {BACKEND_SCORE_MAX}</span>
                      </div>
                    );
                  })}
                </div>
              </div>
              <div className="mt-4">
                <h4 className="text-sm font-medium text-slate-600">Evidence / Explanation</h4>
                <p className="mt-1 text-sm text-slate-500">Not provided by API for this response</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {recommended && (
        <section className="card p-6">
          <h2 className="text-lg font-semibold text-slate-800">Recommended Response</h2>
          <div className="mt-4 rounded-lg border-2 border-emerald-200 bg-emerald-50 p-5">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <h3 className="text-base font-semibold text-slate-800">Response {String.fromCharCode(65 + recIdx)}</h3>
                <p className="text-sm text-slate-600">Model: {recommended.modelName}</p>
              </div>
              <span className="rounded bg-white px-2 py-1 text-xs font-medium text-emerald-700">Lowest detected sycophancy</span>
            </div>
            <p className="mt-3 whitespace-pre-wrap text-sm leading-relaxed text-slate-700">{recommended.response?.response_text}</p>
            <div className="mt-4 grid gap-3 sm:grid-cols-2">
              <div>
                <p className="text-sm text-slate-600">WOBBLE</p>
                <p className="text-lg font-semibold text-slate-800">{recommended.finalScore !== null ? formatBackScore(recommended.finalScore) : "N/A"} / {BACKEND_SCORE_MAX}</p>
              </div>
              <div>
                <p className="text-sm text-slate-600">Detected sycophancy severity</p>
                <p className="text-lg font-semibold text-slate-800">{recommended.finalScore !== null ? `${toDisplayScore(recommended.finalScore).toFixed(1)}%` : "N/A"}</p>
              </div>
            </div>
          </div>
        </section>
      )}

      <section className="card p-6">
        <h2 className="text-lg font-semibold text-slate-800">Five-Facet Sycophancy Analysis</h2>
        <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
          {FACET_DEFS.map((f) => {
            const val = selectedFacets[f.key];
            return (
              <div key={f.key} className="rounded-lg border border-slate-200 p-4">
                <h3 className="text-sm font-semibold text-slate-800">{f.id}</h3>
                <p className="text-sm text-slate-600">{f.label}</p>
                <p className="mt-2 text-xl font-semibold text-slate-800">{val !== null && val !== undefined ? val : "N/A"} / {BACKEND_SCORE_MAX}</p>
                <p className="mt-2 text-xs text-slate-500">Explanation not available for this evaluation.</p>
              </div>
            );
          })}
        </div>
      </section>

      <section className="card p-6">
        <h2 className="text-lg font-semibold text-slate-800">Response Analysis Panel</h2>
        <p className="mt-2 text-sm text-slate-600">Evidence not available for this evaluation.</p>
      </section>
    </div>
  );
}
