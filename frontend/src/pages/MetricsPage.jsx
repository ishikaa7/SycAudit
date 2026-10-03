import { useSubmissionContext } from "../components/layout/SubmissionLayout.jsx";
import SubmissionHeader from "../components/results/SubmissionHeader.jsx";
import PageHeader from "../components/ui/PageHeader.jsx";
import Notice from "../components/ui/Notice.jsx";
import EmptyState from "../components/ui/EmptyState.jsx";
import { FACET_DEFS } from "../utils/scoring.js";

/**
 * The API exposes no human-reference annotations, so every metric below is
 * rendered as N/A. The structure is intentionally complete: the tables, rows
 * and labels a fully-instrumented build would need are all present, with the
 * cells honestly unavailable rather than invented.
 */
const OVERALL_METRICS = [
  { key: "exact_agreement", label: "Exact Agreement" },
  { key: "cohens_kappa", label: "Cohen's Kappa" },
  { key: "precision", label: "Precision" },
  { key: "recall", label: "Recall" },
  { key: "f1", label: "F1 Score" },
];

const DISAGREEMENT_ROWS = [
  { key: "model_lower", label: "Model < Human" },
  { key: "same", label: "Same" },
  { key: "model_higher", label: "Model > Human" },
];

function NaMetric({ label }) {
  return (
    <div className="rounded-xl border border-stone-200 bg-cream-50 p-4">
      <p className="text-[12.5px] font-semibold text-stone-600">{label}</p>
      <p className="mt-2 text-[26px] font-bold leading-none tabular-nums text-stone-300">N/A</p>
      <p className="meta-text mt-2">Not exposed by the API</p>
    </div>
  );
}

export default function MetricsPage() {
  const { submission } = useSubmissionContext();

  return (
    <div className="animate-fade-up">
      <PageHeader
        eyebrow="Metrics & evaluation"
        title="Human-reference evaluation"
        subtitle="Agreement of the model scorer against human gold annotations for this submission."
      />

      <SubmissionHeader submission={submission} />

      <div className="mb-6">
        <Notice tone="warning" title="Human-reference evaluation metrics are unavailable for this submission because the current API does not expose human gold annotations.">
          The backend returns model-generated scores only. Exact agreement, Cohen's kappa,
          precision, recall, F1, per-facet positive counts and disagreement tallies have no
          source in the response payload, so they are shown as N/A rather than estimated.
        </Notice>
      </div>

      {/* Overall metric tiles */}
      <section className="mb-6">
        <div className="mb-3">
          <h2 className="section-title">Overall metrics</h2>
          <p className="section-sub">Model scorer versus human gold labels.</p>
        </div>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
          {OVERALL_METRICS.map((m) => (
            <NaMetric key={m.key} label={m.label} />
          ))}
        </div>
      </section>

      {/* Per-facet table */}
      <section className="mb-6">
        <div className="mb-3">
          <h2 className="section-title">Per-facet agreement</h2>
          <p className="section-sub">Positive counts and kappa for each SycAudit facet.</p>
        </div>
        <div className="card overflow-hidden">
          <div className="scroll-x">
            <table className="w-full min-w-[620px] border-collapse">
              <thead className="border-b border-stone-100 bg-cream-50">
                <tr>
                  <th className="table-head">Facet</th>
                  <th className="table-head text-right">Human +ve</th>
                  <th className="table-head text-right">Model +ve</th>
                  <th className="table-head text-right">Kappa</th>
                  <th className="table-head text-right">Exact Agreement</th>
                </tr>
              </thead>
              <tbody>
                {FACET_DEFS.map((f) => (
                  <tr key={f.key} className="border-b border-stone-100 last:border-0 hover:bg-cream-50">
                    <td className="table-cell">
                      <span className="font-semibold text-stone-700">{f.id}</span>
                      <span className="ml-2 text-stone-600">{f.label}</span>
                    </td>
                    <td className="table-num text-stone-400">N/A</td>
                    <td className="table-num text-stone-400">N/A</td>
                    <td className="table-num text-stone-400">N/A</td>
                    <td className="table-num text-stone-400">N/A</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {/* Disagreement analysis */}
      <section className="mb-6">
        <div className="mb-3">
          <h2 className="section-title">Disagreement analysis</h2>
          <p className="section-sub">
            Where the model scorer diverges from the human judgement.
          </p>
        </div>
        <div className="grid gap-3 sm:grid-cols-3">
          {DISAGREEMENT_ROWS.map((d) => (
            <div key={d.key} className="rounded-xl border border-stone-200 bg-white p-4 shadow-card">
              <p className="text-[12.5px] font-semibold text-stone-600">{d.label}</p>
              <p className="mt-2 text-[26px] font-bold leading-none tabular-nums text-stone-300">N/A</p>
              <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-cream-200">
                <div className="h-full w-0 rounded-full bg-stone-200" />
              </div>
            </div>
          ))}
        </div>
      </section>

      <EmptyState
        compact
        icon="alert"
        title="No evaluation chart is shown"
        subtitle="Charts would require a human-reference label set. Rather than draw invented distributions, this section stays empty until the API exposes gold annotations."
      />
    </div>
  );
}