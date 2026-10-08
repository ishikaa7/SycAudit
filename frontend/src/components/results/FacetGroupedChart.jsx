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
import { BACKEND_SCORE_MAX, PALETTE, seriesColor } from "../../utils/scoring.js";

/**
 * Grouped bar chart with one facet on the X axis and one bar per comparison
 * group (a prompt framing, or a model).
 *
 * Both axes are real backend values: facets stay on the backend's native 0–2
 * scale. A category with no stored value is omitted rather than drawn as a
 * zero-height bar, so "not scored" is never mistaken for "scored zero".
 *
 * Callers must render their own empty state: this component assumes at least
 * one real value and deliberately draws nothing otherwise.
 *
 * Series colours come from `seriesColor(name)`, so a given model keeps the same
 * colour in every chart and legend across the product.
 */
function GroupedTooltip({ active, payload, label, unitMax }) {
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
              {p.value == null ? "N/A" : `${p.value} / ${unitMax}`}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function FacetGroupedChart({
  data,
  categoryKeys,
  categoryLabels,
  height = 280,
  unitMax = BACKEND_SCORE_MAX,
  colorFor,
}) {
  if (!Array.isArray(data) || data.length === 0 || categoryKeys.length === 0) return null;

  // Default keeps this component's existing behaviour for every existing
  // caller. Model Comparison passes `colorFor` so a model keeps the same
  // identity colour it has in the other charts on that page.
  const resolve = colorFor ?? ((name) => seriesColor(name, categoryKeys));

  return (
    <div style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 8, right: 8, bottom: 4, left: -12 }}>
          <CartesianGrid strokeDasharray="2 4" stroke={PALETTE.grid} vertical={false} />
          <XAxis
            dataKey="label"
            tick={{ fontSize: 11, fill: PALETTE.axisStrong, fontWeight: 600 }}
            axisLine={{ stroke: PALETTE.grid }}
            tickLine={false}
          />
          <YAxis
            domain={[0, unitMax]}
            tick={{ fontSize: 10, fill: PALETTE.axisMuted }}
            axisLine={false}
            tickLine={false}
            width={40}
          />
          <Tooltip
            content={<GroupedTooltip unitMax={unitMax} />}
            cursor={{ fill: PALETTE.surface }}
          />
          {categoryKeys.length > 1 && (
            <Legend wrapperStyle={{ fontSize: 11, paddingTop: 8 }} iconType="circle" iconSize={7} />
          )}
          {categoryKeys.map((key) => (
            <Bar
              key={key}
              dataKey={key}
              name={categoryLabels?.[key] ?? key}
              fill={resolve(categoryLabels?.[key] ?? key)}
              radius={[4, 4, 0, 0]}
              isAnimationActive={false}
            />
          ))}
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}