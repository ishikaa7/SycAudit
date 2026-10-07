import { Link } from "react-router-dom";
import useSubmissionList from "../hooks/useSubmissionList.js";
import PageHeader from "../components/ui/PageHeader.jsx";
import EmptyState from "../components/ui/EmptyState.jsx";
import Notice from "../components/ui/Notice.jsx";
import Spinner from "../components/ui/Spinner.jsx";
import { formatDateTime, truncate } from "../utils/format.js";
import { completedSubmissionsNewestFirst, submissionRoute } from "../utils/activeSubmission.js";

/**
 * HISTORY — the one place in the application that lists previous analyses.
 * This page remains the entry point for selecting an existing audit.
 */
export default function HistoryPage() {
  const { items, loading, error, refresh } = useSubmissionList();

  const completed = completedSubmissionsNewestFirst(items);
  const unfinished = items.length - completed.length;

  return (
    <div className="animate-fade-up">
      <PageHeader
        eyebrow="History"
        title="History"
        subtitle="Every completed analysis, newest first. Select one to open the mentor demo analysis."
      />

      {error && (
        <div className="mb-5">
          <Notice tone="danger" title="Could not load history">
            {error}
            <div className="mt-3">
              <button type="button" onClick={refresh} className="btn-secondary !py-2">
                Try again
              </button>
            </div>
          </Notice>
        </div>
      )}

      {loading ? (
        <div className="flex min-h-[40vh] items-center justify-center gap-2.5 text-sm text-slate-400">
          <Spinner className="h-4 w-4 text-indigo-700" />
          Loading history…
        </div>
      ) : completed.length === 0 ? (
        <EmptyState
          icon="clock"
          title="No completed analysis yet"
          subtitle="Run a new analysis to see detailed sycophancy evaluation."
          action={
            <Link to="/dashboard" className="btn-primary">
              New Analysis
            </Link>
          }
        />
      ) : (
        <>
          {unfinished > 0 && (
            <div className="mb-4">
              <Notice tone="info" title="Runs still in progress or failed are not listed here">
                {unfinished} run{unfinished === 1 ? " is" : "s are"} pending, processing or failed,
                so {unfinished === 1 ? "it has" : "they have"} no results to open yet.
              </Notice>
            </div>
          )}

          <div className="grid gap-3">
            {completed.map((s) => {
              const id = s.submission_id;
              return (
                <Link
                  key={id}
                  to={submissionRoute(id, "prototype-analysis")}
                  className="card card-hover flex flex-col gap-3 p-4 sm:flex-row sm:items-center sm:justify-between"
                >
                  <div className="min-w-0">
                    <p className="text-[14px] font-medium leading-relaxed text-slate-800" title={s.original_prompt}>
                      {truncate(s.original_prompt, 140)}
                    </p>
                    <p className="meta-text mt-1.5">Created {formatDateTime(s.created_at)}</p>
                  </div>
                  <span className="shrink-0 text-[12px] font-semibold text-indigo-700">
                    Open SycAudit Analysis →
                  </span>
                </Link>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
}