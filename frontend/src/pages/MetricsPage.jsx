import { useMemo } from "react";

import { useSubmissionContext } from "../components/layout/SubmissionLayout.jsx";
import SubmissionHeader from "../components/results/SubmissionHeader.jsx";
import PageHeader from "../components/ui/PageHeader.jsx";
import Notice from "../components/ui/Notice.jsx";
import EmptyState from "../components/ui/EmptyState.jsx";

import {
  BACKEND_SCORE_MAX,
  FACET_DEFS,
  buildMatrix,
} from "../utils/scoring.js";

export default function MetricsPage() {
  const { submission } = useSubmissionContext();

  const rows = useMemo(
    () => buildMatrix(submission),
    [submission]
  );

  if (!submission) {
    return (
      <div className="animate-fade-up">
        <PageHeader
          eyebrow="Facet analysis"
          title="Facet Scores"
          subtitle="Real SycAudit facet scores for this evaluation."
        />

        <Notice tone="warning" title="No submission loaded">
          Select an evaluation from History.
        </Notice>
      </div>
    );
  }

  const scoredRows = rows.filter(
    (row) =>
      row.scored &&
      row.score &&
      row.finalScore !== null
  );

  return (
    <div className="animate-fade-up">
      <PageHeader
        eyebrow="Facet analysis"
        title="Facet Scores"
        subtitle="Real SycAudit facet scores returned for this evaluation."
      />

      <SubmissionHeader submission={submission} />

      {scoredRows.length === 0 ? (
        <div className="mt-6">
          <EmptyState
            icon="alert"
            title="No facet scores available"
            subtitle="This submission does not contain stored facet scores."
          />
        </div>
      ) : (
        <section className="mt-6">
          <div className="mb-4">
            <h2 className="section-title">
              SycAudit Facets
            </h2>

            <p className="section-sub">
              Backend scale: 0–{BACKEND_SCORE_MAX}.
            </p>
          </div>

          <div className="space-y-4">
            {scoredRows.map((row, index) => {
              const facets =
                row.score?.facet_scores || {};

              return (
                <article
                  key={
                    row.response?.response_id ||
                    `${row.modelName}-${index}`
                  }
                  className="card overflow-hidden"
                >
                  <div className="border-b border-slate-100 bg-surface-50 px-5 py-4">
                    <p className="text-[14px] font-semibold text-slate-900">
                      {row.modelName || `Response ${index + 1}`}
                    </p>

                    <p className="mt-1 text-[12px] text-slate-500">
                      {row.variantDef?.label ||
                        row.variantLabel ||
                        row.variantKey ||
                        "Unknown variant"}
                    </p>
                  </div>

                  <div className="grid gap-3 p-5 sm:grid-cols-2 lg:grid-cols-5">
                    {FACET_DEFS.map((facet) => {
                      const value = facets[facet.key];

                      const valid =
                        typeof value === "number" &&
                        Number.isFinite(value);

                      return (
                        <div
                          key={facet.key}
                          className="rounded-xl border border-slate-200 p-4"
                        >
                          <p className="text-[11px] font-bold uppercase tracking-wide text-slate-400">
                            {facet.id}
                          </p>

                          <h3 className="mt-1 text-[13px] font-semibold text-slate-900">
                            {facet.label}
                          </h3>

                          <p className="mt-3 text-[22px] font-bold tabular-nums text-slate-900">
                            {valid ? value : "N/A"}

                            <span className="text-[11px] font-normal text-slate-400">
                              {" "}
                              / {BACKEND_SCORE_MAX}
                            </span>
                          </p>

                          <div className="mt-3 h-2 overflow-hidden rounded-full bg-slate-100">
                            <div
                              className="h-full rounded-full bg-indigo-600"
                              style={{
                                width: valid
                                  ? `${(value / BACKEND_SCORE_MAX) * 100}%`
                                  : "0%",
                              }}
                            />
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </article>
              );
            })}
          </div>
        </section>
      )}
    </div>
  );
}