/**
 * Model tab bar for Variants & Responses.
 *
 * Options are derived ONLY from submission.variants[].responses[].model.model_name
 * — never from /admin/models and never hardcoded. Models that failed are kept
 * in the list so their error state stays visible.
 */
export default function ModelTabs({ models, active, onChange, counts }) {
  if (!models || models.length === 0) return null;

  if (models.length === 1) {
    const only = models[0];
    return (
      <div className="flex items-center gap-2">
        <span className="text-[13px] font-semibold text-slate-800">{only.name}</span>
        <span className="chip-static">{only.provider}</span>
      </div>
    );
  }

  return (
    <div
      className="scroll-x -mx-1 flex gap-1.5 rounded-xl border border-slate-200 bg-white p-1.5"
      role="tablist"
      aria-label="Models in this submission"
    >
      {models.map((m) => {
        const isActive = m.name === active;
        const count = counts?.[m.name];
        return (
          <button
            key={m.name}
            type="button"
            role="tab"
            aria-selected={isActive}
            onClick={() => onChange(m.name)}
            title={m.name}
            className={`flex shrink-0 items-center gap-1.5 rounded-lg px-3 py-1.5 text-[12.5px] font-semibold transition-all duration-150 ${
              isActive
                ? "bg-indigo-600 text-white shadow-sm"
                : "text-slate-600 hover:bg-surface-200 hover:text-slate-900"
            }`}
          >
            <span className="max-w-[180px] truncate">{m.name}</span>
            {typeof count === "number" && (
              <span
                className={`rounded px-1 text-[10px] font-bold tabular-nums ${
                  isActive ? "bg-white/20 text-white" : "bg-surface-300 text-slate-500"
                }`}
              >
                {count}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}