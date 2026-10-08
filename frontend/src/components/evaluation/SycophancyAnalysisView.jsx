import { useEffect, useMemo, useState } from "react";
import ModelSelect from "../ui/ModelSelect.jsx";
import PageHeader from "../ui/PageHeader.jsx";
import EmptyState from "../ui/EmptyState.jsx";
import ObservationList from "./ObservationList.jsx";
import FacetScoreCard from "./FacetScoreCard.jsx";
import SycophancyGauge from "./SycophancyGauge.jsx";
import {
  BACKEND_SCORE_MAX,
  DISPLAY_SCORE_MAX,
  buildAnalysisSummary,
  buildMatrix,
  collectVariants,
  deriveFacetInsights,
  facetRows,
  responseProvider,
  severityLabel,
  severityLevel,
  toDisplayScore,
} from "../../utils/scoring.js";

/**
 * SYCOPHANCY ANALYSIS — the whole page, for one submission.
 *
 * Layout: header with the model / variant selectors, a two-column card holding
 * the overall score and the summary + observations, the five facet cards, then
 * the response those facets refer to.
 *
 * There is deliberately no navigation in here and no submission list. The
 * sidebar is the only navigation between sections, and History is the only page
 * that lists previous analyses. This component renders whatever submission it is
 * given — the latest completed one, or an older one opened from History — so
 * there is exactly one implementation of the page.
 *
 * Everything shown comes from the stored submission payload. The API returns
 * scores, facet values, response text and a report, and NO reasoning, rationale
 * or evidence text at all. So:
 *   - the summary is arithmetic over the stored facets, labelled "Derived from
 *     facet scores";
 *   - each observation restates one stored facet value, toned by that value;
 *   - every facet card reads "No evidence available." rather than inventing one.
 * Nothing is fabricated to fill a gap, and no score is ever defaulted.
 */
export default function SycophancyAnalysisView({ submission }) {
  const variants = useMemo(() => collectVariants(submission), [submission]);
  const rows = useMemo(() => buildMatrix(submission), [submission]);

  const [model, setModel] = useState(null);
  const [variantKey, setVariantKey] = useState(null);

  // Only models with a stored, scored response can be explained, so the selector
  // offers exactly those. A model that failed is never listed as scorable.
  const scoredModels = useMemo(() => {
    const seen = new Map();
    rows
      .filter((r) => r.scored && r.finalScore !== null)
      .forEach((r) => {
        if (!seen.has(r.modelName)) seen.set(r.modelName, r.provider);
      });
    return Array.from(seen, ([name, provider]) => ({ name, provider }));
  }, [rows]);

  // Variants this model actually scored, in submission order.
  const modelVariants = useMemo(() => {
    const seen = new Map();
    rows
      .filter((r) => r.modelName === model && r.scored && r.finalScore !== null)
      .forEach((r) => {
        if (seen.has(r.variantKey)) return;
        const def = variants.find((v) => v.key === r.variantKey);
        seen.set(r.variantKey, def ?? { key: r.variantKey, label: r.variantLabel });
      });
    return Array.from(seen.values());
  }, [rows, model, variants]);

  // Keep the model selection valid as the payload changes.
  useEffect(() => {
    if (scoredModels.length === 0) return;
    if (!model || !scoredModels.some((m) => m.name === model)) {
      setModel(scoredModels[0].name);
    }
  }, [scoredModels, model]);

  // Keep the variant selection valid for the chosen model.
  useEffect(() => {
    if (modelVariants.length === 0) return;
    if (!variantKey || !modelVariants.some((v) => v.key === variantKey)) {
      setVariantKey(modelVariants[0].key);
    }
  }, [modelVariants, variantKey]);

  const activeVariant = modelVariants.find((v) => v.key === variantKey) ?? null;
  const row = activeVariant
    ? rows.find((r) => r.modelName === model && r.variantKey === activeVariant.key) ?? null
    : null;

  const scored = Boolean(row?.scored && row.finalScore !== null);

  const modelOptions = useMemo(
    () => scoredModels.map((m) => ({ value: m.name, label: m.name })),
    [scoredModels]
  );
  const variantOptions = useMemo(
    () =>
      modelVariants.map((v) => ({
        value: v.key,
        label: v.sublabel && v.sublabel !== v.label ? `${v.label} · ${v.sublabel}` : v.label,
      })),
    [modelVariants]
  );

  const facets = useMemo(() => facetRows(row?.score), [row]);
  const insights = useMemo(() => deriveFacetInsights(row?.score), [row]);
  const summary = useMemo(() => (scored ? buildAnalysisSummary(row?.score) : null), [row, scored]);

  const displayScore = toDisplayScore(row?.finalScore);
  const level = severityLevel(row?.finalScore);
  const bandTone =
    level === "low" ? "text-emerald-700" : level === "mid" ? "text-amber-700" : "text-red-600";

  // A facet recorded at 0 is the only genuinely problem-free state. Anything
  // else is toned by how far up the 0-2 scale it sits, so the checkmark colour
  // can never disagree with the number next to it.
  const observations = insights
    .filter((i) => i.present)
    .map((i) => ({
      id: i.id,
      label: `${i.facetId} · ${i.label}`,
      text: i.text,
      tone: i.value === 0 ? "good" : i.value > BACKEND_SCORE_MAX / 2 ? "bad" : "warn",
    }));

  const noScoredResponse = (
    <EmptyState
      icon="chart"
      title="No scored response available"
      subtitle="This model does not have a completed sycophancy evaluation for this analysis."
    />
  );

  return (
    <>
      <PageHeader
        eyebrow="Sycophancy analysis"
        title="Sycophancy Analysis"
        subtitle="Detailed analysis of sycophantic behavior in the selected response."
        actions={
          scoredModels.length > 0 ? (
            <div className="flex flex-wrap items-center justify-end gap-2">
              <ModelSelect
                options={modelOptions}
                value={model}
                onChange={setModel}
                id="analysis-model"
                label="Model"
              />
              {/* Only shown when the selected model has more than one scored variant. */}
              {variantOptions.length > 1 && (
                <ModelSelect
                  options={variantOptions}
                  value={variantKey}
                  onChange={setVariantKey}
                  id="analysis-variant"
                  label="Variant"
                />
              )}
            </div>
          ) : null
        }
      />

      {/* Which analysis is on screen: context only, never a selector. */}
      {submission?.original_prompt && (
        <p className="mb-5 border-l-2 border-slate-200 pl-3 text-[12.5px] leading-relaxed text-slate-500">
          <span className="font-semibold text-slate-600">Prompt:</span>{" "}
          {submission.original_prompt}
        </p>
      )}

      {scoredModels.length === 0 ? (
        noScoredResponse
      ) : !row ? (
        noScoredResponse
      ) : (
        <>
          {/* Main card: score on the left, summary + observations on the right */}
          <section className="card mb-6 p-5 sm:p-6">
            <div className="grid gap-6 lg:grid-cols-[minmax(0,35fr)_minmax(0,65fr)] lg:gap-8">
              {/* LEFT — overall score */}
              <div className="flex flex-col items-center text-center">
                <h2 className="section-title self-start">Overall Sycophancy Score</h2>

                <p className="mt-3 flex items-baseline gap-1.5">
                  <span className="text-[44px] font-bold leading-none tabular-nums text-slate-900">
                    {displayScore === null ? "N/A" : displayScore.toFixed(1)}
                  </span>
                  <span className="text-[14px] font-medium text-slate-400">
                    /{DISPLAY_SCORE_MAX}
                  </span>
                </p>

                <div className="mt-4">
                  <SycophancyGauge backScore={row.finalScore} />
                </div>

                <p className={`mt-3 text-[13px] font-semibold ${bandTone}`}>
                  {severityLabel(row.finalScore)}
                </p>
                <p className="meta-text mt-1 max-w-[26ch] text-center">
                  {displayScore === null
                    ? "No overall score is stored for this response."
                    : `Overall score ${displayScore.toFixed(1)} of ${DISPLAY_SCORE_MAX}. Lower scores mean less sycophantic.`}
                </p>
              </div>

              {/* RIGHT — summary + observations */}
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <h2 className="section-title">Analysis Summary</h2>
                  <span className="rounded-md bg-surface-200 px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-slate-500">
                    Derived from facet scores
                  </span>
                </div>

                {summary ? (
                  <p className="mt-2.5 text-[13.5px] leading-relaxed text-slate-700">
                    {summary.text}
                  </p>
                ) : (
                  <p className="mt-2.5 text-[12.5px] leading-relaxed text-slate-400">
                    No facet values are stored for this response, so no summary can be derived from
                    them.
                  </p>
                )}

                <div className="mt-5 border-t border-slate-100 pt-4">
                  <h3 className="section-title">Key Observations</h3>
                  <p className="section-sub">
                    One line per facet, restating the value stored for this response.
                  </p>
                  <div className="mt-3">
                    <ObservationList observations={observations} />
                  </div>
                </div>

                <p className="meta-text mt-4">
                  {row.modelName} · {activeVariant?.label} · {responseProvider(row.response)}
                </p>
              </div>
            </div>
          </section>

          {/* Five facets */}
          <section className="mb-6">
            <h2 className="section-title">Sycophancy Facets</h2>
            <p className="section-sub">
              All five facets on the backend&apos;s native 0&ndash;{BACKEND_SCORE_MAX} scale.
            </p>
            <div className="mt-3 grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
              {facets.map((f) => (
                <FacetScoreCard
                  key={f.key}
                  facet={f}
                  value={f.value}
                  present={f.present}
                  note={insights.find((i) => i.id === f.key)?.text}
                />
              ))}
            </div>
          </section>

          {/* The response the facets refer to */}
          <section className="mb-6">
            <h2 className="section-title">Analysed Response</h2>
            <p className="section-sub">The response these five facet scores refer to.</p>
            <div className="card mt-3 p-4 sm:p-5">
              {row.response?.response_text ? (
                <p className="whitespace-pre-wrap text-[13.5px] leading-[1.75] text-slate-800">
                  {row.response.response_text}
                </p>
              ) : (
                <p className="text-[12.5px] text-slate-400">
                  No response text was stored for this model and variant.
                </p>
              )}
            </div>
          </section>
        </>
      )}
    </>
  );
}