import { severityLabel, scoreBadgeClass } from "../../utils/scoring.js";

/**
 * Severity chip. Bands come from the central utility
 * (ratio < 0.4 low, < 0.7 mid, >= 0.7 high) — emerald / amber / red.
 */
export default function ScoreBadge({ backScore, label, className = "" }) {
  if (typeof backScore !== "number" || !Number.isFinite(backScore)) {
    return (
      <span className="inline-flex items-center rounded-lg bg-slate-100 px-2 py-1 text-[11px] font-semibold text-slate-400">
        N/A
      </span>
    );
  }
  return (
    <span
      title={severityLabel(backScore)}
      className={`inline-flex items-center gap-1.5 rounded-lg px-2 py-1 text-[11px] font-semibold ring-1 ring-inset ${scoreBadgeClass(backScore)} ${className}`}
    >
      {label ?? severityLabel(backScore)}
    </span>
  );
}