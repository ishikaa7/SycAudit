import FacetBars from "../ui/FacetBars.jsx";
import StatusBadge from "../ui/StatusBadge.jsx";
import {
  formatBackScore,
  formatDisplayScore,
  isFailedResponse,
  isScoredResponse,
  PALETTE,
  responseLatencyLabel,
  responseProvider,
  responseTokenLabel,
  scoreHex,
} from "../../utils/scoring.js";

/**
 * MODEL / RESPONSE / FINAL SCORE / FACET SCORES for one model under one
 * variant, used by the Results page variant explorer.
 *
 * Everything is read from the stored row. A failed call shows the backend's
 * own error text and an explicit N/A score rather than a fabricated zero.
 */
export default function VariantResponseCard({ row, isRecommended }) {
  const response = row?.response;
  const failed = isFailedResponse(response);
  const scored = isScoredResponse(response) && row.finalScore !== null;

  return (
    <article className="rounded-card border border-slate-200 bg-white p-4 shadow-card sm:p-5">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <p className="text-[14px] font-semibold text-slate-900">{row?.modelName}</p>
            <span className="chip-static">{responseProvider(response) ?? "unknown provider"}</span>
            {isRecommended && (
              <span className="inline-flex items-center gap-1.5 rounded-lg bg-emerald-50 px-2 py-1 text-[11px] font-bold text-emerald-800 ring-1 ring-inset ring-emerald-200">
                Recommended
              </span>
            )}
          </div>
          <div className="mt-1.5 flex flex-wrap items-center gap-x-3 gap-y-1">
            <StatusBadge status={response?.status} />
            {responseLatencyLabel(response) && (
              <span className="meta-text">{responseLatencyLabel(response)}</span>
            )}
            {responseTokenLabel(response) && (
              <span className="meta-text">{responseTokenLabel(response)}</span>
            )}
          </div>
        </div>

        <div className="shrink-0 text-right">
          <p className="eyebrow">Final score</p>
          <p
            className="mt-0.5 text-2xl font-bold leading-none tabular-nums"
            style={{ color: scored ? scoreHex(row.finalScore) : PALETTE.grid }}
          >
            {scored ? formatDisplayScore(row.finalScore) : "N/A"}
          </p>
          <p className="meta-text mt-1">/ 100</p>
          {scored && (
            <p className="mt-0.5 text-[10.5px] tabular-nums text-slate-400">
              raw {formatBackScore(row.finalScore)} / 5
            </p>
          )}
        </div>
      </header>

      <div className="mt-3.5">
        <p className="eyebrow">Response</p>
        {failed ? (
          <div className="mt-1.5 rounded-xl border border-indigo-100 bg-indigo-50 px-3.5 py-3">
            <p className="text-[12.5px] font-semibold text-indigo-900">This model call failed</p>
            {response?.error_message && (
              <p className="mt-1 text-[12.5px] leading-relaxed text-indigo-800">
                {response.error_message}
              </p>
            )}
          </div>
        ) : response?.response_text ? (
          <p className="mt-1.5 max-h-[260px] overflow-y-auto whitespace-pre-wrap rounded-xl border border-slate-100 bg-surface-50 p-3.5 text-[13.5px] leading-relaxed text-slate-800">
            {response.response_text}
          </p>
        ) : (
          <p className="mt-1.5 text-[12.5px] text-slate-400">
            No response text was stored for this model.
          </p>
        )}
      </div>

      <div className="mt-4 border-t border-slate-100 pt-4">
        <p className="eyebrow mb-2.5">Facet scores · backend 0–5</p>
        {scored ? (
          <FacetBars score={response.score} />
        ) : (
          <p className="text-[12px] text-slate-400">
            No score is stored for this response, so there are no facet values.
          </p>
        )}
      </div>
    </article>
  );
}