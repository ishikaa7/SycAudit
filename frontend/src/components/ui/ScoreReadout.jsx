import { useState } from "react";
import {
  BACKEND_SCORE_MAX,
  formatBackScore,
  formatDisplayScore,
  scoreTextClass,
  toDisplayScore,
} from "../../utils/scoring.js";

/**
 * The main product-facing overall sycophancy score.
 *
 * Backend value is 0-5 and is never modified. The big number is the
 * PRESENTATION TRANSFORM  final_score * 20  ->  0-100, and the raw value is
 * always reachable via the disclosure below it.
 */
export default function ScoreReadout({
  backScore,
  size = "lg",
  caption,
  showDisclosure = true,
  className = "",
}) {
  const [open, setOpen] = useState(false);
  const display = toDisplayScore(backScore);
  const hasValue = display !== null;

  const sizes = {
    sm: { num: "text-2xl", unit: "text-xs" },
    md: { num: "text-3xl", unit: "text-[13px]" },
    lg: { num: "text-[42px] leading-none sm:text-5xl", unit: "text-sm" },
  };
  const s = sizes[size] ?? sizes.lg;

  return (
    <div className={className}>
      <div className="flex items-baseline gap-2">
        <span
          className={`${s.num} font-bold tabular-nums tracking-tight ${hasValue ? scoreTextClass(backScore) : "text-slate-300"}`}
        >
          {hasValue ? display.toFixed(1) : "N/A"}
        </span>
        <span className={`${s.unit} font-medium text-slate-400`}>/ 100</span>
      </div>

      {caption && <p className="mt-1 text-xs text-slate-500">{caption}</p>}

      {showDisclosure && (
        <div className="mt-1.5">
          <button
            type="button"
            onClick={() => setOpen((v) => !v)}
            className="text-[11px] font-medium text-slate-400 underline decoration-slate-300 underline-offset-2 transition-colors hover:text-slate-600"
          >
            {open ? "Hide raw score" : "Show raw score"}
          </button>
          {open && (
            <p className="mt-1.5 animate-slide-down text-[11.5px] leading-relaxed text-slate-500">
              Raw score:{" "}
              <span className="font-semibold tabular-nums text-slate-700">
                {formatBackScore(backScore)}
              </span>{" "}
              / {BACKEND_SCORE_MAX}
              <br />
              <span className="text-slate-400">
                Overall score: normalized from backend 0–5 score
              </span>
            </p>
          )}
        </div>
      )}
    </div>
  );
}

export { formatDisplayScore };