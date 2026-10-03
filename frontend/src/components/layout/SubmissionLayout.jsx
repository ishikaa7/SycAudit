import { useOutletContext, useParams } from "react-router-dom";
import { Outlet } from "react-router-dom";
import useSubmission from "../../hooks/useSubmission.js";
import Spinner from "../ui/Spinner.jsx";
import Notice from "../ui/Notice.jsx";

/**
 * Loads one submission and shares it with the nested result pages via Outlet
 * context, so moving between Final Result / Variants / Analysis / Metrics /
 * Comparison does not refetch or lose state.
 *
 * Active-status polling already lives inside useSubmission.
 */
export default function SubmissionLayout() {
  const { id } = useParams();
  const { submission, loading, error, refresh } = useSubmission(id);

  if (loading) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center gap-2.5 text-sm text-stone-400">
        <Spinner className="h-4 w-4 text-burgundy-700" />
        Loading submission…
      </div>
    );
  }

  if (error) {
    return (
      <div className="mx-auto max-w-lg py-16">
        <Notice tone="danger" title="Could not load this submission">
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

  return <Outlet context={{ submission, refresh }} />;
}

/** Consume the submission provided by SubmissionLayout. */
export function useSubmissionContext() {
  const ctx = useOutletContext();
  return {
    submission: ctx?.submission ?? null,
    refresh: ctx?.refresh ?? (() => {}),
  };
}