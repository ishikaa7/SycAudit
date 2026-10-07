import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useSubmissionContext } from "../components/layout/SubmissionLayout.jsx";
import SubmissionHeader from "../components/results/SubmissionHeader.jsx";
import VariantResponseCard from "../components/evaluation/VariantResponseCard.jsx";
import PageHeader from "../components/ui/PageHeader.jsx";
import EmptyState from "../components/ui/EmptyState.jsx";
import ScoreBadge from "../components/ui/ScoreBadge.jsx";
import ScoreReadout from "../components/ui/ScoreReadout.jsx";
import FacetRadar from "../components/ui/FacetRadar.jsx";
import FacetBars from "../components/ui/FacetBars.jsx";
import WobbleSection from "../components/results/WobbleSection.jsx";
import {
  buildMatrix,
  collectModels,
  collectVariants,
  formatBackScore,
  responseLatencyLabel,
  resolveRecommended,
  scoreHex,
  toDisplayScore,
} from "../utils/scoring.js";

/** Pending / failed banner, shown above the result sections. */
function PendingBanner({ status }) {
  if (status === "failed") {
    return (
      <div className="mb-6 rounded-xl border border-indigo-200 bg-indigo-50 px-4 py-3">
        <p className="text-[13px] font-semibold text-indigo-900">This analysis failed</p>
        <p className="mt-0.5 text-[12.5px] text-indigo-800">
          The backend recorded this run as failed. No report is expected for it.
        </p>
      </div>
    );
  }
  if (status === "pending" || status === "processing") {
    return (
      <div className="mb-6 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3">
        <p className="text-[13px] font-semibold text-amber-900">Analysis in progress</p>
        <p className="mt-0.5 text-[12.5px] text-slate-600">
          The backend is still generating variants, responses and scores. This page updates
          automatically.
        </p>
      </div>
    );
  }
  return null;
}

/**
 * Results: the response-selection page.
 *
 * A. the least sycophantic response (resolved only from the backend's
 *    recommended_response_id)
 * B. every other evaluated model with its real stored score
 * C. a variant selector that switches between variants without leaving the page
 *
 * Nothing on this page is hardcoded: no model names, scores, facet values or
 * response text.
 */
export default function SubmissionDetailsPage() {
  const { submission } = useSubmissionContext();
  const [activeVariant, setActiveVariant] = useState(null);

  const rec = resolveRecommended(submission);
  const rows = useMemo(() => buildMatrix(submission), [submission]);
  const variants = useMemo(() => collectVariants(submission), [submission]);
  const models = useMemo(() => collectModels(submission), [submission]);

  const scored = rows.filter((r) => r.scored && r.finalScore !== null);
  const recId = submission?.report?.recommended_response_id ?? null;

  const others = scored
    .filter((r) => String(r.response?.response_id) !== String(recId))
    .sort((a, b) => (a.finalScore ?? 0) - (b.finalScore ?? 0));

  // Models with no score still deserve to appear, as an explicit N/A.
  const unscoredModels = models.filter(
    (m) => !scored.some((r) => r.modelName === m.name)
  );

  const shownVariants = useMemo(
    () => (activeVariant ? variants.filter((v) => v.key === activeVariant) : variants),
    [variants, activeVariant]
  );

  const hasReport = submission?.report != null;

  return (
    <div className="animate-fade-up">
      <PageHeader
        eyebrow="Final result"
        title="Sycophancy Evaluation"
        subtitle="The recommended response is resolved directly from the backend's recommended_response_id. SycAudit does not compute its own winner."
        actions={
          <Link to={`/submissions/${submission?.submission_id}/analysis`} className="btn-secondary !py-2">
            Why this score?
          </Link>
        }
      />

      <SubmissionHeader submission={submission} />
      <PendingBanner status={submission?.status} />

      {!hasReport ? (
        /* One coherent empty state. No report-dependent section renders below. */
        <div className="mb-6">
          <EmptyState
            icon="alert"
            title="No report available for this submission"
            subtitle={
              submission?.status === "completed"
                ? "The backend stored no report for this run, so no recommendation, score summary or stability figure can be shown. Every stored response is still listed below."
                : "The backend returns a report once the analysis completes. Nothing is inferred in the meantime."
            }
            action={
              <Link to={`/submissions/${submission?.submission_id}/comparison`} className="btn-secondary">
                Compare models
              </Link>
            }
          />
        </div>
      ) : (
        <>
          {/* A — Least Sycophantic Response */}
          <section className="mb-8">
            <div className="mb-3 flex items-center gap-2">
              <span className="grid h-6 w-6 place-items-center rounded-lg bg-indigo-600 text-[11px] font-bold text-white">
                A
              </span>
              <h2 className="section-title">Least Sycophantic Response</h2>
            </div>

            {rec ? (
              <article className="panel overflow-hidden">
                <div className="flex flex-col gap-4 border-b border-slate-100 bg-surface-50 p-5 sm:flex-row sm:items-start sm:justify-between">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="inline-flex items-center gap-1.5 rounded-lg bg-emerald-50 px-2.5 py-1 text-[11.5px] font-bold text-emerald-800 ring-1 ring-inset ring-emerald-200">
                        Backend recommended · least sycophantic
                      </span>
                      <ScoreBadge backScore={rec.finalScore} />
                    </div>
                    <p className="mt-2.5 text-[15px] font-semibold text-slate-900">{rec.modelName}</p>
                    <p className="mt-0.5 text-[12.5px] text-slate-500">
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
                    <p className="whitespace-pre-wrap text-[14px] leading-relaxed text-slate-800">
                      {rec.response.response_text}
                    </p>
                  ) : (
                    <p className="text-[13px] text-slate-400">This response has no stored text.</p>
                  )}

                  {rec.scored && (
                    <>
                      <div className="mt-6 grid gap-5 border-t border-slate-100 pt-5 md:grid-cols-[200px_1fr] md:items-center">
                        <div className="hidden md:block">
                          <FacetRadar score={rec.score} finalScore={rec.finalScore ?? 0} height={168} />
                        </div>
                        <div>
                          <FacetBars score={rec.score} />
                        </div>
                      </div>
                      <p className="mt-3.5 border-t border-slate-100 pt-3.5 text-[11.5px] text-slate-400">
                        Raw final_score {formatBackScore(rec.finalScore)} / 5
                      </p>
                    </>
                  )}

                  <div className="mt-4 flex flex-wrap items-center gap-3 border-t border-slate-100 pt-4">
                    <Link
                      to={`/submissions/${submission?.submission_id}/analysis`}
                      className="btn-secondary !py-2"
                    >
                      View details
                    </Link>
                    <Link
                      to={`/submissions/${submission?.submission_id}/comparison`}
                      className="text-[11.5px] font-medium text-indigo-700 hover:text-indigo-800"
                    >
                      Compare all models →
                    </Link>
                  </div>
                </div>
              </article>
            ) : (
              <EmptyState
                icon="alert"
                tone="warning"
                title={
                  recId == null
                    ? "No recommended response yet"
                    : "Recommended response could not be resolved"
                }
                subtitle={
                  recId == null
                    ? "This submission has no recommended_response_id. SycAudit will not pick a different response on your behalf."
                    : "The backend returned a recommended_response_id that does not match any stored response in this submission."
                }
              />
            )}
          </section>
        </>
      )}

      {/* B — Other model scores */}
      <section className="mb-8">
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <span className="grid h-6 w-6 place-items-center rounded-lg bg-slate-200 text-[11px] font-bold text-slate-600">
              B
            </span>
            <h2 className="section-title">Other model scores</h2>
          </div>
          <p className="meta-text">lower score = less sycophantic</p>
        </div>

        {others.length === 0 && unscoredModels.length === 0 ? (
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
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
            {others.map((r) => (
              <article key={`card-${r.response?.response_id}`} className="card p-4">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="truncate text-[13.5px] font-semibold text-slate-900" title={r.modelName}>
                      {r.modelName}
                    </p>
                    <p className="meta-text mt-0.5 truncate">
                      {r.variantLabel}
                      {r.variantSub ? ` · ${r.variantSub}` : ""}
                    </p>
                  </div>
                  <div className="shrink-0 text-right">
                    <p
                      className="text-2xl font-bold leading-none tabular-nums"
                      style={{ color: scoreHex(r.finalScore) }}
                    >
                      {toDisplayScore(r.finalScore).toFixed(1)}
                    </p>
                    <p className="meta-text mt-1">/ 100</p>
                  </div>
                </div>
                <div className="mt-2.5 flex items-center justify-between gap-2">
                  <ScoreBadge backScore={r.finalScore} />
                  <span className="text-[10.5px] tabular-nums text-slate-400">
                    raw {formatBackScore(r.finalScore)} / 5
                  </span>
                </div>
                <div className="mt-3">
                  <FacetBars score={r.score} />
                </div>
              </article>
            ))}

            {unscoredModels.map((m) => (
              <article key={`unscored-${m.name}`} className="card border-dashed p-4">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="truncate text-[13.5px] font-semibold text-slate-600" title={m.name}>
                      {m.name}
                    </p>
                    <p className="meta-text mt-0.5">{m.provider ?? "unknown provider"}</p>
                  </div>
                  <div className="shrink-0 text-right">
                    <p className="text-2xl font-bold leading-none tabular-nums text-slate-300">N/A</p>
                    <p className="meta-text mt-1">/ 100</p>
                  </div>
                </div>
                <p className="mt-3 text-[11.5px] leading-relaxed text-slate-400">
                  No score is stored for this model in this run.
                </p>
              </article>
            ))}
          </div>
        )}

        {scored.length > 0 && (
          <div className="mt-3">
            <Link
              to={`/submissions/${submission?.submission_id}/comparison`}
              className="text-[11.5px] font-medium text-indigo-700 hover:text-indigo-800"
            >
              Compare models →
            </Link>
          </div>
        )}
      </section>

      {/* C — Variant / response exploration, without leaving the page */}
      <section className="mb-8">
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <span className="grid h-6 w-6 place-items-center rounded-lg bg-slate-200 text-[11px] font-bold text-slate-600">
              C
            </span>
            <h2 className="section-title">All generated responses</h2>
          </div>
          <p className="meta-text">
            {variants.length} variant{variants.length === 1 ? "" : "s"} · {models.length} model
            {models.length === 1 ? "" : "s"}
          </p>
        </div>

        {variants.length === 0 ? (
          <EmptyState
            compact
            icon="doc"
            title="No prompt variants stored"
            subtitle="The backend returned no variants for this submission."
          />
        ) : (
          <>
            <div className="mb-4 flex flex-wrap gap-2" role="group" aria-label="Filter by prompt variant">
              {variants.map((v) => (
                <button
                  key={v.key}
                  type="button"
                  aria-pressed={activeVariant === v.key}
                  onClick={() => setActiveVariant(activeVariant === v.key ? null : v.key)}
                  className={`rounded-lg px-3 py-1.5 text-[12.5px] font-semibold transition-colors ${
                    activeVariant === v.key
                      ? "bg-indigo-600 text-white"
                      : "border border-slate-200 bg-white text-slate-600 hover:bg-surface-50"
                  }`}
                >
                  {v.label}
                  {v.sublabel && v.sublabel !== v.label ? ` · ${v.sublabel}` : ""}
                </button>
              ))}
            </div>

            {activeVariant === null && (
              <p className="mb-3 text-[11.5px] text-slate-400">
                Showing every variant. Select one above to focus on it.
              </p>
            )}

            {shownVariants.map((v) => {
              const vRows = rows.filter((r) => r.variantKey === v.key);
              return (
                <div key={v.key} className="mb-6 last:mb-0">
                  <div className="mb-3 flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 pb-2">
                    <h3 className="text-[14px] font-semibold text-slate-900">
                      {v.label}
                      {v.sublabel && v.sublabel !== v.label ? ` · ${v.sublabel}` : ""}
                    </h3>
                    <span className="meta-text">
                      {vRows.length} response{vRows.length === 1 ? "" : "s"}
                    </span>
                  </div>

                  {vRows.length === 0 ? (
                    <p className="text-[12.5px] text-slate-400">
                      No model responses were stored for this variant.
                    </p>
                  ) : (
                    <div className="grid gap-4 xl:grid-cols-2">
                      {vRows.map((r) => (
                        <VariantResponseCard
                          key={`${r.modelName}-${r.variantKey}-${r.response?.response_id}`}
                          row={r}
                          isRecommended={
                            r.response?.response_id != null &&
                            String(r.response.response_id) === String(recId)
                          }
                        />
                      ))}
                    </div>
                  )}
                </div>
              );
            })}
          </>
        )}
      </section>

      {/* Wobble, when the backend stored a report */}
      {hasReport && (
        <section>
          <div className="mb-3 flex items-center gap-2">
            <span className="grid h-6 w-6 place-items-center rounded-lg bg-slate-200 text-[11px] font-bold text-slate-600">
              D
            </span>
            <h2 className="section-title">Wobble &amp; stability</h2>
          </div>
          <WobbleSection report={submission?.report} />
        </section>
      )}
    </div>
  );
}