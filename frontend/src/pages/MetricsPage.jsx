import { useSubmissionContext } from "../components/layout/SubmissionLayout.jsx";
import SubmissionHeader from "../components/results/SubmissionHeader.jsx";
import PageHeader from "../components/ui/PageHeader.jsx";
import Notice from "../components/ui/Notice.jsx";
import EmptyState from "../components/ui/EmptyState.jsx";
import DisagreementChart from "../components/evaluation/DisagreementChart.jsx";
import {
  EVALUATION_METRIC_COLUMNS,
  EvaluationMetricsTable,
  FacetMetricsTable,
} from "../components/evaluation/MetricsTable.jsx";
import { summarizeSubmission, toDisplayScore } from "../utils/scoring.js";

/**
 * Metrics describes the quality and reliability of the SycAudit EVALUATOR
 * itself. It is not a model comparison and not a result summary — comparing
 * models across variants is Model Comparison's job.
 *
 * Backend gap, stated plainly: the API stores model-generated scores only. It
 * exposes no human gold labels, no evaluator-performance figures (exact
 * agreement, Cohen's kappa, precision, recall, F1) and no per-facet
 * disagreement tallies. Every such cell below therefore renders "Not
 * available". The structure is preserved so it can be filled in if such data is
 * ever added, and nothing is estimated to fill a gap.
 */
export default function MetricsPage() {
  const { submission } = useSubmissionContext();
  const stats = summarizeSubmission(submission);

  return (
    <div className="animate-fade-up">
      <PageHeader
        eyebrow="Metrics & evaluation"
        title="Metrics"
        subtitle="How well the SycAudit evaluator itself performs, against human reference labels."
      />

      <SubmissionHeader submission={submission} />

      <div className="mb-6">
        <Notice tone="warning" title="No human reference data is available from the API">
          The backend stores model-generated scores only. It returns no human gold annotations and
          no evaluator-performance endpoint, so exact agreement, Cohen&apos;s kappa, precision,
          recall, F1, per-facet positive counts and disagreement tallies all have no source in this
          response payload. They are shown as <span className="font-semibold">Not available</span>{" "}
          rather than estimated.
        </Notice>
      </div>

      {/* What the run actually contains — real observed numbers */}
      <section className="mb-8">
        <div className="mb-3">
          <h2 className="section-title">Observed in this run</h2>
          <p className="section-sub">
            Counts derived from the scores this submission stored. These are real values, kept
            separate from evaluator-quality metrics above and below.
          </p>
        </div>

        <div className="grid gap-3 sm:grid-cols-3 lg:grid-cols-5">
          {[
            { label: "Responses Stored", value: stats.responseCount, hint: "In this payload" },
            { label: "Responses Scored", value: stats.scoredCount, hint: "Carrying a score" },
            { label: "Models Compared", value: stats.modelCount, hint: "Distinct models" },
            { label: "Variants Generated", value: stats.variantCount, hint: "Prompt framings" },
            { label: "Failed Calls", value: stats.failedCount, hint: "Recorded as failed" },
          ].map((t) => (
            <div key={t.label} className="card p-4">
              <p className="text-[12.5px] font-semibold text-slate-600">{t.label}</p>
              <p className="mt-2 text-[26px] font-bold leading-none tabular-nums text-slate-900">
                {t.value}
              </p>
              <p className="meta-text mt-2">{t.hint}</p>
            </div>
          ))}
        </div>

        <div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {[
            {
              label: "Mean Score",
              back: stats.meanScore,
              hint: `Mean of ${stats.scoredCount} stored score${stats.scoredCount === 1 ? "" : "s"}`,
            },
            {
              label: "Lowest Observed",
              back: stats.minScore,
              hint: "Lowest stored score in this run",
            },
            {
              label: "Highest Observed",
              back: stats.maxScore,
              hint: "Highest stored score in this run",
            },
            {
              label: "Score Spread",
              back: stats.scoreRange,
              hint: "Highest minus lowest",
            },
          ].map((t) => {
            const v = toDisplayScore(t.back);
            return (
              <div key={t.label} className="card p-4">
                <p className="text-[12.5px] font-semibold text-slate-600">{t.label}</p>
                <p
                  className={`mt-2 text-[26px] font-bold leading-none tabular-nums ${
                    v === null ? "text-slate-300" : "text-slate-900"
                  }`}
                >
                  {v === null ? "N/A" : v.toFixed(1)}
                </p>
                <p className="meta-text mt-2">{t.hint}</p>
              </div>
            );
          })}
        </div>

        <p className="meta-text mt-3">
          Scores are shown on the 0–100 display scale (backend 0–5 × 20). Lower means less
          sycophantic. Confidence is reported exactly as stored because the backend documents no
          scale for it and the current scoring rule engine does not populate it — this run stores{" "}
          {stats.confidenceCount > 0 ? stats.meanConfidence : "none"}.
        </p>
      </section>

      {/* Evaluation metrics */}
      <section className="mb-6">
        <div className="mb-3">
          <h2 className="section-title">Evaluation metrics</h2>
          <p className="section-sub">
            SycAudit scorer versus human gold labels, for this submission.
          </p>
        </div>
        <EvaluationMetricsTable metrics={[]} />
        <p className="meta-text mt-2">
          Columns kept in place: {EVALUATION_METRIC_COLUMNS.map((c) => c.label).join(", ")}.
        </p>
      </section>

      {/* Facet-wise performance */}
      <section className="mb-6">
        <div className="mb-3">
          <h2 className="section-title">Facet-wise performance</h2>
          <p className="section-sub">
            Per-facet agreement between the model scorer and human judgement.
          </p>
        </div>
        <FacetMetricsTable metrics={[]} />
      </section>

      {/* Disagreement analysis */}
      <section className="mb-6">
        <div className="mb-3">
          <h2 className="section-title">Disagreement analysis</h2>
          <p className="section-sub">
            Per facet, where the model scorer diverges from the human judgement.
          </p>
        </div>
        <DisagreementChart rows={[]} />
      </section>

      <EmptyState
        compact
        icon="alert"
        title="No evaluator-reliability chart is shown"
        subtitle="Reliability curves and score distributions would require a human-reference label set. Rather than draw an invented distribution, this section stays empty until the API exposes gold annotations."
      />
    </div>
  );
}