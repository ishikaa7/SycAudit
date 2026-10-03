import { FACET_DEFS, facetFillPct, scoreHex } from "../../utils/scoring.js";
import { formatBackScore } from "../../utils/scoring.js";

/**
 * Horizontal facet bars on the real backend 0-5 scale.
 * Absent facets render as "N/A" rather than 0 — never invent a value.
 */
export default function FacetBars({ score, max = 5 }) {
  return (
    <div className="flex flex-col gap-2.5">
      {FACET_DEFS.map((facet) => {
        const raw = score?.facet_scores?.[facet.key];
        const present = typeof raw === "number" && Number.isFinite(raw);
        const value = present ? Math.min(max, Math.max(0, raw)) : 0;
        const pct = present ? facetFillPct(value) : 0;
        const hex = present ? scoreHex(value) : "#d6d3d1";
        return (
          <div key={facet.key} className="flex items-center gap-2.5">
            <span
              className="w-[104px] shrink-0 truncate text-xs text-stone-500"
              title={facet.label}
            >
              {facet.label}
            </span>
            <div className="h-2 flex-1 overflow-hidden rounded-full bg-cream-200">
              {present ? (
                <div
                  className="h-full origin-left animate-grow-in rounded-full"
                  style={{ width: `${pct}%`, backgroundColor: hex }}
                />
              ) : null}
            </div>
            <span className="w-10 shrink-0 text-right text-xs font-semibold tabular-nums text-stone-700">
              {present ? formatBackScore(value, 2) : "N/A"}
            </span>
          </div>
        );
      })}
    </div>
  );
}