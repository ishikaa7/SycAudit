import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  LabelList,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  BACKEND_SCORE_MAX,
  FACET_DEFS,
  PALETTE,
  facetFillPct,
  isFailedResponse,
  isSuccessfulResponse,
  scoreHex,
} from "../../utils/scoring.js";

function FacetTooltip({ active, payload }) {
  if (!active || !payload || payload.length === 0) return null;
  const p = payload[0];
  const row = p?.payload;
  return (
    <div className="rounded-xl border border-slate-200 bg-white px-3 py-2 shadow-panel">
      <p className="text-[12px] font-semibold text-slate-800">{row?.name}</p>
      <p className="mt-0.5 text-[11.5px] text-slate-500">
        {row?.id} · {row?.value} / {BACKEND_SCORE_MAX}
      </p>
    </div>
  );
}

/**
 * One model's facet profile for a single prompt framing.
 * Reads only real backend facet_scores; renders a "no valid response" state
 * rather than substituting zeros.
 */
export default function VariantFacetChart({ row, variantDef, height = 168 }) {
  const hasData = row?.scored && row?.score?.facet_scores != null;

  // Distinguish "no response", "call failed" and "response stored but not yet
  // scored" so the UI never claims a valid response is missing.
  let emptyTitle = "No response";
  let emptyBody = "This model has no response for this framing.";
  if (row && isFailedResponse(row.response)) {
    emptyTitle = "No valid response";
    emptyBody =
      row.response?.error_message ||
      "This model call failed, so no facet scores exist for this framing.";
  } else if (row && isSuccessfulResponse(row.response)) {
    emptyTitle = "No facet scores stored";
    emptyBody = "The response was stored successfully, but the backend has no score for it yet.";
  }

  const data = hasData
    ? FACET_DEFS.map((f) => {
        const v = row.score.facet_scores[f.key];
        const present = typeof v === "number" && Number.isFinite(v);
        return {
          id: f.id,
          name: f.label,
          value: present ? v : 0,
          // Precomputed so the label needs no formatter (Recharts 3 passes a
          // single argument to LabelFormatter).
          label: present ? v.toFixed(1) : "",
          present,
          max: BACKEND_SCORE_MAX,
        };
      })
    : [];

  return (
    <div className="rounded-card border border-slate-200 bg-white p-4 shadow-card">
      <header className="mb-3 flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="text-[13.5px] font-semibold text-slate-900">
            {variantDef.label} — {variantDef.sublabel}
          </p>
          <p className="meta-text truncate">{row?.modelName ?? "No model"}</p>
        </div>
        {hasData && (
          <span
            className="shrink-0 rounded-lg px-2 py-1 text-[11px] font-bold tabular-nums"
            style={{
              backgroundColor:
                row.finalScore != null ? `${scoreHex(row.finalScore)}18` : PALETTE.surface,
              color: row.finalScore != null ? scoreHex(row.finalScore) : PALETTE.axisMuted,
            }}
          >
            {row.finalScore != null ? `${row.finalScore.toFixed(2)} / ${BACKEND_SCORE_MAX}` : "N/A"}
          </span>
        )}
      </header>

      {!hasData ? (
        <div
          className="grid place-items-center rounded-xl border border-dashed border-slate-200 text-center"
          style={{ height }}
        >
          <div className="px-3">
            <p className="text-[12.5px] font-semibold text-slate-600">{emptyTitle}</p>
            <p className="mt-1 text-[11.5px] leading-relaxed text-slate-400">{emptyBody}</p>
          </div>
        </div>
      ) : (
        <>
          <div style={{ height }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={data} margin={{ top: 16, right: 4, bottom: 0, left: -22 }}>
                <CartesianGrid strokeDasharray="2 4" stroke={PALETTE.grid} vertical={false} />
                <XAxis
                  dataKey="id"
                  tick={{ fontSize: 10.5, fill: PALETTE.axisStrong, fontWeight: 600 }}
                  axisLine={{ stroke: PALETTE.grid }}
                  tickLine={false}
                />
                <YAxis
                  domain={[0, BACKEND_SCORE_MAX]}
                  tick={{ fontSize: 9.5, fill: PALETTE.axisMuted }}
                  axisLine={false}
                  tickLine={false}
                  width={38}
                />
                <Tooltip content={<FacetTooltip />} cursor={{ fill: PALETTE.surface }} />
                <Bar dataKey="value" radius={[4, 4, 0, 0]} isAnimationActive={false}>
                  {data.map((d) => (
                    <Cell key={d.id} fill={d.present ? scoreHex(d.value) : PALETTE.grid} />
                  ))}
                  <LabelList
                    dataKey="label"
                    position="top"
                    style={{ fontSize: 9.5, fill: PALETTE.axisStrong, fontWeight: 600 }}
                  />
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Accessible + explicit facet legend, since bars alone can mislead. */}
          <dl className="mt-2 grid grid-cols-5 gap-1 border-t border-slate-100 pt-2.5">
            {data.map((d) => (
              <div key={d.id} className="min-w-0 text-center">
                <dt className="truncate text-[9.5px] font-medium text-slate-400" title={d.name}>
                  {d.name}
                </dt>
                <dd
                  className="mt-0.5 text-[11px] font-bold tabular-nums"
                  style={{ color: d.present ? scoreHex(d.value) : PALETTE.axisMuted }}
                >
                  {d.present ? facetFillPct(d.value).toFixed(0) + "%" : "N/A"}
                </dd>
              </div>
            ))}
          </dl>
        </>
      )}
    </div>
  );
}