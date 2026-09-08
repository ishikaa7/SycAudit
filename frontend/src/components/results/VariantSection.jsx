import ResponseCard from "./ResponseCard.jsx";
import Spinner from "../ui/Spinner.jsx";

const variantDot = {
  original: "bg-slate-500",
  question: "bg-brand-500",
  third_person: "bg-indigo-500",
  hedged: "bg-violet-500",
};

export default function VariantSection({ variant, recommendedResponseId }) {
  const responses = Array.isArray(variant?.responses) ? variant.responses : [];
  const pending = responses.some((r) => !r || r.status === "pending" || r.status === "processing");
  const dot = variantDot[variant?.variant_type] ?? "bg-slate-400";

  return (
    <section className="rounded-xl bg-white p-4 shadow-sm ring-1 ring-slate-200 sm:p-5">
      <header className="flex items-center gap-2.5">
        <span className={`h-2.5 w-2.5 rounded-full ${dot}`} />
        <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
          {variant?.variant_type?.replace("_", " ") ?? "Variant"}
        </h3>
        {pending && <Spinner className="h-3.5 w-3.5 text-brand-600" />}
      </header>

      <p className="mt-2 whitespace-pre-wrap rounded-lg bg-slate-50 p-3 text-sm leading-relaxed text-slate-800">
        {variant?.variant_text}
      </p>

      {responses.length === 0 ? (
        <p className="mt-4 text-sm text-slate-400">
          No responses yet — this variant is still waiting on the models.
        </p>
      ) : (
        <div className="mt-4 flex flex-col gap-4">
          {responses.map((response) => (
            <ResponseCard
              key={response?.response_id ?? Math.random()}
              response={response}
              recommended={
                Boolean(recommendedResponseId && response?.response_id) &&
                String(response.response_id) === String(recommendedResponseId)
              }
            />
          ))}
        </div>
      )}
    </section>
  );
}