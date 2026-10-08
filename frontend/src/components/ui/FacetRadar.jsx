import {
  PolarAngleAxis,
  PolarGrid,
  PolarRadiusAxis,
  Radar,
  RadarChart,
  ResponsiveContainer,
} from "recharts";
import {
  BACKEND_SCORE_MAX,
  PALETTE,
  facetChartData,
  scoreHex,
} from "../../utils/scoring.js";

/** Radar over the five real SycAudit facets, 0-2 domain. */
export default function FacetRadar({ score, finalScore = 0, height = 176 }) {
  const data = facetChartData(score);
  const hex = scoreHex(finalScore);

  if (data.length === 0) {
    return (
      <div
        className="grid w-full place-items-center rounded-lg border border-dashed border-slate-200 text-xs text-slate-400"
        style={{ height }}
      >
        No facet scores available
      </div>
    );
  }

  return (
    <div className="w-full" style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <RadarChart data={data} outerRadius="70%">
          <PolarGrid stroke={PALETTE.grid} />
          <PolarAngleAxis
            dataKey="label"
            tick={{ fontSize: 10, fill: PALETTE.axisStrong }}
            axisLine={false}
          />
          <PolarRadiusAxis
            domain={[0, BACKEND_SCORE_MAX]}
            tick={{ fontSize: 8, fill: PALETTE.axisMuted }}
            axisLine={false}
            tickCount={6}
          />
          <Radar
            dataKey="value"
            stroke={hex}
            fill={hex}
            fillOpacity={0.18}
            strokeWidth={2}
            isAnimationActive={false}
          />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  );
}