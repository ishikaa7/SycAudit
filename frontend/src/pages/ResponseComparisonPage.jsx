import { useMemo, useState } from "react";
import { useSubmissionContext } from "../components/layout/SubmissionLayout.jsx";
import PageHeader from "../components/ui/PageHeader.jsx";
import EmptyState from "../components/ui/EmptyState.jsx";
import Notice from "../components/ui/Notice.jsx";
import {
  BACKEND_SCORE_MAX,
  FACET_DEFS,
  collectVariants,
  buildMatrix,
  formatBackScore,
  toDisplayScore,
  severityLabel,
  responseProvider,
} from "../utils/scoring.js";

function ResponseText({ text }) {
  if (!text) {
    return <p className="text-[13px] text-slate-400">No response text available.</p>;
  }
  return (
    <p className="whitespace-pre-wrap text-[14px] leading-relaxed text-slate-800">
      {text}
    </p>
  );
}

export default function ResponseComparisonPage() {
  const { submission } = useSubmissionContext();
  const variants = useMemo(() => collectVariants(submission), [submission]);
  const rows = useMemo(() => buildMatrix(submission), [submission]);

  const scoredRows = useMemo(
    () =>
      rows
        .filter((r) => r.scored && r.finalScore !== null && r.response?.response_text)
        .map((r) => ({
          key: `${r.modelName}::${r.variantKey}`,
          modelName: r.modelName,
          variantKey: r.variantKey,
          variantDef: r.variantDef,
          provider: r.provider || responseProvider(r.modelName, r.variantKey),
          response: r.response,
          score: r.score || {},
          finalScore: r.finalScore,
          rank: r.rank ?? null,
        })),
    [rows]
  );

  const [selectedIdx, setSelectedIdx] = useState(0);

  if (!submission) {
    return (
      <div className="animate-fade-up">
        <PageHeader eyebrow="Response Comparison" title="Response Comparison" />
        <Notice tone="warning" title="No submission loaded">
          Select an evaluation from History.
        </Notice>
      </div>
    );
  }

  if (scoredRows.length === 0) {
    return (
      <div className="animate-fade-up">
        <PageHeader eyebrow="Response Comparison" title="Response Comparison" />
        <EmptyState
          icon="alert"
          title="No comparable responses"
          subtitle="No scored responses with text are available for this evaluation."
        />
      </div>
    );
  }

  if (selectedIdx >= scoredRows.length || selectedIdx < 0) {
    setSelectedIdx(0);
  }

  const selected = scoredRows[selectedIdx];
  const facets = selected.score?.facet_scores || {};

  const wobble = selected.finalScore ?? null;
  const severityDisp = wobble !== null ? toDisplayScore(wobble) : null;
  const severityLbl = wobble !== null ? severityLabel(wobble) : null;

  return (
    <div className="animate-fade-up">
      <PageHeader
        eyebrow="Response Comparison"
        title="Response Comparison"
        subtitle="Compare actual generated responses and their real SycAudit evaluation."
      />

      <div className="mb-6">
        <div className="card p-3">
          <div className="flex gap-2 overflow-x-auto pb-1">
            {scoredRows.map((r, idx) => {
              const label = r.variantDef?.label || r.variantKey || `Response ${idx + 1}`;
              const isSel = idx === selectedIdx;
              return (
                <button
                  key={r.key}
                  type="button"
                  onClick={() => setSelectedIdx(idx)}
                  className={`shrink-0 rounded-lg px-3 py-1.5 text-[12px] font-semibold transition-colors ${
                    isSel
                      ? "bg-indigo-600 text-white shadow-sm"
                      : "bg-slate-100 text-slate-700 hover:bg-slate-200"
                  }`}
                >
                  {label}
                </button>
              );
            })}
          </div>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-[1fr_1fr]">
        <section className="card overflow-hidden">
          <div className="border-b border-slate-100 bg-surface-50 p-5">
            <p className="text-[12px] font-semibold uppercase tracking-wide text-slate-500">
              Selected response
            </p>
            <p className="mt-1 text-[16px] font-semibold text-slate-900">
              {selected.variantDef?.label || selected.variantKey || "Response"}
            </p>
            <p className="mt-1.5 text-[12.5px] text-slate-500">
              {selected.modelName}
              {selected.provider ? ` · ${selected.provider}` : ""}
            </p>
          </div>
          <div className="max-h-[500px] overflow-auto p-5">
            <ResponseText text={selected.response?.response_text} />
          </div>
        </section>

        <section className="card overflow-hidden">
          <div className="border-b border-slate-100 bg-surface-50 p-5">
            <h2 className="text-[16px] font-semibold text-slate-900">SycAudit Analysis</h2>
          </div>
          <div className="p-5 space-y-5">
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="rounded-lg border border-slate-200 p-3">
                <p className="text-[11.5px] font-semibold uppercase tracking-wide text-slate-500">
                  WOBBLE
                </p>
                <p className="mt-1 text-[20px] font-semibold tabular-nums text-slate-900">
                  {wobble !== null ? formatBackScore(wobble) : "Unavailable"}{" "}
                  <span className="text-[13px] text-slate-500">/ {BACKEND_SCORE_MAX}</span>
                </p>
                <p className="mt-0.5 text-[11.5px] text-slate-400">
                  (F1+F2+F3+F4+F5)/5
                </p>
              </div>
              <div className="rounded-lg border border-slate-200 p-3">
                <p className="text-[11.5px] font-semibold uppercase tracking-wide text-slate-500">
                  Detected sycophancy severity
                </p>
                <p className="mt-1 text-[20px] font-semibold text-slate-900">
                  {severityDisp !== null ? severityDisp.toFixed(1) : "Unavailable"}
                  <span className="text-[13px] text-slate-500">%</span>
                </p>
                {severityLbl && (
                  <p className="mt-0.5 text-[11.5px] text-slate-500">{severityLbl}</p>
                )}
              </div>
            </div>

            <div className="rounded-lg border border-slate-200 p-3">
              <p className="text-[11.5px] font-semibold uppercase tracking-wide text-slate-500">
                Rank
              </p>
              <p className="mt-1 text-[16px] font-semibold text-slate-900">
                {selected.rank != null ? `#${selected.rank}` : "Unavailable"}
              </p>
              {scoredRows.length > 1 && (
                <p className="mt-0.5 text-[11.5px] text-slate-400">
                  Among {scoredRows.length} comparable responses (lower WOBBLE is better)
                </p>
              )}
            </div>

            <div>
              <p className="text-[12px] font-semibold uppercase tracking-wide text-slate-500">
                Facet Analysis
              </p>
              <div className="mt-2 space-y-2">
                {FACET_DEFS.map((f) => {
                  const key = f.key;
                  const val = facets[key];
                  return (
                    <div
                      key={key}
                      className="flex items-center justify-between rounded-lg border border-slate-100 px-3 py-2"
                    >
                      <div>
                        <p className="text-[13px] font-medium text-slate-800">
                          {f.id} — {f.label}
                        </p>
                      </div>
                      <p className="text-[13px] tabular-nums text-slate-800">
                        {val !== null && val !== undefined ? val : "N/A"} / {BACKEND_SCORE_MAX}
                      </p>
                    </div>
                  );
                })}
              </div>
            </div>

            <div>
              <p className="text-[12px] font-semibold uppercase tracking-wide text-slate-500">
                Evidence / Explanation
              </p>
              <p className="mt-1 text-[12.5px] text-slate-400">
                Not provided by API for this response
              </p>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
