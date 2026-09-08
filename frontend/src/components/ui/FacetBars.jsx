import { FACETS, scoreHex } from "../../utils/constants.js";
import { formatScore } from "../../utils/format.js";

function facetValue(score, key) {
  if (!score) return 0;
  const facets = score.facet_scores;
  if (facets && typeof facets === "object" && typeof facets[key] === "number") {
    return facets[key];
  }
  if (typeof score[key] === "number") return score[key];
  return 0;
}

export default function FacetBars({ score, max = 5 }) {
  return (
    <div className="flex flex-col gap-2">
      {FACETS.map((facet) => {
        const value = facetValue(score, facet.key);
        const hex = scoreHex(value, max);
        const pct = max > 0 ? Math.min(100, (value / max) * 100) : 0;
        return (
          <div key={facet.key} className="flex items-center gap-2.5">
            <span className="w-32 shrink-0 truncate text-xs text-slate-500">
              {facet.label}
            </span>
            <div className="h-2 flex-1 overflow-hidden rounded-full bg-slate-100">
              <div
                className="h-full rounded-full transition-all duration-500"
                style={{ width: `${pct}%`, backgroundColor: hex }}
              />
            </div>
            <span className="w-8 shrink-0 text-right text-xs font-semibold tabular-nums">
              {formatScore(value)}
            </span>
          </div>
        );
      })}
    </div>
  );
}