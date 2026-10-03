import { useEffect, useMemo, useState } from "react";
import { useSubmissionContext } from "../components/layout/SubmissionLayout.jsx";
import SubmissionHeader from "../components/results/SubmissionHeader.jsx";
import PageHeader from "../components/ui/PageHeader.jsx";
import ModelSelect from "../components/ui/ModelSelect.jsx";
import EmptyState from "../components/ui/EmptyState.jsx";
import Notice from "../components/ui/Notice.jsx";
import ScoreReadout from "../components/ui/ScoreReadout.jsx";
import FacetRadar from "../components/ui/FacetRadar.jsx";
import VariantFacetChart from "../components/results/VariantFacetChart.jsx";
import {
  VARIANT_DEFS,
  buildMatrix,
  collectModels,
  facetRows,
  formatBackScore,
  responseProvider,
  toDisplayScore,
} from "../utils/scoring.js";

export default function AnalysisPage() {
  const { submission } = useSubmissionContext();
  const models = useMemo(() => collectModels(submission), [submission]);
  const [model, setModel] = useState(null);

  // Keep a valid selection when models load or the submission changes.
  useEffect(() => {
    if (models.length === 0) return;
    if (!model || !models.some((m) => m.name === model)) setModel(models[0].name);
  }, [models, model]);

  const rows = useMemo(() => buildMatrix(submission), [submission]);
  const modelRows = useMemo(() => rows.filter((r) => r.modelName === model), [rows, model]);

  const scoredRows = modelRows.filter((r) => r.scored && r.finalScore !== null);
  const best = scoredRows.length
    ? scoredRows.reduce((a, b) => ((a.finalScore ?? Infinity) <= (b.finalScore ?? Infinity) ? a : b))
    : null;

  if (models.length === 0) {
    return (
      <div className="animate-fade-up">
        <PageHeader eyebrow="Sycophancy analysis" title="Facet-level analysis" />
        <SubmissionHeader submission={submission} />
        <EmptyState
          icon="chart"
          title="No scored responses to analyse"
          subtitle="Facet analysis needs at least one stored response with scores. Nothing is displayed until the backend provides them."
        />
      </div>
    );
  }

  return (
    <div className="animate-fade-up">
      <PageHeader
        eyebrow="Sycophancy analysis"
        title="Facet-level analysis"
        subtitle="Each of the five SycAudit facets, shown per prompt framing for the selected model. Facets use the backend's native 0–5 scale."
        actions={<ModelSelect models={models} value={model} onChange={setModel} />}
      />

      <SubmissionHeader submission={submission} />

      <div className="mb-5">
        <Notice title="Reading these numbers">
          Facet scores are the backend's real 0–5 values and are never rescaled. The overall
          sycophancy score elsewhere in the app is normalized to 0–100 by multiplying the stored
          0–5 value by 20. Lower scores mean less sycophancy.
        </Notice>
      </div>

      {/* Selected model summary */}
      <section className="card mb-6 p-5">
        <div className="flex flex-col gap-5 sm:flex-row sm:items-start sm:justify-between">
          <div className="min-w-0">
            <p className="eyebrow">Selected model</p>
            <p className="mt-1 text-[16px] font-semibold text-stone-900">{model}</p>
            <p className="meta-text mt-0.5">
              {responseProvider(modelRows[0]?.response)} ·{" "}
              {scoredRows.length} of {modelRows.length} framings scored
            </p>
            {best && (
              <p className="mt-2.5 text-[12.5px] text-stone-500">
                Lowest-scoring framing for this model:{" "}
                <span className="font-semibold text-stone-700">
                  {best.variantSub} ({formatBackScore(best.finalScore)} / 5)
                </span>
              </p>
            )}
          </div>
          <div className="shrink-0 sm:text-right">
            <ScoreReadout
              backScore={best?.finalScore ?? null}
              size="md"
              caption={best ? `Best framing · ${best.variantSub}` : "No scored framing"}
            />
          </div>
        </div>

        {/* Facet values for the selected model's best-scored framing */}
        {best && (
          <div className="mt-5 grid gap-5 border-t border-stone-100 pt-5 md:grid-cols-[190px_1fr] md:items-center">
            <div className="hidden md:block">
              <FacetRadar score={best.score} finalScore={best.finalScore ?? 0} height={172} />
            </div>
            <div className="space-y-2.5">
              {facetRows(best.score).map((r) => (
                <div key={r.key} className="flex items-baseline gap-3 border-b border-stone-100 pb-2 last:border-0">
                  <span className="w-8 shrink-0 text-[11px] font-bold text-stone-400">{r.id}</span>
                  <span className="min-w-0 flex-1 truncate text-[12.5px] text-stone-600">{r.label}</span>
                  <span className="shrink-0 text-[12.5px] font-semibold tabular-nums text-stone-800">
                    {r.present ? formatBackScore(r.value, 2) : "N/A"}
                    <span className="ml-0.5 text-[10.5px] font-normal text-stone-400">/ 5</span>
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
      </section>

      {/* Four variant graphs: one per prompt framing, for the selected model */}
      <section className="mb-6">
        <div className="mb-3">
          <h2 className="section-title">All four prompt framings</h2>
          <p className="section-sub">
            Four separate graphs for <span className="font-semibold text-stone-700">{model}</span> —
            these are framings of one prompt, not four different models.
          </p>
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          {VARIANT_DEFS.map((v) => (
            <VariantFacetChart
              key={v.key}
              variantDef={v}
              row={modelRows.find((r) => r.variantKey === v.key) ?? null}
            />
          ))}
        </div>
      </section>

      {/* Overall normalized comparison for this model */}
      <section>
        <div className="mb-3">
          <h2 className="section-title">Overall score by framing</h2>
          <p className="section-sub">Normalized 0–100 (backend 0–5 × 20). Lower is less sycophantic.</p>
        </div>
        <div className="card overflow-hidden">
          <div className="scroll-x">
            <table className="w-full min-w-[420px] border-collapse">
              <thead className="border-b border-stone-100 bg-cream-50">
                <tr>
                  <th className="table-head">Framing</th>
                  <th className="table-head text-right">/ 100</th>
                  <th className="table-head text-right">Raw / 5</th>
                </tr>
              </thead>
              <tbody>
                {VARIANT_DEFS.map((v) => {
                  const row = modelRows.find((r) => r.variantKey === v.key);
                  const present = row?.scored && row.finalScore !== null;
                  return (
                    <tr key={v.key} className="border-b border-stone-100 last:border-0">
                      <td className="table-cell">
                        <span className="font-semibold text-stone-800">{v.label}</span>
                        <span className="ml-1.5 text-stone-400">{v.sublabel}</span>
                      </td>
                      <td className="table-num font-semibold">
                        {present ? toDisplayScore(row.finalScore)?.toFixed(1) : "N/A"}
                      </td>
                      <td className="table-num text-stone-400">
                        {present ? formatBackScore(row.finalScore) : "N/A"}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      </section>
    </div>
  );
}