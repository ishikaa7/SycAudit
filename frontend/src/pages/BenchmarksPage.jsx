import PageHeader from "../components/ui/PageHeader.jsx";
import EmptyState from "../components/ui/EmptyState.jsx";

/**
 * The backend's benchmark tooling is CLI-only; nothing is exposed over the API.
 * The route stays in the navigation with a deliberate, designed empty state.
 */
export default function BenchmarksPage() {
  return (
    <div className="animate-fade-up">
      <PageHeader
        eyebrow="Benchmarks"
        title="Benchmarks"
        subtitle="Reference results for SycAudit runs against published model benchmarks."
      />

      <EmptyState
        icon="flag"
        title="Benchmarks are not available yet."
        subtitle="No benchmark data is currently exposed through the application API."
      />

      <div className="mt-6 grid gap-4 sm:grid-cols-3">
        {[
          {
            title: "What a benchmark would show",
            body: "Aggregate sycophancy scores for a named model set, comparable across SycAudit releases.",
          },
          {
            title: "Why it is empty",
            body: "Benchmark generation runs from the command line. There is no HTTP endpoint serving those results.",
          },
          {
            title: "Where the data would come from",
            body: "Once an endpoint exists, this page will render its values. Nothing is estimated in the meantime.",
          },
        ].map((c) => (
          <div key={c.title} className="card p-5">
            <p className="text-[13px] font-semibold text-slate-800">{c.title}</p>
            <p className="mt-1.5 text-[12.5px] leading-relaxed text-slate-500">{c.body}</p>
          </div>
        ))}
      </div>
    </div>
  );
}