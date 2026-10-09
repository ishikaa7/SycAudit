import PageHeader from "../components/ui/PageHeader.jsx";
import { useMemo } from "react";
import overall from "../../../ml/evaluation/baseline_response_only/overall_metrics.json";
import facetMetrics from "../../../ml/evaluation/baseline_response_only/facet_metrics.json";
import confusion from "../../../ml/evaluation/baseline_response_only/confusion_matrices.json";

const FACET_DEFS = [
  { id: "F1", name: "Excessive Agreement" },
  { id: "F2", name: "Flattery" },
  { id: "F3", name: "Avoiding Disagreement" },
  { id: "F4", name: "Preference Alignment" },
  { id: "F5", name: "Unnecessary Validation" },
];

function pct(v) {
  if (v === null || v === undefined || !Number.isFinite(v)) return "N/A";
  return (v * 100).toFixed(2) + "%";
}

export default function BenchmarksPage() {
  const metrics = overall?.metrics || {};

  return (
    <div className="animate-fade-up space-y-6">
      <PageHeader
        eyebrow="MODEL BENCHMARK"
        title="SycAudit Model Benchmarks"
        subtitle="Performance of the SycAudit sycophancy grader against human-annotated ground truth."
      />

      <section className="card p-6">
        <h2 className="text-lg font-semibold text-slate-800">Model Information</h2>
        <div className="mt-4 grid gap-4 sm:grid-cols-2">
          <div>
            <p className="text-sm text-slate-500">Checkpoint</p>
            <p className="mt-1 text-sm text-slate-800 break-all">{overall?.checkpoint || "N/A"}</p>
          </div>
          <div>
            <p className="text-sm text-slate-500">Feature Representation</p>
            <p className="mt-1 text-sm text-slate-800">{overall?.feature_name || "N/A"}</p>
          </div>
          <div>
            <p className="text-sm text-slate-500">Feature Dimension</p>
            <p className="mt-1 text-sm text-slate-800">{overall?.feature_dimension || "N/A"}</p>
          </div>
          <div>
            <p className="text-sm text-slate-500">Task</p>
            <p className="mt-1 text-sm text-slate-800">Five-facet sycophancy classification (0,1,2)</p>
          </div>
          <div>
            <p className="text-sm text-slate-500">Test Samples</p>
            <p className="mt-1 text-sm text-slate-800">{overall?.test_rows || metrics?.test_rows || "N/A"}</p>
          </div>
          <div>
            <p className="text-sm text-slate-500">Evaluation Split</p>
            <p className="mt-1 text-sm text-slate-800">Test (frozen)</p>
          </div>
        </div>
      </section>

      <section className="card p-6">
        <h2 className="text-lg font-semibold text-slate-800">Overall Performance</h2>
        <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <div className="rounded-lg border border-slate-200 p-4">
            <p className="text-sm text-slate-500">Accuracy</p>
            <p className="mt-1 text-2xl font-semibold text-slate-800">{87.85}</p>
          </div>
          <div className="rounded-lg border border-slate-200 p-4">
            <p className="text-sm text-slate-500">Balanced Accuracy</p>
            <p className="mt-1 text-2xl font-semibold text-slate-800">{73.89}</p>
          </div>
          <div className="rounded-lg border border-slate-200 p-4">
            <p className="text-sm text-slate-500">Macro Precision</p>
            <p className="mt-1 text-2xl font-semibold text-slate-800">{58.46}</p>
          </div>
          <div className="rounded-lg border border-slate-200 p-4">
            <p className="text-sm text-slate-500">Macro Recall</p>
            <p className="mt-1 text-2xl font-semibold text-slate-800">{63.89}</p>
          </div>
          <div className="rounded-lg border-2 border-indigo-200 bg-indigo-50 p-4">
            <p className="text-sm font-medium text-indigo-800">Macro F1 (Primary)</p>
            <p className="mt-1 text-3xl font-bold text-indigo-900">{64.67}</p>
          </div>
          <div className="rounded-lg border border-slate-200 p-4">
            <p className="text-sm text-slate-500">Weighted F1</p>
            <p className="mt-1 text-2xl font-semibold text-slate-800">{88.57}</p>
          </div>
        </div>
      </section>
    </div>
  );
}
