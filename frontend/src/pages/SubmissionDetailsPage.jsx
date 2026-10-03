import { useState } from "react";
import { Link } from "react-router-dom";
import { useSubmissionContext } from "../components/layout/SubmissionLayout.jsx";
import SubmissionHeader from "../components/results/SubmissionHeader.jsx";
import PageHeader from "../components/ui/PageHeader.jsx";
import EmptyState from "../components/ui/EmptyState.jsx";
import Notice from "../components/ui/Notice.jsx";
import ScoreReadout from "../components/ui/ScoreReadout.jsx";
import ScoreBadge from "../components/ui/ScoreBadge.jsx";
import FacetBars from "../components/ui/FacetBars.jsx";
import FacetRadar from "../components/ui/FacetRadar.jsx";
import WobbleSection from "../components/results/WobbleSection.jsx";
import Spinner from "../components/ui/Spinner.jsx";
import {
  buildMatrix,
  formatBackScore,
  responseLatencyLabel,
  resolveRecommended,
  toDisplayScore,
  VARIANT_BY_KEY,
} from "../utils/scoring.js";

function PendingBanner({ status }) {
  if (status === "completed") return null;
  const failed = status === "failed";
  return (
    <div className="mb-4">
      <Notice tone={failed ? "danger" : "info"} title={failed ? "This analysis failed" : "Analysis in progress"}>
        {failed
          ? "The backend reported a failed status for this submission. Responses below reflect what was stored, if anything."
          : "Responses and scores appear as each model finishes. This page updates automatically."}
        {!failed && (
          <span className="ml-1.5 inline-flex items-center gap-1.5 text-stone-400">
            <Spinner className="h-3 w-3" />
            updating
          </span>
        )}
      </Notice>
    </div>
  );
}

export default function SubmissionDetailsPage() {
  const { submission } = useSubmissionContext();
  const [showRaw, setShowRaw] = useState(false);

  const rec = resolveRecommended(submission);
  const rows = buildMatrix(submission);
  const scored = rows.filter((r) => r.scored && r.finalScore !== null);
  const others = scored
    .filter((r) => !rec || String(r.response?.response_id) !== String(submission?.report?.recommended_response_id))
    .sort((a, b) => (a.finalScore ?? 0) - (b.finalScore ?? 0));
  const hasReport = submission?.report != null;

  return (
    <div className="animate-fade-up">
      <PageHeader
        eyebrow="Final result"
        title="Sycophancy audit result"
        subtitle="The recommended response is resolved directly from the backend's recommended_response_id. SycAudit does not compute its own winner."
        actions={
          <Link to={`/submissions/${submission?.submission_id}/analysis`} className="btn-secondary !py-2">
            Open full analysis
          </Link>
        }
      />

      <SubmissionHeader submission={submission} />
      <PendingBanner status={submission?.status} />

      {!hasReport && (
        <div className="mb-6">
          <EmptyState
            icon="alert"
            title="No report available for this submission"
            subtitle="The backend returns a report once the analysis completes. Nothing is inferred in the meantime."
          />
        </div>
      )}

      {/* 1 — Least Sycophantic Response */}
      <section className="mb-8">
        <div className="mb-3 flex items-center gap-2">
          <span className="grid h-6 w-6 place-items-center rounded-lg bg-burgundy-700 text-[11px] font-bold text-white">
            1
          </span>
          <h2 className="section-title">Least sycophantic response</h2>
        </div>

        {rec ? (
          <article className="panel overflow-hidden">
            <div className="flex flex-col gap-4 border-b border-stone-100 bg-cream-50 p-5 sm:flex-row sm:items-start sm:justify-between">
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="inline-flex items-center gap-1.5 rounded-lg bg-olive-50 px-2.5 py-1 text-[11.5px] font-bold text-olive-800 ring-1 ring-inset ring-olive-200">
                    <svg
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2.2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      className="h-3.5 w-3.5"
                      aria-hidden="true"
                    >
                      <path d="m5 13 4 4L19 7" />
                    </svg>
                    Recommended · least sycophantic
                  </span>
                  <ScoreBadge backScore={rec.finalScore} />
                </div>
                <p className="mt-2.5 text-[15px] font-semibold text-stone-900">{rec.modelName}</p>
                <p className="mt-0.5 text-[12.5px] text-stone-500">
                  {rec.variantDef
                    ? `${rec.variantDef.label} — ${rec.variantDef.sublabel}`
                    : rec.variantKey ?? "Unknown variant"}
                  {rec.provider ? ` · ${rec.provider}` : ""}
                  {responseLatencyLabel(rec.response) ? ` · ${responseLatencyLabel(rec.response)}` : ""}
                </p>
              </div>

              <div className="shrink-0 sm:text-right">
                <ScoreReadout backScore={rec.finalScore} size="md" caption="Overall score" />
              </div>
            </div>

            <div className="p-5">
              {rec.response?.response_text ? (
                <p className="whitespace-pre-wrap text-[14px] leading-relaxed text-stone-800">
                  {rec.response.response_text}
                </p>
              ) : (
                <p className="text-[13px] text-stone-400">This response has no stored text.</p>
              )}

              {rec.scored && (
                <>
                  <div className="mt-6 grid gap-5 border-t border-stone-100 pt-5 md:grid-cols-[200px_1fr] md:items-center">
                    <div className="hidden md:block">
                      <FacetRadar score={rec.score} finalScore={rec.finalScore ?? 0} height={168} />
                    </div>
                    <div>
                      <FacetBars score={rec.score} />
                    </div>
                  </div>
                  <div className="mt-4 flex flex-wrap items-center gap-x-4 gap-y-2 border-t border-stone-100 pt-3.5 text-[11.5px] text-stone-400">
                    <span>
                      Raw final_score{" "}
                      <span className="font-semibold tabular-nums text-stone-600">
                        {formatBackScore(rec.finalScore)}
                      </span>{" "}
                      / 5
                    </span>
                    {typeof rec.score?.confidence === "number" && (
                      <span>
                        confidence{" "}
                        <span className="font-semibold tabular-nums text-stone-600">
                          {Math.round(rec.score.confidence * 100)}%
                        </span>
                      </span>
                    )}
                    {typeof rec.score?.ml_score === "number" && (
                      <span>
                        ml_score{" "}
                        <span className="font-semibold tabular-nums text-stone-600">
                          {formatBackScore(rec.score.ml_score)}
                        </span>
                      </span>
                    )}
                    {typeof rec.score?.rule_adjustment === "number" && (
                      <span>
                        rule_adjustment{" "}
                        <span className="font-semibold tabular-nums text-stone-600">
                          {rec.score.rule_adjustment > 0 ? "+" : ""}
                          {formatBackScore(rec.score.rule_adjustment)}
                        </span>
                      </span>
                    )}
                  </div>
                </>
              )}
            </div>
          </article>
        ) : (
          <EmptyState
            icon="alert"
            tone="warning"
            title={
              submission?.report?.recommended_response_id == null
                ? "No recommended response yet"
                : "Recommended response could not be resolved"
            }
            subtitle={
              submission?.report?.recommended_response_id == null
                ? "This submission has no recommended_response_id. SycAudit will not pick a different response on your behalf."
                : "The backend returned a recommended_response_id that does not match any stored response in this submission."
            }
          />
        )}
      </section>

      {/* 2 — Other model scores */}
      <section className="mb-8">
        <div className="mb-3 flex items-center gap-2">
          <span className="grid h-6 w-6 place-items-center rounded-lg bg-stone-200 text-[11px] font-bold text-stone-600">
            2
          </span>
          <h2 className="section-title">Other model scores</h2>
          <span className="meta-text ml-1">lower is less sycophantic</span>
        </div>

        {others.length === 0 ? (
          <EmptyState
            compact
            title="No other scored responses"
            subtitle={
              scored.length === 0
                ? "No response in this submission carries a score yet."
                : "The recommended response is the only scored response stored so far."
            }
          />
        ) : (
          <div className="card overflow-hidden">
            <div className="scroll-x">
              <table className="w-full min-w-[520px] border-collapse">
                <thead className="border-b border-stone-100 bg-cream-50">
                  <tr>
                    <th className="table-head">Model</th>
                    <th className="table-head">Variant</th>
                    <th className="table-head text-right">Score / 100</th>
                    <th className="table-head text-right">Raw / 5</th>
                    <th className="table-head">Band</th>
                  </tr>
                </thead>
                <tbody>
                  {others.map((r) => (
                    <tr
                      key={`${r.modelName}-${r.variantKey}-${r.response?.response_id}`}
                      className="border-b border-stone-100 last:border-0 hover:bg-cream-50"
                    >
                      <td className="table-cell font-medium text-stone-800">{r.modelName}</td>
                      <td className="table-cell text-stone-500">
                        {VARIANT_BY_KEY[r.variantKey]?.letter ?? ""}
                        {r.variantSub ? ` · ${r.variantSub}` : r.variantSub}
                      </td>
                      <td className="table-num font-semibold">
                        {toDisplayScore(r.finalScore)?.toFixed(1)}
                      </td>
                      <td className="table-num text-stone-400">{formatBackScore(r.finalScore)}</td>
                      <td className="table-cell">
                        <ScoreBadge backScore={r.finalScore} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {scored.length > 0 && (
          <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
            <button
              type="button"
              onClick={() => setShowRaw((v) => !v)}
              className="text-[11.5px] font-medium text-stone-400 underline decoration-stone-300 underline-offset-2 hover:text-stone-600"
            >
              {showRaw ? "Hide" : "Show"} backend field values
            </button>
            <Link
              to={`/submissions/${submission?.submission_id}/comparison`}
              className="text-[11.5px] font-medium text-burgundy-700 hover:text-burgundy-800"
            >
              Compare models →
            </Link>
          </div>
        )}

        {showRaw && scored.length > 0 && (
          <div className="card mt-3 animate-slide-down p-4">
            <p className="eyebrow">Stored score objects · backend 0–5</p>
            <div className="mt-2.5 space-y-2">
              {scored.map((r) => (
                <div key={`raw-${r.response?.response_id}`} className="text-[11.5px]">
                  <p className="font-semibold text-stone-700">
                    {r.modelName} · {r.variantSub}
                  </p>
                  <p className="mt-0.5 font-mono text-[11px] leading-relaxed text-stone-500">
                    final_score {formatBackScore(r.finalScore)} · facets{" "}
                    {r.score?.facet_scores
                      ? Object.entries(r.score.facet_scores)
                          .map(([k, v]) => `${k}=${formatBackScore(v)}`)
                          .join(", ")
                      : "none stored"}
                  </p>
                </div>
              ))}
            </div>
          </div>
        )}
      </section>

      {/* 3 — Wobble / stability (real backend report, secondary) */}
      <section>
        <div className="mb-3 flex items-center gap-2">
          <span className="grid h-6 w-6 place-items-center rounded-lg bg-stone-200 text-[11px] font-bold text-stone-600">
            3
          </span>
          <h2 className="section-title">Wobble &amp; stability</h2>
        </div>
        <WobbleSection report={submission?.report} />
      </section>
    </div>
  );
}