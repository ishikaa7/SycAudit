import FacetBars from "../ui/FacetBars.jsx";
import FacetRadar from "../ui/FacetRadar.jsx";
import { getModelInfo, formatScore } from "../../utils/format.js";
import { scoreText } from "../../utils/constants.js";

const providerTone = {
  groq: "bg-fuchsia-50 text-fuchsia-700 ring-fuchsia-200",
  gemini: "bg-sky-50 text-sky-700 ring-sky-200",
  huggingface: "bg-amber-50 text-amber-700 ring-amber-200",
  openai: "bg-emerald-50 text-emerald-700 ring-emerald-200",
  anthropic: "bg-orange-50 text-orange-700 ring-orange-200",
};

function providerBadge(provider) {
  return providerTone[provider] ?? "bg-slate-100 text-slate-600 ring-slate-200";
}

export default function ResponseCard({ response, recommended = false }) {
  const model = getModelInfo(response);
  const status = response?.status;
  const failed = status === "failed" || status === "timeout";
  const score = response?.score;
  const finalScore = typeof score?.final_score === "number" ? score.final_score : null;

  return (
    <article
      className={`rounded-xl bg-white p-4 shadow-sm transition-shadow ${
        recommended
          ? "ring-2 ring-brand-500 shadow-brand-100"
          : "ring-1 ring-slate-200"
      }`}
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap items-center gap-2">
          <span
            className={`inline-flex items-center gap-1.5 rounded-md px-2 py-1 text-xs font-medium ring-1 ring-inset ${providerBadge(model.provider)}`}
          >
            <span className="capitalize">{model.provider}</span>
          </span>
          <span className="text-sm font-semibold text-slate-800">{model.name}</span>
          {recommended && (
            <span className="inline-flex items-center gap-1 rounded-full bg-brand-600 px-2.5 py-1 text-xs font-semibold text-white shadow-sm">
              <svg viewBox="0 0 24 24" fill="currentColor" className="h-3.5 w-3.5" aria-hidden="true">
                <path d="M12 2l2.9 6.3 6.9.8-5.1 4.7 1.4 6.8L12 17.2 5.9 20.6l1.4-6.8L2.2 9.1l6.9-.8L12 2z" />
              </svg>
              Recommended · Least sycophantic
            </span>
          )}
        </div>

        {finalScore !== null && (
          <div className="flex items-baseline gap-1.5">
            <span className={`text-2xl font-bold tabular-nums ${scoreText(finalScore)}`}>
              {formatScore(finalScore)}
            </span>
            <span className="text-xs text-slate-400">/ 5 sycophancy</span>
          </div>
        )}
      </div>

      {failed ? (
        <div className="mt-3 rounded-lg bg-red-50 px-3 py-2.5 text-sm text-red-700">
          This model call failed
          {response?.error_message ? ` — ${response.error_message}` : ""}.
        </div>
      ) : (
        response?.response_text && (
          <p className="mt-3 whitespace-pre-wrap rounded-lg bg-slate-50 p-3 text-sm leading-relaxed text-slate-700">
            {response.response_text}
          </p>
        )
      )}

      {score && !failed && (
        <div className="mt-4 border-t border-slate-100 pt-4">
          <div className="grid gap-5 md:grid-cols-[190px_1fr] md:items-center">
            <div className="hidden md:block">
              <FacetRadar score={score} finalScore={finalScore ?? 0} />
            </div>
            <div className="md:pl-2">
              <FacetBars score={score} />
            </div>
          </div>

          {(typeof score.ml_score === "number" ||
            typeof score.rule_adjustment === "number" ||
            typeof score.confidence === "number") && (
            <div className="mt-3 flex flex-wrap gap-x-5 gap-y-1 text-xs text-slate-400">
              {typeof score.ml_score === "number" && (
                <span>
                  ml_score <span className="font-semibold text-slate-600">{formatScore(score.ml_score)}</span>
                </span>
              )}
              {typeof score.rule_adjustment === "number" && (
                <span>
                  rule_adjustment{" "}
                  <span className="font-semibold text-slate-600">
                    {score.rule_adjustment > 0 ? "+" : ""}
                    {formatScore(score.rule_adjustment)}
                  </span>
                </span>
              )}
              {typeof score.confidence === "number" && (
                <span>
                  confidence{" "}
                  <span className="font-semibold text-slate-600">
                    {formatScore(score.confidence * 100, 0)}%
                  </span>
                </span>
              )}
            </div>
          )}
        </div>
      )}
    </article>
  );
}