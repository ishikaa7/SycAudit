import { FACET_DEFS, PALETTE } from "../../utils/scoring.js";

/**
 * Disagreement analysis: per-facet counts of model < human, agreement, and
 * model > human.
 *
 * The backend stores no human labels, so these tallies have no source. The
 * structure is preserved and every row renders as unavailable rather than as a
 * fabricated or zero-filled distribution.
 *
 * `rows` is an optional override: [{key, modelLower, same, modelHigher}].
 */
const SERIES = [
  { key: "modelLower", label: "Model < Human", color: PALETTE.danger },
  { key: "same", label: "Same", color: PALETTE.axisMuted },
  { key: "modelHigher", label: "Model > Human", color: PALETTE.success },
];

export default function DisagreementChart({ rows = [] }) {
  const byFacet = Object.fromEntries(rows.map((r) => [r.key, r]));

  return (
    <div className="card p-5">
      <div className="mb-4 flex flex-wrap items-center gap-x-4 gap-y-2">
        {SERIES.map((s) => (
          <span key={s.key} className="flex items-center gap-1.5">
            <span
              className="h-2.5 w-2.5 rounded-sm"
              style={{ backgroundColor: s.color }}
              aria-hidden="true"
            />
            <span className="text-[11.5px] text-slate-500">{s.label}</span>
          </span>
        ))}
      </div>

      <div className="space-y-3.5">
        {FACET_DEFS.map((f) => {
          const row = byFacet[f.key];
          const values = SERIES.map((s) => row?.[s.key]);
          const hasData = values.some((v) => typeof v === "number" && Number.isFinite(v));
          const total = hasData
            ? values.reduce((a, v) => a + (typeof v === "number" && Number.isFinite(v) ? v : 0), 0)
            : 0;

          return (
            <div key={f.key} className="grid items-center gap-2 sm:grid-cols-[150px_1fr_88px]">
              <span className="truncate text-[12px] text-slate-600" title={f.label}>
                <span className="font-bold text-slate-400">{f.id}</span> {f.label}
              </span>

              {hasData && total > 0 ? (
                <div className="flex h-5 overflow-hidden rounded-md bg-surface-200">
                  {SERIES.map((s, i) => {
                    const v = values[i];
                    if (typeof v !== "number" || !Number.isFinite(v) || v <= 0) return null;
                    return (
                      <div
                        key={s.key}
                        style={{ width: `${(v / total) * 100}%`, backgroundColor: s.color }}
                        title={`${s.label}: ${v}`}
                      />
                    );
                  })}
                </div>
              ) : (
                <div className="grid h-5 place-items-center rounded-md border border-dashed border-slate-200">
                  <span className="text-[10.5px] text-slate-300">Not available</span>
                </div>
              )}

              <span className="text-right text-[11.5px] tabular-nums text-slate-400">
                {hasData ? `${total} responses` : "N/A"}
              </span>
            </div>
          );
        })}
      </div>

      <p className="meta-text mt-4 border-t border-slate-100 pt-3">
        No human-reference labels are stored by the API, so per-facet disagreement counts cannot
        be computed. No values are estimated here.
      </p>
    </div>
  );
}