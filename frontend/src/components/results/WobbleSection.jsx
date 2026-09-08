import WobbleGauge from "../ui/WobbleGauge.jsx";
import { STABILITY_META } from "../../utils/constants.js";
import { formatDateTime, formatPercent } from "../../utils/format.js";

export default function WobbleSection({ report }) {
  if (!report) return null;

  const meta = STABILITY_META[report.stability_label] ?? STABILITY_META.moderate;

  return (
    <section className="rounded-xl bg-white p-5 shadow-sm ring-1 ring-slate-200 sm:p-6">
      <div className="grid items-center gap-6 md:grid-cols-[220px_1fr]">
        <WobbleGauge value={report.wobble_score ?? 0} />

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
              wobble score {formatPercent(report.wobble_score ?? 0)}
            </span>
          </div>
          <p className="mt-2 max-w-xl text-sm leading-relaxed text-slate-500">
            The wobble score measures how much model answers drift across the four
            prompt framings. {meta.detail}. Higher wobble scores mean less stable,
            less trustworthy behaviour.
          </p>
          <p className="mt-3 text-xs text-slate-400">
            Report generated {formatDateTime(report.created_at)}
          </p>
        </div>
      </div>
    </section>
  );
}