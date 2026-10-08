import { BACKEND_SCORE_MAX, PALETTE, facetFillPct, scoreHex } from "../../utils/scoring.js";

/**
 * One SycAudit facet for one response, on the backend's native 0-5 scale.
 *
 * The score is never rescaled: a facet stored as 1.25 reads "1.25 / 5", matching
 * what the API holds. `note` is the caller's derived reading of that same stored
 * value.
 *
 * The evidence slot states plainly that no evidence exists. The API returns no
 * reasoning, rationale or evidence text for a response, so this card never
 * fabricates one to fill the space.
 */
export default function FacetScoreCard({ facet, value, present, note, max = BACKEND_SCORE_MAX }) {
  const pct = present ? facetFillPct(value) : 0;
  const hex = present ? scoreHex(value) : PALETTE.grid;

  return (
    <article className="flex flex-col rounded-card border border-slate-200 bg-white p-4 shadow-card">
      <header className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="text-[10.5px] font-bold tracking-wide text-slate-400">{facet.id}</p>
          <p className="mt-0.5 text-[13px] font-semibold leading-snug text-slate-900" title={facet.label}>
            {facet.label}
          </p>
        </div>
        <p
          className="shrink-0 text-[17px] font-bold leading-none tabular-nums"
          style={{ color: present ? hex : PALETTE.grid }}
        >
          {present ? value.toFixed(2) : "N/A"}
          <span className="ml-0.5 text-[10.5px] font-medium text-slate-400">/ {max}</span>
        </p>
      </header>

      <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-surface-200">
        {present && (
          <div
            className="h-full origin-left animate-grow-in rounded-full"
            style={{ width: `${pct}%`, backgroundColor: hex }}
          />
        )}
      </div>

      <p className="mt-3 flex-1 text-[11.5px] leading-relaxed text-slate-500">
        {note ??
          (present
            ? `${value.toFixed(2)} of ${max} on the backend facet scale.`
            : "No value stored for this facet on this response.")}
      </p>

      <p className="mt-2.5 border-t border-slate-100 pt-2 text-[11px] leading-relaxed text-slate-400">
        No evidence available.
      </p>
    </article>
  );
}