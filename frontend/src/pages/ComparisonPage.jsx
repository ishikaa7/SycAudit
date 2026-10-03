import { useEffect, useMemo, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { useSubmissionContext } from "../components/layout/SubmissionLayout.jsx";
import SubmissionHeader from "../components/results/SubmissionHeader.jsx";
import PageHeader from "../components/ui/PageHeader.jsx";
import ModelSelect from "../components/ui/ModelSelect.jsx";
import EmptyState from "../components/ui/EmptyState.jsx";
import Notice from "../components/ui/Notice.jsx";
import ScoreBadge from "../components/ui/ScoreBadge.jsx";
import {
  DISPLAY_SCORE_MAX,
  PALETTE,
  buildComparison,
  collectModels,
  formatBackScore,
  VARIANT_BY_KEY,
} from "../utils/scoring.js";

const SERIES_COLORS = [PALETTE.burgundy, PALETTE.olive, PALETTE.butterDeep, PALETTE.stone];

function ComparisonTooltip({ active, payload, label }) {
  if (!active || !payload || payload.length === 0) return null;
  return (
    <div className="rounded-xl border border-stone-200 bg-white px-3 py-2.5 shadow-panel">
      <p className="mb-1.5 text-[12px] font-semibold text-stone-800">{label}</p>
      <div className="space-y-1">
        {payload.map((p) => (
          <div key={p.dataKey} className="flex items-center gap-2 text-[11.5px]">
            <span className="h-2 w-2 rounded-full" style={{ backgroundColor: p.color }} />
            <span className="min-w-0 flex-1 truncate text-stone-600">{p.dataKey}</span>
            <span className="shrink-0 font-semibold tabular-nums text-stone-800">
              {p.value ?? "N/A"}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function ComparisonPage() {
  const { submission } = useSubmissionContext();
  const models = useMemo(() => collectModels(submission), [submission]);
  const [highlight, setHighlight] = useState(null);

  const { models: cmpModels, variants: cmpVariants, series } = useMemo(
    () => buildComparison(submission),
    [submission]
  );

  useEffect(() => {
    if (cmpModels.length === 0) return;
    if (!highlight || !cmpModels.some((m) => m.name === highlight)) setHighlight(cmpModels[0].name);
  }, [cmpModels, highlight]);

  if (models.length === 0) {
    return (
      <div className="animate-fade-up">
        <PageHeader eyebrow="Model comparison" title="Compare models" />
        <SubmissionHeader submission={submission} />
        <EmptyState
          icon="chart"
          title="No models to compare in this submission"
          subtitle="Comparison needs at least one model response with a score. Nothing is drawn until the backend provides them."
        />
      </div>
    );
  }

  // Chart data: one group per framing, one bar per model.
  const chartData = cmpVariants.map((variantKey) => {
    const entry = { framing: VARIANT_BY_KEY[variantKey]?.sublabel ?? variantKey, variantKey };
    series.forEach((s) => {
      if (s.model === highlight) entry[s.model] = s.displayScore;
    });
    return entry;
  });

  const matrixRows = cmpModels;

  return (
    <div className="animate-fade-up">
      <PageHeader
        eyebrow="Model comparison"
        title="Model × variant comparison"
        subtitle="Each model's overall sycophancy score for every prompt framing. Variants are kept separate — nothing is collapsed or averaged."
        actions={<ModelSelect models={models} value={highlight} onChange={setHighlight} label="Highlight" />}
      />

      <SubmissionHeader submission={submission} />

      <div className="mb-5">
        <Notice title="Score basis">
          Bars use the normalized 0–100 overall score, derived directly from the stored backend
          0–5 value (×20). Raw values are shown in the table beneath. Lower is less sycophantic.
        </Notice>
      </div>

      {cmpVariants.length === 0 || cmpModels.length === 0 ? (
        <EmptyState
          icon="chart"
          title="No scored model × variant pairs"
          subtitle="The backend has not stored a scored response for a model/framing pair in this submission."
        />
      ) : (
        <>
          <section className="card mb-6 p-5">
            <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
              <h2 className="section-title">Overall score by prompt framing</h2>
              <p className="meta-text">0–100 normalized · lower is better</p>
            </div>
            <div className="h-[280px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData} margin={{ top: 8, right: 8, bottom: 4, left: -12 }}>
                  <CartesianGrid strokeDasharray="2 4" stroke={PALETTE.stoneSoft} vertical={false} />
                  <XAxis
                    dataKey="framing"
                    tick={{ fontSize: 11, fill: "#78716c", fontWeight: 600 }}
                    axisLine={{ stroke: PALETTE.stoneSoft }}
                    tickLine={false}
                  />
                  <YAxis
                    domain={[0, DISPLAY_SCORE_MAX]}
                    tick={{ fontSize: 10, fill: "#a8a29e" }}
                    axisLine={false}
                    tickLine={false}
                    width={40}
                  />
                  <Tooltip content={<ComparisonTooltip />} cursor={{ fill: "#faf8f4" }} />
                  {cmpModels.length > 1 && (
                    <Legend
                      wrapperStyle={{ fontSize: 11, paddingTop: 8 }}
                      iconType="circle"
                      iconSize={7}
                    />
                  )}
                  {cmpModels.map((m, i) => (
                    <Bar
                      key={m.name}
                      dataKey={m.name}
                      fill={SERIES_COLORS[i % SERIES_COLORS.length]}
                      radius={[4, 4, 0, 0]}
                      isAnimationActive={false}
                    />
                  ))}
                </BarChart>
              </ResponsiveContainer>
            </div>
          </section>

          <section>
            <div className="mb-3">
              <h2 className="section-title">Full model × variant matrix</h2>
              <p className="section-sub">
                Every valid response, with its normalized score and the underlying 0–5 value.
              </p>
            </div>
            <div className="card overflow-hidden">
              <div className="scroll-x">
                <table className="w-full min-w-[560px] border-collapse">
                  <thead className="border-b border-stone-100 bg-cream-50">
                    <tr>
                      <th className="table-head">Model</th>
                      {cmpVariants.map((vk) => (
                        <th key={vk} className="table-head text-right">
                          {VARIANT_BY_KEY[vk]?.letter}
                          <span className="ml-1 font-normal normal-case tracking-normal text-stone-400">
                            {VARIANT_BY_KEY[vk]?.sublabel}
                          </span>
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {matrixRows.map((m) => (
                      <tr key={m.name} className="border-b border-stone-100 last:border-0 hover:bg-cream-50">
                        <td className="table-cell font-medium text-stone-800">{m.name}</td>
                        {cmpVariants.map((vk) => {
                          const cell = series.find((s) => s.model === m.name && s.variantKey === vk);
                          const has = cell?.displayScore != null;
                          return (
                            <td key={vk} className="table-num">
                              {has ? (
                                <span className="block">
                                  <span className="block font-semibold tabular-nums text-stone-800">
                                    {cell.displayScore.toFixed(1)}
                                  </span>
                                  <span className="block text-[10.5px] tabular-nums text-stone-400">
                                    {formatBackScore(cell.backScore)}
                                  </span>
                                </span>
                              ) : (
                                <span className="text-stone-300">N/A</span>
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
            <p className="meta-text mt-2">
              Top figure is the normalized 0–100 value; the smaller figure beneath is the stored
              backend 0–5 score. N/A means the backend stored no valid scored response for that
              model and framing.
            </p>
          </section>

          {/* Per-model best framing, straight from the stored data */}
          <section className="mt-6">
            <div className="mb-3">
              <h2 className="section-title">Lowest-scoring framing per model</h2>
              <p className="section-sub">
                The least sycophantic framing each model produced in this submission.
              </p>
            </div>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {cmpModels.map((m) => {
                const cells = series.filter((s) => s.model === m.name && s.displayScore != null);
                const bestCell = cells.reduce((a, b) => (a.displayScore <= b.displayScore ? a : b));
                return (
                  <div key={m.name} className="card p-4">
                    <p className="truncate text-[13px] font-semibold text-stone-800" title={m.name}>
                      {m.name}
                    </p>
                    {bestCell ? (
                      <>
                        <p className="mt-2 text-[22px] font-bold leading-none tabular-nums text-stone-900">
                          {bestCell.displayScore.toFixed(1)}
                          <span className="ml-1 text-[11px] font-medium text-stone-400">/ 100</span>
                        </p>
                        <p className="mt-1.5 text-[12px] text-stone-500">
                          {bestCell.variantDef?.label} — {bestCell.variantDef?.sublabel}
                        </p>
                        <div className="mt-2">
                          <ScoreBadge backScore={bestCell.backScore} />
                        </div>
                      </>
                    ) : (
                      <p className="mt-2 text-[12.5px] text-stone-400">
                        No scored framing available for this model.
                      </p>
                    )}
                  </div>
                );
              })}
            </div>
          </section>
        </>
      )}
    </div>
  );
}