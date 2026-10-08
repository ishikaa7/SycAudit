import { Link } from "react-router-dom";
import StatusBadge from "../ui/StatusBadge.jsx";
import { formatDateTime, truncate } from "../../utils/format.js";

/**
 * Shared header for a result dashboard: the analysed prompt and its status.
 *
 * This component deliberately renders NO tab bar. It used to own one — Results /
 * Model Comparison / Metrics / Sycophancy Analysis / All Responses — which made
 * every result page carry a second navigation system alongside the sidebar.
 * Those are all standalone pages reached from the sidebar, so the sidebar is the
 * only navigation and this header is context only.
 */
export default function SubmissionHeader({ submission, children }) {
  return (
    <div className="mb-6">
      <div className="card p-4 sm:p-5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0 flex-1">
            <p className="eyebrow">Analysed prompt</p>
            <p className="mt-1.5 whitespace-pre-wrap text-[14px] leading-relaxed text-slate-800">
              {submission?.original_prompt}
            </p>
            <p className="meta-text mt-2">
              Submitted {formatDateTime(submission?.created_at)}
              {submission?.submission_id && (
                <>
                  {" · "}
                  <span className="font-mono text-[11px]">{truncate(submission.submission_id, 18)}</span>
                </>
              )}
            </p>
          </div>
          <div className="flex shrink-0 items-center gap-2">
            <StatusBadge status={submission?.status} />
          </div>
        </div>
        {children}
      </div>
    </div>
  );
}

/** Compact link back to the full result view. */
export function BackToResult({ id, label = "View full result" }) {
  return (
    <Link to={`/submissions/${id}`} className="text-xs font-medium text-indigo-700 hover:text-indigo-800">
      {label}
    </Link>
  );
}