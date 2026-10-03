import { Link } from "react-router-dom";
import useSubmissionList from "../hooks/useSubmissionList.js";
import PageHeader from "../components/ui/PageHeader.jsx";
import EmptyState from "../components/ui/EmptyState.jsx";
import Notice from "../components/ui/Notice.jsx";
import StatusBadge from "../components/ui/StatusBadge.jsx";
import Spinner from "../components/ui/Spinner.jsx";
import { formatDateTime, truncate } from "../utils/format.js";

/**
 * Results index. The list endpoint returns no scores, so each row links into the
 * submission's own result pages rather than summarising numbers here.
 */
export default function ResultsIndexPage() {
  const { items, loading, error, refresh } = useSubmissionList();
  const completed = items.filter((s) => s.status === "completed");

  return (
    <div className="animate-fade-up">
      <PageHeader
        eyebrow="Results"
        title="Your analyses"
        subtitle="Every sycophancy audit you have run. Open one to see its final result, variants, analysis and comparison."
        actions={
          <Link to="/dashboard" className="btn-primary !py-2">
            New analysis
          </Link>
        }
      />

      {error && (
        <div className="mb-5">
          <Notice tone="danger" title="Could not load your analyses">
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
          Loading analyses…
        </div>
      ) : items.length === 0 ? (
        <EmptyState
          icon="doc"
          title="No analyses yet"
          subtitle="Run your first prompt to generate four framings, collect model responses and score sycophancy."
          action={
            <Link to="/dashboard" className="btn-primary">
              Start an analysis
            </Link>
          }
        />
      ) : (
        <>
          <div className="mb-4 flex items-center gap-4">
            <p className="meta-text">
              <span className="font-semibold text-stone-700">{items.length}</span> total ·{" "}
              <span className="font-semibold text-stone-700">{completed.length}</span> completed
            </p>
          </div>

          <div className="grid gap-3">
            {items.map((s) => {
              const id = s.submission_id ?? s.id;
              return (
                <Link
                  key={id}
                  to={`/submissions/${id}`}
                  className="card card-hover flex flex-col gap-3 p-4 sm:flex-row sm:items-center sm:justify-between"
                >
                  <div className="min-w-0">
                    <p className="truncate text-[14px] font-medium text-stone-800">
                      {truncate(s.original_prompt, 120)}
                    </p>
                    <p className="meta-text mt-1">
                      Created {formatDateTime(s.created_at)}
                      {s.updated_at && s.updated_at !== s.created_at && (
                        <> · Updated {formatDateTime(s.updated_at)}</>
                      )}
                    </p>
                  </div>
                  <div className="flex shrink-0 items-center gap-3">
                    <StatusBadge status={s.status} />
                    <span className="text-[11.5px] font-medium text-burgundy-700">Open →</span>
                  </div>
                </Link>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
}