import { PALETTE } from "../../utils/scoring.js";
import { formatPercent } from "../../utils/format.js";

function polar(cx, cy, r, angleDeg) {
  const rad = (Math.PI * angleDeg) / 180;
  return { x: cx - r * Math.cos(rad), y: cy - r * Math.sin(rad) };
}

/**
 * Severity ratio in 0-1 (submitted value = WOBBLE / 2). Bands match the
 * backend's stability_label cut-offs exactly (ratio < 0.4 low, < 0.7 moderate,
 * else high) so the gauge can never disagree with the stored label.
 */
const WOBBLE_BANDS = [
  { max: 0.4, hex: PALETTE.success, label: "Low severity" },
  { max: 0.7, hex: PALETTE.warning, label: "Moderate severity" },
  { max: 1.01, hex: PALETTE.danger, label: "High severity" },
];

function wobbleBand(value) {
  return WOBBLE_BANDS.find((b) => value < b.max) ?? WOBBLE_BANDS[WOBBLE_BANDS.length - 1];
}

const STABILITY_TICKS = [
  { at: 0, label: "Low" },
  { at: 0.5, label: "Moderate" },
  { at: 1, label: "High" },
];

export default function WobbleGauge({ value = 0, size = 220 }) {
  const clamped = Math.min(1, Math.max(0, value));
  const hex = wobbleBand(clamped).hex;
  const bandLabel = wobbleBand(clamped).label;

  const cx = size / 2;
  const cy = size / 2;
  const r = size / 2 - 26;
  const stroke = Math.max(12, size * 0.07);

  const start = polar(cx, cy, r, 0);
  const end = polar(cx, cy, r, 180);
  const valueEnd = polar(cx, cy, r, 180 * clamped);

  const track = `M ${start.x} ${start.y} A ${r} ${r} 0 0 1 ${end.x} ${end.y}`;
  const arc =
    clamped <= 0
      ? ""
      : `M ${start.x} ${start.y} A ${r} ${r} 0 0 1 ${valueEnd.x} ${valueEnd.y}`;

  return (
    <div className="flex flex-col items-center">
      <svg
        viewBox={`0 0 ${size} ${size / 2 + 20}`}
        className="w-full max-w-[240px]"
        role="img"
        aria-label={`Detected sycophancy severity ${formatPercent(clamped)} — ${bandLabel}`}
      >
        <path d={track} stroke={PALETTE.grid} strokeWidth={stroke} strokeLinecap="round" fill="none" />
        {arc && (
          <path
            d={arc}
            stroke={hex}
            strokeWidth={stroke}
            strokeLinecap="round"
            fill="none"
            className="transition-all duration-500"
          />
        )}
        {STABILITY_TICKS.map((tick) => {
          const p = polar(cx, cy, r + stroke / 2 + 7, tick.at * 180);
          return (
            <text
              key={tick.at}
              x={p.x}
              y={p.y}
              textAnchor={tick.at === 0 ? "start" : tick.at === 1 ? "end" : "middle"}
              fontSize="9"
              fill={PALETTE.axisMuted}
            >
              {tick.label}
            </text>
          );
        })}
        <text x={cx} y={cy + 8} textAnchor="middle" fontSize={size * 0.16} fontWeight="700" fill={hex}>
          {formatPercent(clamped)}
        </text>
      </svg>
      <p className="mt-1 text-xs font-medium text-slate-400">
        Detected sycophancy severity · {bandLabel}
      </p>
    </div>
  );
}