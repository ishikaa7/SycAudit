import { useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { useSubmissionContext } from "../components/layout/SubmissionLayout.jsx";
import SubmissionHeader from "../components/results/SubmissionHeader.jsx";
import PageHeader from "../components/ui/PageHeader.jsx";
import Notice from "../components/ui/Notice.jsx";
import EmptyState from "../components/ui/EmptyState.jsx";

import {
  BACKEND_SCORE_MAX,
  FACET_DEFS,
  buildMatrix,
  formatBackScore,
  toDisplayScore,
  severityLabel,
} from "../utils/scoring.js";

function ResponseText({ text }) {
  if (!text) {
    return (
      <p className="text-[13px] text-slate-400">
        No response text available.
      </p>
    );
  }

  return (
    <p className="whitespace-pre-wrap text-[14px] leading-relaxed text-slate-800">
      {text}
    </p>
  );
}

function FacetCard({ facet, value }) {
  const valid =
    typeof value === "number" &&
    Number.isFinite(value) &&
    value >= 0 &&
    value <= BACKEND_SCORE_MAX;

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-[11px] font-bold uppercase tracking-wide text-slate-400">
            {facet.id}
          </p>

          <h3 className="mt-1 text-[13px] font-semibold leading-snug text-slate-900">
            {facet.label}
          </h3>
        </div>

        <p className="shrink-0 text-[18px] font-bold tabular-nums text-slate-900">
          {valid ? value : "N/A"}
          <span className="text-[11px] font-normal text-slate-400">
            {" "}
            / {BACKEND_SCORE_MAX}
          </span>
        </p>
      </div>

      <div className="mt-3 h-2 overflow-hidden rounded-full bg-slate-100">
        <div
          className="h-full rounded-full bg-indigo-600 transition-all"
          style={{
            width: valid
              ? `${(value / BACKEND_SCORE_MAX) * 100}%`
              : "0%",
          }}
        />
      </div>
    </div>
  );
}

export default function AnalysisPage() {
  const { submission } = useSubmissionContext();

  const rows = useMemo(
    () => buildMatrix(submission),
    [submission]
  );

  const scoredRows = useMemo(
    () =>
      rows.filter(
        (row) =>
          row.scored &&
          row.finalScore !== null &&
          row.response?.response_text
      ),
    [rows]
  );

  const [selectedIndex, setSelectedIndex] = useState(0);

  if (!submission) {
    return (
      <div className="animate-fade-up">
        <PageHeader
          eyebrow="SYCHOPHANCY ANALYSIS"
          title="Response Analysis"
          subtitle="Inspect the SycAudit evaluation of an existing response."
        />

        <Notice tone="warning" title="No submission loaded">
          Select an existing evaluation from History.
        </Notice>
      </div>
    );
  }

  if (scoredRows.length === 0) {
    return (
      <div className="animate-fade-up">
        <PageHeader
          eyebrow="SYCHOPHANCY ANALYSIS"
          title="Response Analysis"
          subtitle="Inspect the SycAudit evaluation of an existing response."
        />

        <SubmissionHeader submission={submission} />

        <div className="mt-6">
          <EmptyState
            icon="alert"
            title="No scored responses"
            subtitle="This submission does not contain a scored response with response text."
          />
        </div>
      </div>
    );
  }

  const safeIndex =
    selectedIndex >= 0 && selectedIndex < scoredRows.length
      ? selectedIndex
      : 0;

  const selected = scoredRows[safeIndex];

  const score = selected.score || {};
  const facets = score.facet_scores || {};

  const wobble =
    typeof selected.finalScore === "number"
      ? selected.finalScore
      : null;

  const severity =
    wobble !== null
      ? toDisplayScore(wobble)
      : null;

  const severityText =
    wobble !== null
      ? severityLabel(wobble)
      : null;

  return (
    <div className="animate-fade-up">
      <PageHeader
        eyebrow="SYCHOPHANCY ANALYSIS"
        title="Response Analysis"
        subtitle="Inspect the SycAudit evaluation of each generated response from this existing submission."
        actions={
          <Link
            to={`/submissions/${submission.submission_id}/comparison`}
            className="btn-secondary !py-2"
          >
            Compare models
          </Link>
        }
      />

      <SubmissionHeader submission={submission} />

      {/* RESPONSE SELECTOR */}
      <section className="mt-6 mb-6">
        <div className="card p-3">
          <div
            className="flex gap-2 overflow-x-auto pb-1"
            role="tablist"
            aria-label="Generated responses"
          >
            {scoredRows.map((row, index) => {
              const active = index === safeIndex;

              const label =
                row.variantDef?.label ||
                row.variantLabel ||
                row.variantKey ||
                `Response ${index + 1}`;

              return (
                <button
                  key={
                    row.response?.response_id ||
                    `${row.modelName}-${row.variantKey}-${index}`
                  }
                  type="button"
                  role="tab"
                  aria-selected={active}
                  onClick={() => setSelectedIndex(index)}
                  className={`shrink-0 rounded-lg px-3 py-2 text-[12px] font-semibold transition-colors ${
                    active
                      ? "bg-indigo-600 text-white shadow-sm"
                      : "bg-slate-100 text-slate-700 hover:bg-slate-200"
                  }`}
                >
                  {label}
                </button>
              );
            })}
          </div>
        </div>
      </section>

      {/* RESPONSE + SUMMARY */}
      <div className="grid gap-6 lg:grid-cols-[1fr_360px]">
        <section className="card overflow-hidden">
          <div className="border-b border-slate-100 bg-surface-50 p-5">
            <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-400">
              Selected response
            </p>

            <h2 className="mt-1 text-[17px] font-semibold text-slate-900">
              {selected.modelName || "Unknown model"}
            </h2>

            <p className="mt-1 text-[12px] text-slate-500">
              {selected.variantDef?.label ||
                selected.variantLabel ||
                selected.variantKey ||
                "Unknown variant"}
              {selected.provider
                ? ` Â· ${selected.provider}`
                : ""}
            </p>
          </div>

          <div className="max-h-[520px] overflow-y-auto p-5">
            <ResponseText
              text={selected.response?.response_text}
            />
          </div>
        </section>

        <section className="card p-5">
          <h2 className="text-[15px] font-semibold text-slate-900">
            SycAudit Analysis
          </h2>

          <div className="mt-4 grid gap-3">
            <div className="rounded-xl border border-slate-200 p-4">
              <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-400">
                WOBBLE
              </p>

              <p className="mt-1 text-[25px] font-bold tabular-nums text-slate-900">
                {wobble !== null
                  ? formatBackScore(wobble)
                  : "N/A"}

                <span className="text-[13px] font-normal text-slate-400">
                  {" "}
                  / {BACKEND_SCORE_MAX}
                </span>
              </p>

              <p className="mt-1 text-[11px] text-slate-400">
                Mean of F1â€“F5
              </p>
            </div>

            <div className="rounded-xl border border-slate-200 p-4">
              <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-400">
                Detected sycophancy severity
              </p>

              <p className="mt-1 text-[25px] font-bold tabular-nums text-slate-900">
                {severity !== null
                  ? severity.toFixed(1)
                  : "N/A"}

                {severity !== null && (
                  <span className="text-[13px] font-normal text-slate-400">
                    %
                  </span>
                )}
              </p>

              {severityText && (
                <p className="mt-1 text-[11px] text-slate-500">
                  {severityText}
                </p>
              )}
            </div>

            <div className="rounded-xl border border-slate-200 p-4">
              <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-400">
                Rank
              </p>

              <p className="mt-1 text-[20px] font-bold text-slate-900">
                {selected.rank != null
                  ? `#${selected.rank}`
                  : "N/A"}
              </p>

              <p className="mt-1 text-[11px] text-slate-400">
                Lower WOBBLE = less detected sycophancy
              </p>
            </div>
          </div>
        </section>
      </div>

      {/* FACETS */}
      <section className="mt-6">
        <div className="mb-4">
          <h2 className="section-title">
            Facet Analysis
          </h2>

          <p className="section-sub">
            The five SycAudit facet scores returned for this response.
          </p>
        </div>

        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
          {FACET_DEFS.map((facet) => (
            <FacetCard
              key={facet.key}
              facet={facet}
              value={facets[facet.key]}
            />
          ))}
        </div>
      </section>

      {/* EVIDENCE */}
      <section className="mt-6">
        <div className="card p-5">
          <h2 className="text-[15px] font-semibold text-slate-900">
            Evidence / Explanation
          </h2>

          <p className="mt-2 text-[12.5px] leading-relaxed text-slate-500">
            Evidence and explanation are displayed only when supplied by
            the backend. No evidence is inferred or generated by the
            frontend.
          </p>

          {selected.score?.evidence ? (
            <div className="mt-4 rounded-lg bg-slate-50 p-4 text-[13px] leading-relaxed text-slate-700">
              {selected.score.evidence}
            </div>
          ) : (
            <p className="mt-3 text-[12px] text-slate-400">
              No evidence was provided by the API for this response.
            </p>
          )}
        </div>
      </section>
    </div>
  );
}
