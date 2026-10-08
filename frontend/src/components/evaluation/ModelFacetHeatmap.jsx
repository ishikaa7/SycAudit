import { BACKEND_SCORE_MAX, FACET_DEFS, formatBackScore } from "../../utils/scoring.js";

/**
 * Facet x model heatmap. Rows are models, columns are the five canonical
 * SycAudit facets, cells are that model's mean stored facet value.
 *
 * Built as a CSS grid rather than a charting primitive: it keeps the existing
 * recharts dependency untouched and makes "no data" unambiguous, because a
 * missing value is an empty dashed cell, never a zero-coloured one.
 */
export default function ModelFacetHeatmap({ rows, max = BACKEND_SCORE_MAX }) {
  if (!Array.isArray(rows) || rows.length === 0) return null;

  return (
    <div className="scroll-x">
      <div className="min-w-[520px]">
        {/* Column headers */}
        <div
          className="grid gap-1 pb-1"
          style={{ gridTemplateColumns: `minmax(140px, 1.4fr) repeat(${FACET_DEFS.length}, minmax(64px, 1fr))` }}
        >
          <div className="flex items-end text-[11px] font-semibold uppercase tracking-wide text-slate-400">
            Model
          </div>
          {FACET_DEFS.map((f) => (
            <div key={f.key} className="text-center" title={f.label}>
              <p className="text-[11px] font-bold text-slate-600">{f.id}</p>
            </div>
          ))}
        </div>

        {/* Cells */}
        {rows.map((row) => (
          <div
            key={row.name}
            className="grid items-center gap-1 border-t border-slate-100 py-1"
            style={{ gridTemplateColumns: `minmax(140px, 1.4fr) repeat(${FACET_DEFS.length}, minmax(64px, 1fr))` }}
          >
            <div className="truncate pr-2 text-[12.5px] font-medium text-slate-700" title={row.name}>
              {row.name}
            </div>
            {row.cells.map((cell) => {
              const present = cell.value !== null;
              return (
                <div
                  key={cell.key}
                  title={
                    present
                      ? `${row.name} · ${cell.label} (${cell.id}): ${formatBackScore(cell.value)} / ${max}`
                      : `${row.name} · ${cell.label} (${cell.id}): not available`
                  }
                  className={`flex h-9 items-center justify-center rounded-md text-[11.5px] font-semibold tabular-nums ${
                    present ? "text-white" : "border border-dashed border-slate-200 text-slate-300"
                  }`}
                  style={
                    present
                      ? { backgroundColor: heatColor(cell.value, max) }
                      : undefined
                  }
                >
                  {present ? formatBackScore(cell.value, 1) : "—"}
                </div>
              );
            })}
          </div>
        ))}

        {/* Legend */}
        <div className="mt-3 flex items-center gap-2 border-t border-slate-100 pt-2.5">
          <span className="text-[10.5px] text-slate-400">0</span>
          <div className="h-2 flex-1 rounded-full bg-[linear-gradient(90deg,#f8fafc_0%,#10b981_45%,#f59e0b_70%,#ef4444_100%)]" />
          <span className="text-[10.5px] text-slate-400">{max}</span>
          <span className="ml-1 text-[10.5px] text-slate-400">
            mean facet score · dashed = no stored value
          </span>
        </div>
      </div>
    </div>
  );
}

/**
 * Emerald -> amber -> red ramp, matching the product's severity palette.
 * The light end is the page tint so that low (better) values stay quiet, and the
 * ramp uses the same 0.4 / 0.7 breakpoints as `severityLevel` so a cell's colour
 * always agrees with the badge shown elsewhere for that score.
 */
function heatColor(value, max) {
  const pct = Math.min(1, Math.max(0, value / max));
  const SURFACE = [248, 250, 252];
  const LOW = [16, 185, 129];
  const MID = [245, 158, 11];
  const HIGH = [239, 68, 68];
  if (pct <= 0.4) return mix(SURFACE, LOW, pct / 0.4);
  if (pct <= 0.7) return mix(LOW, MID, (pct - 0.4) / 0.3);
  return mix(MID, HIGH, (pct - 0.7) / 0.3);
}

function mix(a, b, t) {
  const c = a.map((v, i) => Math.round(v + (b[i] - v) * Math.max(0, Math.min(1, t))));
  return `rgb(${c[0]},${c[1]},${c[2]})`;
}