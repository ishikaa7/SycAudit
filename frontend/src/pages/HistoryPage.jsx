import { Link } from "react-router-dom";
import useSubmissionList from "../hooks/useSubmissionList.js";
import PageHeader from "../components/ui/PageHeader.jsx";
import EmptyState from "../components/ui/EmptyState.jsx";
import Notice from "../components/ui/Notice.jsx";
import StatusBadge from "../components/ui/StatusBadge.jsx";
import Spinner from "../components/ui/Spinner.jsx";
import { formatDateTime, timeAgo, truncate } from "../utils/format.js";

/** Chronological run history, including pending and failed runs. */
export default function HistoryPage() {
  const { items, loading, error, refresh } = useSubmissionList();

  return (
    <div className="animate-fade-up">
      <PageHeader
        eyebrow="History"
        title="Run history"
        subtitle="All runs in chronological order, including any that are still processing or failed."
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
        <div className="flex min-h-[40vh] items-center justify-center gap-2.5 text-sm text-stone-400">
          <Spinner className="h-4 w-4 text-burgundy-700" />
          Loading history…
        </div>
      ) : items.length === 0 ? (
        <EmptyState
          icon="clock"
          title="No history yet"
          subtitle="Runs you start will be listed here with their status and timestamps."
          action={
            <Link to="/dashboard" className="btn-primary">
              Run an analysis
            </Link>
          }
        />
      ) : (
        <div className="card overflow-hidden">
          <div className="scroll-x">
            <table className="w-full min-w-[640px] border-collapse">
              <thead className="border-b border-stone-100 bg-cream-50">
                <tr>
                  <th className="table-head">Prompt</th>
                  <th className="table-head">Status</th>
                  <th className="table-head">Created</th>
                  <th className="table-head text-right">Last updated</th>
                  <th className="table-head" />
                </tr>
              </thead>
              <tbody>
                {items.map((s) => {
                  const id = s.submission_id ?? s.id;
                  return (
                    <tr key={id} className="border-b border-stone-100 last:border-0 hover:bg-cream-50">
                      <td className="table-cell">
                        <Link
                          to={`/submissions/${id}`}
                          className="block max-w-[320px] truncate font-medium text-stone-800 hover:text-burgundy-800"
                          title={s.original_prompt}
                        >
                          {truncate(s.original_prompt, 70)}
                        </Link>
                      </td>
                      <td className="table-cell">
                        <StatusBadge status={s.status} />
                      </td>
                      <td className="table-cell text-stone-500">{formatDateTime(s.created_at)}</td>
                      <td className="table-cell text-right text-stone-500">
                        {timeAgo(s.updated_at ?? s.created_at)}
                      </td>
                      <td className="table-cell text-right">
                        <Link
                          to={`/submissions/${id}`}
                          className="text-[11.5px] font-medium text-burgundy-700 hover:text-burgundy-800"
                        >
                          View →
                        </Link>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}