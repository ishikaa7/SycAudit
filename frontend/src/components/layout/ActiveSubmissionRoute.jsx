import { useMemo } from "react";
import { Link, Navigate } from "react-router-dom";
import useSubmissionList from "../../hooks/useSubmissionList.js";
import PageHeader from "../ui/PageHeader.jsx";
import EmptyState from "../ui/EmptyState.jsx";
import Notice from "../ui/Notice.jsx";
import Spinner from "../ui/Spinner.jsx";
import { latestCompletedSubmission, submissionRoute } from "../../utils/activeSubmission.js";

/**
 * Resolves the ACTIVE submission for a top-level section route.
 *
 * /results, /comparison, /metrics and /analysis carry no submission id, so this
 * picks the latest completed run and redirects into that run's existing nested
 * route (/submissions/:id/<segment>). The nested pages are therefore the ONLY
 * implementation of each section: a current analysis and a historical one opened
 * from History render exactly the same components.
 *
 * Redirecting rather than rendering in place is deliberate:
 *  - the id ends up in the URL, so a refresh keeps the same submission;
 *  - browser back/forward stay ordinary react-router history;
 *  - there is no second copy of any page to keep in sync.
 *
 * When no completed run exists there is nothing to redirect to, so the same
 * designed empty state is shown in place. Data comes from the existing
 * useSubmissionList hook (GET /submissions); no submission id is hardcoded.
 */
export default function ActiveSubmissionRoute({
  segment,
  eyebrow,
  title,
  subtitle,
  icon = "chart",
}) {
  const { items, loading, error, refresh } = useSubmissionList();

  const latest = useMemo(() => latestCompletedSubmission(items), [items]);
  const latestId = latest?.submission_id ?? null;

  if (loading) {
    return (
      <div className="animate-fade-up">
        <PageHeader eyebrow={eyebrow} title={title} subtitle={subtitle} />
        <div className="flex min-h-[40vh] items-center justify-center gap-2.5 text-sm text-slate-400">
          <Spinner className="h-4 w-4 text-indigo-700" />
          Loading your latest analysis…
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="animate-fade-up">
        <PageHeader eyebrow={eyebrow} title={title} subtitle={subtitle} />
        <Notice tone="danger" title="Could not load your analyses">
          {error}
          <div className="mt-3">
            <button type="button" onClick={refresh} className="btn-secondary !py-2">
              Try again
            </button>
          </div>
        </Notice>
      </div>
    );
  }

  if (!latestId) {
    return (
      <div className="animate-fade-up">
        <PageHeader eyebrow={eyebrow} title={title} subtitle={subtitle} />
        <EmptyState
          icon={icon}
          title="No completed analysis yet"
          subtitle="Run a new analysis to see detailed sycophancy evaluation."
          action={
            <Link to="/dashboard" className="btn-primary">
              New Analysis
            </Link>
          }
        />
      </div>
    );
  }

  return <Navigate to={submissionRoute(latestId, segment)} replace />;
}