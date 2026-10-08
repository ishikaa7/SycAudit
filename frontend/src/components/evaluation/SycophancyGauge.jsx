import {
  DISPLAY_SCORE_MAX,
  PALETTE,
  severityLabel,
  severityLevel,
  scoreHex,
  toDisplayScore,
} from "../../utils/scoring.js";

/**
 * Circular ring gauge for the overall sycophancy score of ONE response.
 *
 * The ring is driven entirely by the stored score: the arc length is the real
 * value on the app's existing 0-100 display scale (backend 0-2 x 50), and the
 * colour comes from `scoreHex`, i.e. the pre-existing `severityLevel` thresholds
 * (ratio low < 0.4, mid < 0.7, high otherwise). No band is invented here, and no
 * score is defaulted — a response with no stored score renders an explicit
 * unavailable state instead of an empty or zero ring.
 *
 * The number itself is rendered by the caller directly above the ring, so the
 * ring carries proportion and severity only.
 */
export default function SycophancyGauge({ backScore, size = 190 }) {
  const display = toDisplayScore(backScore);

  if (display === null) {
    return (
      <div
        className="grid place-items-center rounded-full border border-dashed border-slate-200 text-center"
        style={{ width: size, height: size }}
      >
        <div className="px-4">
          <p className="text-xl font-bold tabular-nums text-slate-300">N/A</p>
          <p className="mt-1 text-[11px] text-slate-400">No score stored</p>
        </div>
      </div>
    );
  }

  const ratio = Math.min(1, Math.max(0, display / DISPLAY_SCORE_MAX));
  const hex = scoreHex(backScore);
  const stroke = 14;
  const r = (size - stroke) / 2 - 1;
  const c = size / 2;
  const circumference = 2 * Math.PI * r;
  const level = severityLevel(backScore);

  return (
    <div className="flex flex-col items-center" style={{ width: size }}>
      <svg
        viewBox={`0 0 ${size} ${size}`}
        width={size}
        height={size}
        className="shrink-0"
        role="img"
        aria-label={`Overall sycophancy score ${display} of ${DISPLAY_SCORE_MAX}. ${severityLabel(
          backScore
        )}.`}
      >
        <circle
          cx={c}
          cy={c}
          r={r}
          fill="none"
          stroke={PALETTE.grid}
          strokeWidth={stroke}
        />
        {ratio > 0 && (
          <circle
            cx={c}
            cy={c}
            r={r}
            fill="none"
            stroke={hex}
            strokeWidth={stroke}
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={circumference * (1 - ratio)}
            transform={`rotate(-90 ${c} ${c})`}
            className="transition-all duration-500"
          />
        )}
      </svg>

      <div className="mt-2 flex w-full items-center justify-between text-[10.5px] font-medium tabular-nums text-slate-400">
        <span>0</span>
        <span className="sr-only">severity band: {level}</span>
        <span>{DISPLAY_SCORE_MAX}</span>
      </div>
    </div>
  );
}