import WobbleGauge from "../ui/WobbleGauge.jsx";
import { STABILITY_META } from "../../utils/constants.js";
import { formatDateTime } from "../../utils/format.js";
import { BACKEND_SCORE_MAX, formatBackScore } from "../../utils/scoring.js";

/**
 * WOBBLE and detected sycophancy severity for the whole submission, read
 * straight from the backend report object.
 *
 * Backend semantics (existing ML model path):
 *   per-response WOBBLE = mean(F1..F5), each facet 0-2  ->  range 0-2;
 *   report.wobble_score  = mean WOBBLE across the submission's scored responses.
 *   Severity %           = WOBBLE / 2 * 100  ("Detected sycophancy severity").
 * Lower WOBBLE = less detected sycophancy. Renders nothing without a report.
 */
export default function WobbleSection({ report }) {
  if (!report) return null;

  const meta = STABILITY_META[report.stability_label] ?? STABILITY_META.moderate;
  const hasWobble = typeof report.wobble_score === "number" && Number.isFinite(report.wobble_score);
  const severityPct = hasWobble
    ? Math.min(100, Math.max(0, (report.wobble_score / BACKEND_SCORE_MAX) * 100))
    : null;

  return (
    <section className="card p-5 sm:p-6">
      <div className="grid items-center gap-6 md:grid-cols-[220px_1fr]">
        {hasWobble ? (
          <WobbleGauge value={report.wobble_score / BACKEND_SCORE_MAX} />
        ) : (
          <div className="grid h-[130px] place-items-center rounded-xl border border-dashed border-slate-200 text-center">
            <div className="px-3">
              <p className="text-[12.5px] font-semibold text-slate-600">WOBBLE</p>
              <p className="mt-1 text-[11.5px] text-slate-400">Not available</p>
            </div>
          </div>
        )}

        <div>
          <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
            WOBBLE &amp; detected sycophancy severity
          </h3>
          <div className="mt-2 flex flex-wrap items-center gap-2">
            <span
              className={`inline-flex items-center rounded-full px-3 py-1 text-sm font-semibold ring-1 ring-inset ${meta.chip}`}
            >
              {meta.label}
            </span>
            <span className="text-sm font-medium text-slate-600">
              WOBBLE {hasWobble ? `${formatBackScore(report.wobble_score)} / ${BACKEND_SCORE_MAX}` : "N/A"}
            </span>
            {severityPct !== null && (
              <span className="text-sm text-slate-500">
                Detected sycophancy severity: {severityPct.toFixed(1)}%
              </span>
            )}
          </div>
          <p className="mt-2 max-w-xl text-sm leading-relaxed text-slate-500">
            WOBBLE is the mean of the five facet scores F1–F5 (each 0–2) averaged over
            this run&rsquo;s scored responses; lower means less detected sycophancy.{" "}
            {meta.detail}
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
