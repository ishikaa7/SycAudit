import { Link, useParams } from "react-router-dom";
import useSubmission from "../hooks/useSubmission.js";
import StatusBadge from "../components/ui/StatusBadge.jsx";
import Spinner from "../components/ui/Spinner.jsx";
import WobbleSection from "../components/results/WobbleSection.jsx";
import VariantSection from "../components/results/VariantSection.jsx";
import { VARIANT_ORDER } from "../utils/constants.js";

export default function SubmissionDetailsPage() {
  const { id } = useParams();
  const { submission, loading, error } = useSubmission(id);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24 text-slate-400">
        <Spinner className="h-8 w-8" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-xl bg-red-50 px-4 py-12 text-center text-sm text-red-700 ring-1 ring-inset ring-red-200">
        <p className="font-semibold">Could not load this submission</p>
        <p className="mt-1">{error}</p>
        <Link to="/dashboard" className="mt-4 inline-block font-semibold text-brand-600 hover:text-brand-700">
          Back to dashboard
        </Link>
      </div>
    );
  }

  const variants = Array.isArray(submission?.variants) ? submission.variants : [];
  const report = submission?.report ?? null;
  const recommendedId = report?.recommended_response_id ?? null;

  const orderedVariants = VARIANT_ORDER.map(({ key }) =>
    variants.find((v) => v?.variant_type === key)
  ).filter(Boolean);

  const hasVariants = variants.length > 0;

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4">
        <Link
          to="/dashboard"
          className="inline-flex items-center gap-1.5 text-sm font-medium text-slate-500 transition-colors hover:text-brand-700"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="h-4 w-4">
            <path d="m15 18-6-6 6-6" />
          </svg>
          Dashboard
        </Link>
        <StatusBadge status={submission?.status} />
      </div>

      <section className="rounded-2xl bg-white p-5 shadow-sm ring-1 ring-slate-200 sm:p-6">
        <h1 className="text-pretty text-lg font-semibold leading-snug text-slate-900">
          {submission?.original_prompt}
        </h1>
        <p className="mt-1 text-xs text-slate-400">
          Submitted{" "}
          {new Date(submission?.created_at).toLocaleString(undefined, {
            dateStyle: "medium",
            timeStyle: "short",
          })}
        </p>
      </section>

      {!hasVariants ? (
        <section className="rounded-xl bg-white p-8 text-center shadow-sm ring-1 ring-slate-200">
          <div className="mx-auto mb-4 grid h-12 w-12 place-items-center rounded-full bg-brand-50 text-brand-600">
            <Spinner className="h-6 w-6" />
          </div>
          <p className="text-sm font-semibold text-slate-700">
            {submission?.status === "failed"
              ? "This submission failed to process"
              : "Audit in progress"}
          </p>
          <p className="mx-auto mt-1 max-w-md text-sm text-slate-400">
            {submission?.status === "failed"
              ? "The backend could not generate variants or responses for this prompt. Try resubmitting."
              : "SycAudit is rewriting your prompt into framings and collecting model responses. This page refreshes automatically — no reload needed."}
          </p>
        </section>
      ) : (
        <>
          <WobbleSection report={report} />
          {orderedVariants.map((variant) => (
            <VariantSection
              key={variant.variant_id}
              variant={variant}
              recommendedResponseId={recommendedId}
            />
          ))}
        </>
      )}
    </div>
  );
}