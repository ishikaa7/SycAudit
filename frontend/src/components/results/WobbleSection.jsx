import WobbleGauge from "../ui/WobbleGauge.jsx";
import { STABILITY_META } from "../../utils/constants.js";
import { formatDateTime } from "../../utils/format.js";
import { formatBackScore } from "../../utils/scoring.js";

/**
 * Wobble / stability, read straight from the backend report object.
 * Renders nothing when there is no report, so the caller can gate on it.
 *
 * `wobble_score` is displayed exactly as stored. No producer or documented
 * scale for it exists in the backend, so it is shown as a raw stored value
 * rather than being rescaled into a percentage that the data cannot support.
 */
export default function WobbleSection({ report }) {
  if (!report) return null;

  const meta = STABILITY_META[report.stability_label] ?? STABILITY_META.moderate;
  const hasWobble = typeof report.wobble_score === "number" && Number.isFinite(report.wobble_score);

  return (
    <section className="card p-5 sm:p-6">
      <div className="grid items-center gap-6 md:grid-cols-[220px_1fr]">
        {hasWobble ? (
          <WobbleGauge value={report.wobble_score} />
        ) : (
          <div className="grid h-[130px] place-items-center rounded-xl border border-dashed border-slate-200 text-center">
            <div className="px-3">
              <p className="text-[12.5px] font-semibold text-slate-600">Wobble score</p>
              <p className="mt-1 text-[11.5px] text-slate-400">Not available</p>
            </div>
          </div>
        )}

        <div>
          <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
            Stability report
          </h3>
          <div className="mt-2 flex flex-wrap items-center gap-2">
            <span
              className={`inline-flex items-center rounded-full px-3 py-1 text-sm font-semibold ring-1 ring-inset ${meta.chip}`}
            >
              {meta.label}
            </span>
            <span className="text-sm text-slate-500">
              wobble score (as stored) {hasWobble ? formatBackScore(report.wobble_score) : "N/A"}
            </span>
          </div>
          <p className="mt-2 max-w-xl text-sm leading-relaxed text-slate-500">
            The wobble score measures how much model answers drift across prompt framings.{" "}
            {meta.detail} Higher wobble scores mean less stable, less trustworthy behaviour.
          </p>
          {report.created_at && (
            <p className="mt-3 text-xs text-slate-400">
              Report generated {formatDateTime(report.created_at)}
            </p>
          )}
        </div>
      </div>
    </section>
  );
}