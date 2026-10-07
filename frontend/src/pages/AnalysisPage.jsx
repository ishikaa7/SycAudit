import { useSubmissionContext } from "../components/layout/SubmissionLayout.jsx";
import SycophancyAnalysisView from "../components/evaluation/SycophancyAnalysisView.jsx";
import Notice from "../components/ui/Notice.jsx";

/**
 * Sycophancy Analysis for the active submission.
 *
 * This is the ONLY implementation of the page. /analysis resolves the active
 * submission and redirects to /submissions/:id/analysis, and History opens an
 * older run at the same address, so a current analysis and a historical one
 * render the same component from the same data.
 *
 * It deliberately does NOT use the shared SubmissionHeader, because that carries
 * the Results / Model Comparison / Metrics / Sycophancy Analysis / All Responses
 * tab bar. Those are sidebar destinations, and a second navigation system
 * inside this page would duplicate them. The sidebar is the only navigation.
 */
export default function AnalysisPage() {
  const { submission } = useSubmissionContext();

  return (
    <div className="animate-fade-up">
      <SycophancyAnalysisView submission={submission} />

      {/* Reachable by deep link on a run that has not finished scoring. */}
      {submission && submission.status !== "completed" && (
        <div className="mt-6">
          <Notice
            tone={submission.status === "failed" ? "danger" : "warning"}
            title={
              submission.status === "failed"
                ? "This analysis failed"
                : "This analysis is not finished yet"
            }
          >
            {submission.status === "failed"
              ? "The backend recorded this run as failed, so there are no scores to show."
              : "The backend is still generating responses and scores. The figures above update automatically once the run completes."}
          </Notice>
        </div>
      )}
    </div>
  );
}