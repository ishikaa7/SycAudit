import {
  PolarAngleAxis,
  PolarGrid,
  PolarRadiusAxis,
  Radar,
  RadarChart,
  ResponsiveContainer,
} from "recharts";
import { FACETS, scoreHex } from "../../utils/constants.js";

function facetValue(score, key) {
  if (!score) return 0;
  const facets = score.facet_scores;
  if (facets && typeof facets === "object" && typeof facets[key] === "number") {
    return facets[key];
  }
  if (typeof score[key] === "number") return score[key];
  return 0;
}

export default function FacetRadar({ score, finalScore = 0 }) {
  const data = FACETS.map((facet) => ({
    label: facet.label,
    value: facetValue(score, facet.key),
  }));
  const hex = scoreHex(finalScore);

  return (
    <div className="h-44 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <RadarChart data={data} outerRadius="72%">
          <PolarGrid stroke="#e2e8f0" />
          <PolarAngleAxis dataKey="label" tick={{ fontSize: 10, fill: "#64748b" }} />
          <PolarRadiusAxis domain={[0, 5]} tick={false} axisLine={false} />
          <Radar
            dataKey="value"
            stroke={hex}
            fill={hex}
            fillOpacity={0.22}
            strokeWidth={2}
            isAnimationActive={false}
          />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  );
}