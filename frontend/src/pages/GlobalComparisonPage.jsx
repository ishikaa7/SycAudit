import { Link } from "react-router-dom";
import useSubmissionList from "../hooks/useSubmissionList.js";
import PageHeader from "../components/ui/PageHeader.jsx";
import EmptyState from "../components/ui/EmptyState.jsx";
import Notice from "../components/ui/Notice.jsx";
import StatusBadge from "../components/ui/StatusBadge.jsx";
import Spinner from "../components/ui/Spinner.jsx";
import { formatDateTime, truncate } from "../utils/format.js";

/**
 * Model comparison is scoped to one submission, because models only become
 * knowable from a submission's responses. This page picks which submission to
 * compare; it does not aggregate across runs.
 */
export default function GlobalComparisonPage() {
  const { items, loading, error, refresh } = useSubmissionList();
  const comparable = items.filter((s) => s.status === "completed");

  return (
    <div className="animate-fade-up">
      <PageHeader
        eyebrow="Model comparison"
        title="Choose a submission to compare"
        subtitle="Model scores are derived from a single run's responses. Pick the submission you want to compare within."
      />

      {error && (
        <div className="mb-5">
          <Notice tone="danger" title="Could not load submissions">
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
        <div className="flex min-h-[40vh] items-center justify-center gap-2.5 text-sm text-stone-400">
          <Spinner className="h-4 w-4 text-burgundy-700" />
          Loading submissions…
        </div>
      ) : comparable.length === 0 ? (
        <EmptyState
          icon="chart"
          title="No completed submissions to compare"
          subtitle="A comparison needs at least one finished run with stored model responses."
          action={
            <Link to="/dashboard" className="btn-primary">
              Run an analysis
            </Link>
          }
        />
      ) : (
        <div className="grid gap-3">
          {comparable.map((s) => {
            const id = s.submission_id ?? s.id;
            return (
              <Link
                key={id}
                to={`/submissions/${id}/comparison`}
                className="card card-hover flex flex-col gap-3 p-4 sm:flex-row sm:items-center sm:justify-between"
              >
                <div className="min-w-0">
                  <p className="truncate text-[14px] font-medium text-stone-800">
                    {truncate(s.original_prompt, 120)}
                  </p>
                  <p className="meta-text mt-1">Created {formatDateTime(s.created_at)}</p>
                </div>
                <div className="flex shrink-0 items-center gap-3">
                  <StatusBadge status={s.status} />
                  <span className="text-[11.5px] font-medium text-burgundy-700">Compare →</span>
                </div>
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}