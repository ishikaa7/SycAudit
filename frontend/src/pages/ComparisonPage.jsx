import { useMemo } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  LabelList,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { useSubmissionContext } from "../components/layout/SubmissionLayout.jsx";
import SubmissionHeader from "../components/results/SubmissionHeader.jsx";
import FacetGroupedChart from "../components/results/FacetGroupedChart.jsx";
import ModelFacetHeatmap from "../components/evaluation/ModelFacetHeatmap.jsx";
import PageHeader from "../components/ui/PageHeader.jsx";
import EmptyState from "../components/ui/EmptyState.jsx";
import Notice from "../components/ui/Notice.jsx";
import {
  BACKEND_SCORE_MAX,
  DISPLAY_SCORE_MAX,
  FACET_DEFS,
  PALETTE,
  formatBackScore,
  buildModelColorMap,
  modelColor,
  normalizeComparisonData,
} from "../utils/scoring.js";

/**
 * MODEL COMPARISON DASHBOARD — scoped to ONE submission.
 *
 * The page answers a single question: how do the different models behave when
 * answering the SAME user prompt across all generated variants?
 *
 * It is deliberately model-centric and submission-scoped. Models are only
 * comparable inside one run, because each run sends the same prompt to every
 * model; mixing prompts across runs would not be like-for-like. So this page
 * never lists historical submissions and never aggregates across them. The
 * landing page picks the run, the route supplies its id, and everything below
 * is derived from that one payload.
 *
 * DATA SOURCE
 * `/submissions/:id/comparison` is a frontend route, not an API endpoint. The
 * submission is fetched once by SubmissionLayout via the existing
 * GET /submissions/{id}; `normalizeComparisonData` is a pure, frontend-only
 * read of that payload. No endpoint, schema or backend file is touched.
 *
 * MISSING DATA IS NEVER ZERO. Every score and facet the backend did not store
 * stays null and renders as "N/A" or an omitted bar, never a zero-height one.
 */

const FACET_IDS = FACET_DEFS.map((f) => f.id);

/** Shared tooltip for the 0-100 display-scale charts. */
function ScoreTooltip({ active, payload, label, unitMax }) {
  if (!active || !payload || payload.length === 0) return null;
  return (
    <div className="rounded-xl border border-slate-200 bg-white px-3 py-2.5 shadow-panel">
      <p className="mb-1.5 text-[12px] font-semibold text-slate-800">{label}</p>
      <div className="space-y-1">
        {payload.map((p) => (
          <div key={p.dataKey} className="flex items-center gap-2 text-[11.5px]">
            <span className="h-2 w-2 rounded-full" style={{ backgroundColor: p.color }} />
            <span className="min-w-0 flex-1 truncate text-slate-600">{p.dataKey}</span>
            <span className="shrink-0 font-semibold tabular-nums text-slate-800">
              {p.value == null ? "N/A" : Number(p.value).toFixed(2)}
            </span>
          </div>
        ))}
        <p className="pt-0.5 text-[10.5px] text-slate-400">on a 0–{unitMax} scale</p>
      </div>
    </div>
  );
}

/** One chart card. Titles match the dashboard's section order. */
function ChartFrame({ title, caption, children, footnote, note }) {
  return (
    <section className="card mb-6 p-5">
      <div className="mb-3 flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="section-title">{title}</h2>
        {caption && <p className="meta-text">{caption}</p>}
      </div>
      {children}
      {note && <p className="meta-text mt-3">{note}</p>}
      {footnote && <p className="meta-text mt-1.5">{footnote}</p>}
    </section>
  );
}

/** Placeholder frames so the dashboard never flashes empty charts. */
function ComparisonSkeleton() {
  return (
    <div aria-busy="true" aria-label="Loading comparison">
      <div className="card mb-6 animate-pulse p-5">
        <div className="h-3 w-28 rounded bg-surface-200" />
        <div className="mt-3 h-4 w-full rounded bg-surface-200" />
      </div>
      {[300, 320, 280].map((h, i) => (
        <div key={i} className="card mb-6 animate-pulse p-5">
          <div className="h-3 w-40 rounded bg-surface-200" />
          <div className="mt-4 rounded bg-surface-200" style={{ height: h }} />
        </div>
      ))}
    </div>
  );
}

/** "N/A" when the backend stored nothing; a plain dash otherwise is never used for 0. */
function Score({ value, digits = 1, suffix = "" }) {
  if (value == null || !Number.isFinite(value)) {
    return <span className="text-slate-300">N/A</span>;
  }
  return (
    <span className="tabular-nums text-slate-800">
      {value.toFixed(digits)}
      {suffix}
    </span>
  );
}

/** True only when at least one f1..f5 slot holds a real number. */
function hasFacetValue(facets) {
  return Object.values(facets).some((v) => v !== null && v !== undefined);
}

export default function ComparisonPage() {
  const { submission, refresh } = useSubmissionContext();

  const data = useMemo(() => normalizeComparisonData(submission), [submission]);

  // One colour per model for the WHOLE page, resolved once. The same model is
  // therefore the same colour in every chart, the table, the legends and the
  // variant details, and no two models share a colour.
  const colorOf = useMemo(() => {
    const roster = data.models.map((m) => m.name);
    const map = buildModelColorMap(roster);
    return (name) => map.get(String(name)) ?? modelColor(name, roster);
  }, [data.models]);

  // OVERALL — one horizontal bar per model, mean of its variant scores.
  const overallChart = useMemo(
    () =>
      data.models
        .filter((m) => m.overallDisplay !== null)
        .slice()
        .sort((a, b) => (a.overallBack ?? 0) - (b.overallBack ?? 0))
        .map((m) => ({
          name: m.name,
          display: m.overallDisplay,
          back: m.overallBack,
          scoredCount: m.scoredCount,
        })),
    [data.models]
  );

  // MODEL x VARIANT — grouped bars, one series per model. Built from whatever
  // variants the payload contains; no fixed count is assumed.
  const variantChart = useMemo(
    () =>
      data.variants.map((v) => {
        const entry = { variant: v.label, variantKey: v.key };
        data.models.forEach((m) => {
          const cell = m.variants.find((x) => x.key === v.key);
          entry[m.name] = cell?.scoreDisplay ?? null;
        });
        return entry;
      }),
    [data.variants, data.models]
  );

  // FACET PERFORMANCE — five canonical facets on the X axis, one bar per model.
  const facetChart = useMemo(
    () =>
      FACET_DEFS.map((f) => {
        const entry = { facet: f.id, label: f.id, key: f.key };
        data.models.forEach((m) => {
          const v = m.facets[f.id.toLowerCase()];
          if (v !== null && v !== undefined) entry[m.name] = v;
        });
        return entry;
      }).filter((entry) => data.models.some((m) => entry[m.name] !== undefined)),
    [data.models]
  );

  // FACET x MODEL heatmap rows.
  const heatmapRows = useMemo(
    () =>
      data.models.map((m) => ({
        name: m.name,
        meanBack: m.overallBack,
        meanDisplay: m.overallDisplay,
        scoredCount: m.scoredCount,
        cells: FACET_DEFS.map((f) => ({
          key: f.key,
          id: f.id,
          label: f.label,
          value: m.facets[f.id.toLowerCase()] ?? null,
        })),
      })),
    [data.models]
  );

  const tableRows = data.models.filter((m) => m.overallBack !== null || hasFacetValue(m.facets));

  const variantGroups = useMemo(
    () =>
      data.variants.map((v) => ({
        ...v,
        entries: data.models
          .map((m) => ({ model: m.name, cell: m.variants.find((x) => x.key === v.key) }))
          .filter((e) => e.cell),
      })),
    [data.variants, data.models]
  );

  // SubmissionLayout owns the fetch, so a null submission means there is
  // nothing to render yet. Show the skeleton rather than an empty chart.
  if (!submission) return <ComparisonSkeleton />;

  return (
    <div className="animate-fade-up">
      <PageHeader
        eyebrow="Model comparison"
        title="Model Comparison"
        subtitle="Same user prompt • All generated variants"
      />

      <SubmissionHeader submission={submission} />

      {/* 1 — USER PROMPT */}
      <section className="card mb-6 p-5">
        <p className="eyebrow">User prompt</p>
        <p className="mt-2 whitespace-pre-wrap text-[15px] leading-relaxed text-slate-800">
          {data.prompt ?? "No prompt stored for this analysis."}
        </p>
        <p className="meta-text mt-3">
          Same prompt evaluated across all generated variants ·{" "}
          {data.models.length} model{data.models.length === 1 ? "" : "s"} ·{" "}
          {data.variants.length} variant{data.variants.length === 1 ? "" : "s"} · lower score =
          less sycophantic
        </p>
      </section>

      {data.models.length === 0 || data.variants.length === 0 ? (
        <EmptyState
          icon="chart"
          title="No comparison data available for this analysis."
          subtitle="This run stored no models or no prompt variants, so there is nothing to compare. Response text and scores live under Results."
          action={
            <button type="button" onClick={refresh} className="btn-secondary !py-2">
              Refresh this analysis
            </button>
          }
        />
      ) : !data.hasScores ? (
        <EmptyState
          icon="alert"
          tone="warning"
          title="Insufficient evaluation data"
          subtitle="Models and variants exist for this run, but no stored response carries a score. Charts are left empty rather than drawn as zero."
          action={
            <button type="button" onClick={refresh} className="btn-secondary !py-2">
              Refresh this analysis
            </button>
          }
        />
      ) : (
        <>
          <div className="mb-5">
            <Notice title="How to read this">
              Overall scores use the 0–100 display scale, which is the stored backend 0–
              {BACKEND_SCORE_MAX} score multiplied by {DISPLAY_SCORE_MAX / BACKEND_SCORE_MAX}. Facets
              stay on the backend&apos;s native 0–{BACKEND_SCORE_MAX} scale. Every value is
              averaged only across responses that were actually scored, and a lower score means less
              sycophantic. Missing values are shown as N/A and are never counted as zero.
            </Notice>
          </div>

          {/* 2 — OVERALL MODEL COMPARISON */}
          <ChartFrame
            title="Overall Model Comparison"
            caption="Average sycophancy score across all evaluated variants."
            footnote="Lower score = less sycophantic. Each bar is the mean of that model's stored variant scores; a model with no scored variant is listed as N/A rather than drawn at zero."
          >
            {overallChart.length === 0 ? (
              <div className="grid place-items-center rounded-xl border border-dashed border-slate-200 px-4 py-10 text-center">
                <p className="text-[13px] font-semibold text-slate-600">Insufficient evaluation data</p>
                <p className="mt-1 text-[12px] text-slate-400">
                  No model has a stored overall score in this run.
                </p>
              </div>
            ) : (
              <div className="w-full" style={{ height: Math.max(180, overallChart.length * 52) }}>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={overallChart}
                    layout="vertical"
                    margin={{ top: 4, right: 56, bottom: 4, left: 8 }}
                  >
                    <CartesianGrid strokeDasharray="2 4" stroke={PALETTE.grid} horizontal={false} />
                    <XAxis
                      type="number"
                      domain={[0, DISPLAY_SCORE_MAX]}
                      tick={{ fontSize: 10, fill: PALETTE.axisMuted }}
                      axisLine={false}
                      tickLine={false}
                    />
                    <YAxis
                      type="category"
                      dataKey="name"
                      width={140}
                      tick={{ fontSize: 11, fill: PALETTE.axisStrong, fontWeight: 600 }}
                      axisLine={{ stroke: PALETTE.grid }}
                      tickLine={false}
                    />
                    <Tooltip
                      content={<ScoreTooltip unitMax={DISPLAY_SCORE_MAX} />}
                      cursor={{ fill: PALETTE.surface }}
                    />
                    {/* Identity colours, not severity colours: a model keeps the
                        same colour here as in every other chart on the page. */}
                    <Bar dataKey="display" radius={[0, 4, 4, 0]} isAnimationActive={false}>
                      {overallChart.map((d) => (
                        <Cell key={d.name} fill={colorOf(d.name)} />
                      ))}
                      <LabelList
                        dataKey="display"
                        position="right"
                        formatter={(v) => (typeof v === "number" ? v.toFixed(1) : "N/A")}
                        style={{ fontSize: 11, fill: PALETTE.axisStrong, fontWeight: 600 }}
                      />
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}

            <div className="mt-4 grid gap-2.5 sm:grid-cols-2 lg:grid-cols-3">
              {data.models.map((m) => (
                <div key={m.name} className="rounded-xl border border-slate-200 bg-white p-3.5">
                  <p className="flex items-center gap-2">
                    <span
                      className="h-2.5 w-2.5 shrink-0 rounded-full"
                      style={{ backgroundColor: colorOf(m.name) }}
                      aria-hidden="true"
                    />
                    <span className="truncate text-[12.5px] font-semibold text-slate-800" title={m.name}>
                      {m.name}
                    </span>
                  </p>
                  <p className="mt-1.5 text-[20px] font-bold leading-none tabular-nums text-slate-900">
                    {m.overallDisplay !== null ? m.overallDisplay.toFixed(1) : "N/A"}
                    <span className="ml-1 text-[11px] font-medium text-slate-400">/ 100</span>
                  </p>
                  <p className="mt-1.5 text-[11.5px] text-slate-500">
                    {m.scoredCount} scored variant{m.scoredCount === 1 ? "" : "s"}
                    {m.provider ? ` · ${m.provider}` : ""}
                  </p>
                </div>
              ))}
            </div>
          </ChartFrame>

          {/* 3 — MODEL x VARIANT (the core view) */}
          <ChartFrame
            title="Model × Variant"
            caption="Sycophancy score per model for every generated variant"
            footnote="Each series is one model and each group is one generated variant, taken from the variants this run actually stored. A missing bar means no scored response exists for that pair — it is not a zero."
          >
            <div className="h-[320px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={variantChart} margin={{ top: 8, right: 8, bottom: 4, left: -12 }}>
                  <CartesianGrid strokeDasharray="2 4" stroke={PALETTE.grid} vertical={false} />
                  <XAxis
                    dataKey="variant"
                    tick={{ fontSize: 11, fill: PALETTE.axisStrong, fontWeight: 600 }}
                    axisLine={{ stroke: PALETTE.grid }}
                    tickLine={false}
                  />
                  <YAxis
                    domain={[0, DISPLAY_SCORE_MAX]}
                    tick={{ fontSize: 10, fill: PALETTE.axisMuted }}
                    axisLine={false}
                    tickLine={false}
                    width={40}
                  />
                  <Tooltip
                    content={<ScoreTooltip unitMax={DISPLAY_SCORE_MAX} />}
                    cursor={{ fill: PALETTE.surface }}
                  />
                  {/* Legend carries the actual model names. */}
                  <Legend wrapperStyle={{ fontSize: 11, paddingTop: 8 }} iconType="circle" iconSize={7} />
                  {data.models.map((m) => (
                    <Bar
                      key={m.name}
                      dataKey={m.name}
                      name={m.name}
                      fill={colorOf(m.name)}
                      radius={[4, 4, 0, 0]}
                      isAnimationActive={false}
                    />
                  ))}
                </BarChart>
              </ResponsiveContainer>
            </div>
          </ChartFrame>

          {/* 4 — FACET PERFORMANCE */}
          <ChartFrame
            title="Facet Performance"
            caption={`Facet score per model, backend 0–${BACKEND_SCORE_MAX} scale`}
            note="Facet scores are aggregated across the evaluated variants."
            footnote={`${FACET_DEFS.map((f) => `${f.id} ${f.label}`).join(" · ")}`}
          >
            {facetChart.length === 0 ? (
              <div className="grid place-items-center rounded-xl border border-dashed border-slate-200 px-4 py-10 text-center">
                <p className="text-[13px] font-semibold text-slate-600">No facet scores stored</p>
                <p className="mt-1 text-[12px] text-slate-400">
                  Facet performance needs stored facet_scores for this run.
                </p>
              </div>
            ) : (
              <FacetGroupedChart
                data={facetChart}
                categoryKeys={data.models.map((m) => m.name)}
                categoryLabels={Object.fromEntries(data.models.map((m) => [m.name, m.name]))}
                colorFor={colorOf}
                height={300}
              />
            )}
          </ChartFrame>

          {/* 5 — FACET x MODEL HEATMAP */}
          <ChartFrame
            title="Facet × Model"
            caption={`Aggregated facet score per model, 0–${BACKEND_SCORE_MAX}`}
            footnote="Low values are quiet green, mid amber, high red, on the same 0.4 / 0.7 breakpoints used by the score badges. A dashed cell means no value was stored."
          >
            <ModelFacetHeatmap rows={heatmapRows} max={BACKEND_SCORE_MAX} />
          </ChartFrame>
        </>
      )}

      {/* 6 — DETAILED MODEL COMPARISON */}
      {data.hasScores && (
        <section className="mb-6">
          <div className="mb-3">
            <h2 className="section-title">Detailed Model Comparison</h2>
            <p className="section-sub">
              Overall score on the 0–100 display scale, facets on the backend 0–
              {BACKEND_SCORE_MAX} scale.
            </p>
          </div>

          {tableRows.length === 0 ? (
            <EmptyState
              compact
              title="Insufficient evaluation data"
              subtitle="The comparison table needs at least one scored response in this run."
            />
          ) : (
            <div className="card overflow-hidden">
              <div className="scroll-x">
                <table className="w-full min-w-[720px] border-collapse">
                  <caption className="sr-only">
                    Model comparison: overall score and facet scores per model
                  </caption>
                  <thead className="border-b border-slate-100 bg-surface-50">
                    <tr>
                      <th scope="col" className="table-head">
                        Model
                      </th>
                      <th scope="col" className="table-head text-right">
                        Overall
                      </th>
                      {FACET_DEFS.map((f) => (
                        <th key={f.key} scope="col" className="table-head text-right">
                          <span className="font-bold">{f.id}</span>
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {tableRows.map((m) => (
                      <tr key={m.name} className="border-b border-slate-100 last:border-0 hover:bg-surface-50">
                        <th scope="row" className="table-cell">
                          <span className="flex items-center gap-2">
                            <span
                              className="h-2.5 w-2.5 shrink-0 rounded-full"
                              style={{ backgroundColor: colorOf(m.name) }}
                              aria-hidden="true"
                            />
                            <span className="font-medium text-slate-800">{m.name}</span>
                          </span>
                        </th>
                        <td className="table-num">
                          {m.overallDisplay !== null ? (
                            <>
                              <span className="block font-semibold tabular-nums text-slate-900">
                                {m.overallDisplay.toFixed(1)}
                              </span>
                              <span className="block text-[10.5px] tabular-nums text-slate-400">
                                raw {formatBackScore(m.overallBack)} / {BACKEND_SCORE_MAX}
                              </span>
                            </>
                          ) : (
                            <span className="text-slate-300">N/A</span>
                          )}
                        </td>
                        {FACET_DEFS.map((f) => {
                          const v = m.facets[f.id.toLowerCase()];
                          return (
                            <td key={f.key} className="table-num">
                              {v === null || v === undefined ? (
                                <span className="text-slate-300">N/A</span>
                              ) : (
                                <span className="font-medium tabular-nums text-slate-700">
                                  {formatBackScore(v, 2)}
                                </span>
                              )}
                            </td>
                          );
                        })}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* F1..F5 legend */}
              <div className="flex flex-wrap items-center gap-x-4 gap-y-1 border-t border-slate-100 bg-surface-50 px-4 py-2.5">
                <span className="text-[10.5px] font-semibold uppercase tracking-wide text-slate-400">
                  Facets
                </span>
                {FACET_DEFS.map((f) => (
                  <span key={f.key} className="text-[11px] text-slate-500">
                    <span className="font-bold text-slate-700">{f.id}</span> = {f.label}
                  </span>
                ))}
              </div>
            </div>
          )}
        </section>
      )}

      {/* 7 — VARIANT DETAILS */}
      {data.hasScores && variantGroups.length > 0 && (
        <section>
          <details className="card group overflow-hidden">
            <summary className="flex cursor-pointer list-none items-center justify-between gap-3 px-5 py-4">
              <span>
                <span className="section-title">View variant-level details</span>
                <span className="section-sub mt-0.5 block">
                  The stored values behind every chart above — no response text.
                </span>
              </span>
              <svg
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.8"
                strokeLinecap="round"
                strokeLinejoin="round"
                className="h-4 w-4 shrink-0 text-slate-400 transition-transform duration-150 group-open:rotate-180"
                aria-hidden="true"
              >
                <path d="m6 9 6 6 6-6" />
              </svg>
            </summary>

            <div className="border-t border-slate-100 px-5 py-4">
              <div className="space-y-5">
                {variantGroups.map((v) => (
                  <div key={v.key}>
                    <div className="mb-2 flex items-baseline gap-2">
                      <h3 className="text-[13px] font-bold text-slate-800">{v.label}</h3>
                      {v.sublabel && <span className="text-[11px] text-slate-400">{v.sublabel}</span>}
                    </div>

                    <div className="scroll-x">
                      <table className="w-full min-w-[620px] border-collapse">
                        <thead>
                          <tr>
                            <th scope="col" className="table-head">Model</th>
                            <th scope="col" className="table-head text-right">Score</th>
                            {FACET_IDS.map((id) => (
                              <th key={id} scope="col" className="table-head text-right">
                                {id}
                              </th>
                            ))}
                          </tr>
                        </thead>
                        <tbody>
                          {v.entries.map(({ model, cell }) => (
                            <tr key={model} className="border-t border-slate-100">
                              <td className="table-cell">
                                <span className="flex items-center gap-2">
                                  <span
                                    className="h-2 w-2 shrink-0 rounded-full"
                                    style={{ backgroundColor: colorOf(model) }}
                                    aria-hidden="true"
                                  />
                                  <span className="font-medium text-slate-700">{model}</span>
                                </span>
                              </td>
                              <td className="table-num">
                                <Score value={cell.scoreDisplay} digits={1} suffix=" / 100" />
                              </td>
                              {FACET_DEFS.map((f) => {
                                const val = cell.facets[f.id.toLowerCase()];
                                return (
                                  <td key={f.key} className="table-num">
                                    {val === null || val === undefined ? (
                                      <span className="text-slate-300">N/A</span>
                                    ) : (
                                      <span className="tabular-nums text-slate-700">
                                        {formatBackScore(val, 2)}
                                      </span>
                                    )}
                                  </td>
                                );
                              })}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                ))}
              </div>

              <p className="meta-text mt-4">
                Scores are the 0–100 display scale, facets the 0–{BACKEND_SCORE_MAX} backend scale.
                Response text lives under Results and Sycophancy Analysis.
              </p>
            </div>
          </details>
        </section>
      )}
    </div>
  );
}