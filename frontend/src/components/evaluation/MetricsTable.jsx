import { FACET_DEFS } from "../../utils/scoring.js";

/**
 * Evaluator-quality metrics table.
 *
 * The backend exposes NO human gold labels and NO evaluator-performance
 * endpoint (nothing returns exact agreement, kappa, precision, recall or F1).
 * Every cell therefore renders "Not available" while the structure is kept
 * intact, so the table can be populated the moment such data exists without
 * redesigning the page.
 *
 * `metrics` is an optional [{key,label,value}] override. It is intentionally
 * not populated with defaults: absent data must stay absent.
 */

export const EVALUATION_METRIC_COLUMNS = [
  { key: "exact_agreement", label: "Exact Agreement" },
  { key: "cohens_kappa", label: "Cohen's Kappa" },
  { key: "precision", label: "Precision" },
  { key: "recall", label: "Recall" },
  { key: "f1", label: "F1 Score" },
];

export const FACET_METRIC_COLUMNS = [
  { key: "precision", label: "Precision" },
  { key: "recall", label: "Recall" },
  { key: "f1", label: "F1" },
  { key: "human_positive", label: "Human +ve" },
  { key: "model_positive", label: "Model +ve" },
  { key: "kappa", label: "Kappa" },
];

const NOT_AVAILABLE = "Not available";

function Cell({ value }) {
  const has = value !== null && value !== undefined && value !== "";
  return (
    <td className="table-num">
      {has ? (
        <span className="font-semibold tabular-nums text-slate-800">{value}</span>
      ) : (
        <span className="text-slate-300">{NOT_AVAILABLE}</span>
      )}
    </td>
  );
}

export function EvaluationMetricsTable({ metrics = [] }) {
  const byKey = Object.fromEntries(metrics.map((m) => [m.key, m.value]));
  return (
    <div className="card overflow-hidden">
      <div className="scroll-x">
        <table className="w-full min-w-[520px] border-collapse">
          <thead className="border-b border-slate-100 bg-surface-50">
            <tr>
              <th className="table-head">Metric</th>
              {EVALUATION_METRIC_COLUMNS.map((c) => (
                <th key={c.key} className="table-head text-right">
                  {c.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            <tr>
              <td className="table-cell font-medium text-slate-800">
                SycAudit scorer vs human gold labels
              </td>
              {EVALUATION_METRIC_COLUMNS.map((c) => (
                <Cell key={c.key} value={byKey[c.key]} />
              ))}
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}

export function FacetMetricsTable({ metrics = [] }) {
  const byFacet = Object.fromEntries(metrics.map((m) => [m.key, m]));

  return (
    <div className="card overflow-hidden">
      <div className="scroll-x">
        <table className="w-full min-w-[760px] border-collapse">
          <thead className="border-b border-slate-100 bg-surface-50">
            <tr>
              <th className="table-head">Facet</th>
              {FACET_METRIC_COLUMNS.map((c) => (
                <th key={c.key} className="table-head text-right">
                  {c.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {FACET_DEFS.map((f) => {
              const row = byFacet[f.key] ?? {};
              return (
                <tr
                  key={f.key}
                  className="border-b border-slate-100 last:border-0 hover:bg-surface-50"
                >
                  <td className="table-cell">
                    <span className="font-bold text-slate-400">{f.id}</span>
                    <span className="ml-2 font-medium text-slate-700">{f.label}</span>
                  </td>
                  {FACET_METRIC_COLUMNS.map((c) => (
                    <Cell key={c.key} value={row[c.key]} />
                  ))}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export { NOT_AVAILABLE };