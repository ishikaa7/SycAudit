import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import useSubmissionList from "../hooks/useSubmissionList.js";
import PageHeader from "../components/ui/PageHeader.jsx";
import EmptyState from "../components/ui/EmptyState.jsx";
import Notice from "../components/ui/Notice.jsx";
import Spinner from "../components/ui/Spinner.jsx";
import { formatDateTime, truncate } from "../utils/format.js";
import { completedSubmissionsNewestFirst, submissionRoute } from "../utils/activeSubmission.js";

export default function PrototypeIndexPage() {
  const { items, loading, error, refresh } = useSubmissionList();
  const completed = completedSubmissionsNewestFirst(items);

  return (
    <div className="animate-fade-up">
      <PageHeader
        eyebrow="Mentor Demo"
        title="Response Comparison & Prototype Analysis"
        subtitle="Select an existing audit from History to explore REAL responses with prototype analysis."
      />
      {loading ? (
        <div className="flex min-h-[40vh] items-center justify-center gap-2.5 text-sm text-slate-400">
          <Spinner className="h-4 w-4 text-indigo-700" />
          Loading…
        </div>
      ) : completed.length === 0 ? (
        <EmptyState
          icon="chart"
          title="No completed analysis yet"
          subtitle="Complete an analysis first, then return here."
          action={
            <Link to="/history" className="btn-primary">
              Go to History
            </Link>
          }
        />
      ) : (
        <div className="grid gap-3">
          {completed.slice(0, 3).map((s) => (
            <Link
              key={s.submission_id}
              to={submissionRoute(s.submission_id, "prototype-analysis")}
              className="card card-hover flex flex-col gap-3 p-4 sm:flex-row sm:items-center sm:justify-between"
            >
              <div className="min-w-0">
                <p className="text-[14px] font-medium leading-relaxed text-slate-800">{truncate(s.original_prompt, 120)}</p>
                <p className="meta-text mt-1.5">Created {formatDateTime(s.created_at)}</p>
              </div>
              <span className="shrink-0 text-[12px] font-semibold text-indigo-700">Open Prototype Analysis →</span>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}