import { useMemo, useState } from "react";
import { useSubmissionContext } from "../components/layout/SubmissionLayout.jsx";
import SubmissionHeader from "../components/results/SubmissionHeader.jsx";
import PageHeader from "../components/ui/PageHeader.jsx";
import ModelTabs from "../components/ui/ModelTabs.jsx";
import EmptyState from "../components/ui/EmptyState.jsx";
import ScoreBadge from "../components/ui/ScoreBadge.jsx";
import FacetBars from "../components/ui/FacetBars.jsx";
import StatusBadge from "../components/ui/StatusBadge.jsx";
import {
  buildMatrix,
  collectModels,
  collectVariants,
  facetFillPct,
  formatBackScore,
  formatDisplayScore,
  isScoredResponse,
  isFailedResponse,
  PALETTE,
  responseLatencyLabel,
  responseProvider,
  responseTokenLabel,
  scoreHex,
  toDisplayScore,
} from "../utils/scoring.js";

/** Full response body with a character count, copy-free but selectable. */
function ResponseBody({ response }) {
  const text = response?.response_text;
  if (!text) {
    return (
      <p className="text-[13px] text-slate-400">No response text was stored for this model.</p>
    );
  }
  return (
    <div className="rounded-xl border border-slate-100 bg-surface-50 p-3.5">
      <p className="whitespace-pre-wrap text-[13.5px] leading-relaxed text-slate-800">{text}</p>
      <p className="meta-text mt-2">{text.length.toLocaleString()} characters</p>
    </div>
  );
}

function ResponseCard({ row, isRecommended }) {
  const { response } = row;
  // Backend stores a successful call as status "success" (not "completed").
  const failed = isFailedResponse(response);
  const score = row.finalScore;

  return (
    <article className="rounded-xl border border-slate-200 bg-white p-4 transition-all duration-200 hover:shadow-card-hover sm:p-5">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <p className="text-[14px] font-semibold text-slate-900">{row.modelName}</p>
            <span className="chip-static">{responseProvider(response)}</span>
            {isRecommended && (
              <span className="inline-flex items-center gap-1.5 rounded-lg bg-emerald-50 px-2 py-1 text-[11px] font-bold text-emerald-800 ring-1 ring-inset ring-emerald-200">
                Least sycophantic
              </span>
            )}
          </div>
          <div className="mt-1.5 flex flex-wrap items-center gap-x-3 gap-y-1">
            <StatusBadge status={response?.status} />
            {responseLatencyLabel(response) && (
              <span className="meta-text">{responseLatencyLabel(response)}</span>
            )}
            {responseTokenLabel(response) && (
              <span className="meta-text">{responseTokenLabel(response)}</span>
            )}
          </div>
        </div>

        <div className="flex shrink-0 items-center gap-3">
          <ScoreBadge backScore={score} />
          <div className="text-right">
            <p
              className="text-2xl font-bold tabular-nums leading-none"
              style={{ color: isScoredResponse(response) ? scoreHex(score) : undefined }}
            >
              {isScoredResponse(response) ? formatDisplayScore(score) : "N/A"}
            </p>
            <p className="meta-text mt-1">/ 100</p>
          </div>
        </div>
      </header>

      {failed ? (
        <div className="mt-3.5 rounded-xl border border-indigo-100 bg-indigo-50 px-3.5 py-3">
          <p className="text-[12.5px] font-semibold text-indigo-900">This model call failed</p>
          {response?.error_message && (
            <p className="mt-1 text-[12.5px] leading-relaxed text-indigo-800">
              {response.error_message}
            </p>
          )}
          <p className="mt-1.5 text-[11.5px] text-indigo-700/80">
            No score is available for a failed response. This state is preserved from the backend.
          </p>
        </div>
      ) : (
        <div className="mt-3.5">
          <ResponseBody response={response} />
        </div>
      )}

      {row.scored && (
        <div className="mt-4 border-t border-slate-100 pt-4">
          <FacetBars score={response.score} />
          <p className="meta-text mt-3">
            Raw final_score {formatBackScore(score)} / 5 · normalized ×20 for the /100 display
          </p>
        </div>
      )}
    </article>
  );
}

/** Compact bar showing this model's score across the framings returned. */
function VariantBar({ label, sublabel, value, present, isRecommended }) {
  const pct = present ? facetFillPct(value) : 0;
  const hex = present ? scoreHex(value) : PALETTE.grid;
  return (
    <div className="min-w-0">
      <div className="flex items-baseline justify-between gap-2">
        <span className="truncate text-[12.5px] font-semibold text-slate-700">
          {label}
          <span className="ml-1.5 font-normal text-slate-400">{sublabel}</span>
        </span>
        <span className="shrink-0 text-[11.5px] tabular-nums text-slate-500">
          {present ? toDisplayScore(value)?.toFixed(0) : "—"}
        </span>
      </div>
      <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-surface-200">
        {present && (
          <div
            className="h-full origin-left animate-grow-in rounded-full"
            style={{ width: `${pct}%`, backgroundColor: hex, opacity: isRecommended ? 1 : 0.8 }}
          />
        )}
      </div>
    </div>
  );
}

export default function VariantsPage() {
  const { submission } = useSubmissionContext();
  const models = useMemo(() => collectModels(submission), [submission]);
  const [activeModel, setActiveModel] = useState(null);
  const [activeVariant, setActiveVariant] = useState("all");

  const modelName = activeModel ?? models[0]?.name ?? null;
  const rows = useMemo(() => buildMatrix(submission), [submission]);
  const modelRows = useMemo(
    () => rows.filter((r) => r.modelName === modelName),
    [rows, modelName]
  );

  // Framings come from the backend payload, so an unexpected variant_type is
  // shown with a neutral label instead of being hidden.
  const variants = useMemo(() => collectVariants(submission), [submission]);
  const shownVariants = useMemo(
    () => (activeVariant === "all" ? variants : variants.filter((v) => v.key === activeVariant)),
    [variants, activeVariant]
  );

  const counts = useMemo(() => {
    const map = {};
    rows.forEach((r) => {
      map[r.modelName] = (map[r.modelName] ?? 0) + 1;
    });
    return map;
  }, [rows]);

  const recId = submission?.report?.recommended_response_id;

  // Headline counts, taken from the payload rather than assumed.
  const scoredCount = rows.filter((r) => r.scored && r.finalScore !== null).length;

  return (
    <div className="animate-fade-up">
      <PageHeader
        eyebrow="Variants & responses"
        title="Prompt framings and model responses"
        subtitle="Each framing of the same prompt, with every model's response and facet scores. Models and framings are listed only if they appear in this submission."
      />

      <SubmissionHeader submission={submission} />

      {models.length === 0 ? (
        <EmptyState
          icon="doc"
          title="No model responses in this submission"
          subtitle="Nothing has been stored against this submission yet. Scores and responses will appear once the models respond."
        />
      ) : (
        <>
          {/* What this submission actually contains */}
          <div className="mb-5 grid gap-3 sm:grid-cols-4">
            {[
              { label: "Prompt framings", value: variants.length },
              { label: "Models compared", value: models.length },
              { label: "Responses stored", value: rows.length },
              { label: "Responses scored", value: scoredCount },
            ].map((s) => (
              <div key={s.label} className="rounded-xl border border-slate-200 bg-white p-4 shadow-card">
                <p className="text-[12.5px] font-semibold text-slate-600">{s.label}</p>
                <p className="mt-2 text-[24px] font-bold leading-none tabular-nums text-slate-900">
                  {s.value}
                </p>
              </div>
            ))}
          </div>

          <div className="mb-5">
            <ModelTabs models={models} active={modelName} onChange={setActiveModel} counts={counts} />
          </div>

          {/* Variant selector. "All" keeps every framing visible at once. */}
          <div className="mb-5">
            <p className="eyebrow mb-2">Framing</p>
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                onClick={() => setActiveVariant("all")}
                className={`rounded-lg px-3 py-1.5 text-[12.5px] font-semibold transition-colors ${
                  activeVariant === "all"
                    ? "bg-indigo-600 text-white"
                    : "border border-slate-200 bg-white text-slate-600 hover:bg-surface-50"
                }`}
              >
                All ({variants.length})
              </button>
              {variants.map((v) => (
                <button
                  key={v.key}
                  type="button"
                  onClick={() => setActiveVariant(v.key)}
                  className={`rounded-lg px-3 py-1.5 text-[12.5px] font-semibold transition-colors ${
                    activeVariant === v.key
                      ? "bg-indigo-600 text-white"
                      : "border border-slate-200 bg-white text-slate-600 hover:bg-surface-50"
                  }`}
                >
                  {v.label}
                  {v.sublabel && v.sublabel !== v.label ? ` · ${v.sublabel}` : ""}
                </button>
              ))}
            </div>
          </div>

          <section className="card mb-6 p-4 sm:p-5">
            <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
              <p className="section-title">
                Score across {variants.length} framing{variants.length === 1 ? "" : "s"}
              </p>
              <p className="meta-text">{modelName}</p>
            </div>
            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
              {variants.map((v) => {
                const row = modelRows.find((r) => r.variantKey === v.key);
                const present = row?.scored && row.finalScore !== null;
                const isRec = present && String(row.response?.response_id) === String(recId);
                return (
                  <VariantBar
                    key={v.key}
                    label={v.label}
                    sublabel={v.sublabel !== v.label ? v.sublabel : ""}
                    value={row?.finalScore}
                    present={present}
                    isRecommended={isRec}
                  />
                );
              })}
            </div>
          </section>

          <div className="flex flex-col gap-6">
            {shownVariants.map((v) => {
              const row = modelRows.find((r) => r.variantKey === v.key);
              const displayLabel =
                v.sublabel && v.sublabel !== v.label ? `${v.label} — ${v.sublabel}` : v.label;
              return (
                <section key={v.key} className="card overflow-hidden">
                  <header className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 bg-surface-50 px-4 py-3 sm:px-5">
                    <div className="flex items-center gap-2.5">
                      <span className="grid h-7 w-7 shrink-0 place-items-center rounded-lg bg-indigo-700 text-[11px] font-bold text-white">
                        {v.letter ?? v.label.charAt(0).toUpperCase()}
                      </span>
                      <div>
                        <h2 className="text-[14px] font-semibold text-slate-900">{displayLabel}</h2>
                        <p className="meta-text">{modelName}</p>
                      </div>
                    </div>
                    {row?.scored && (
                      <ScoreBadge backScore={row.finalScore} label={`${formatDisplayScore(row.finalScore)} / 100`} />
                    )}
                  </header>

                  <div className="p-4 sm:p-5">
                    <div className="mb-3.5">
                      <p className="eyebrow">Prompt sent to the model</p>
                      <p className="mt-1.5 whitespace-pre-wrap rounded-xl border border-slate-100 bg-surface-50 p-3.5 text-[13.5px] leading-relaxed text-slate-800">
                        {row?.variantText || "No prompt text stored for this framing."}
                      </p>
                    </div>

                    {row ? (
                      <ResponseCard
                        row={row}
                        isRecommended={
                          row.response?.response_id != null &&
                          String(row.response.response_id) === String(recId)
                        }
                      />
                    ) : (
                      <EmptyState
                        compact
                        title={`${modelName} has no response for ${v.label}`}
                        subtitle="The backend did not store a response for this model and framing combination."
                      />
                    )}
                  </div>
                </section>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
}