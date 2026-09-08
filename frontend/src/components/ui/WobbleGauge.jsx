import { scoreHex, severityLevel } from "../../utils/constants.js";
import { formatPercent } from "../../utils/format.js";

function polar(cx, cy, r, angleDeg) {
  const rad = (Math.PI * angleDeg) / 180;
  return { x: cx - r * Math.cos(rad), y: cy - r * Math.sin(rad) };
}

const STABILITY_TICKS = [
  { at: 0, label: "Stable" },
  { at: 0.5, label: "Moderate" },
  { at: 1, label: "Unstable" },
];

export default function WobbleGauge({ value = 0, size = 220 }) {
  const clamped = Math.min(1, Math.max(0, value));
  const hex = scoreHex(clamped, 1);
  const level = severityLevel(clamped, 1);

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
        aria-label={`Wobble score ${formatPercent(clamped)}`}
      >
        <path
          d={track}
          stroke="#e2e8f0"
          strokeWidth={stroke}
          strokeLinecap="round"
          fill="none"
        />
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
              fill="#94a3b8"
            >
              {tick.label}
            </text>
          );
        })}
        <text
          x={cx}
          y={cy + 8}
          textAnchor="middle"
          fontSize={size * 0.16}
          fontWeight="700"
          fill={hex}
        >
          {formatPercent(clamped)}
        </text>
      </svg>
      <p className="mt-1 text-xs font-medium text-slate-400">
        Wobble score{level === "low" ? " · least trustworthy drift" : level === "mid" ? " · moderate drift" : " · high drift"}
      </p>
    </div>
  );
}