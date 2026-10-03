/**
 * Model dropdown for Sycophancy Analysis and Model Comparison.
 * Options come only from the current submission's responses.
 */
export default function ModelSelect({ models, value, onChange, label = "Model", id = "model-select" }) {
  if (!models || models.length === 0) {
    return (
      <div className="flex items-center gap-2">
        <span className="text-xs font-medium text-stone-500">{label}</span>
        <span className="rounded-xl border border-stone-200 bg-white px-3 py-2 text-[13px] text-stone-400">
          N/A
        </span>
      </div>
    );
  }

  return (
    <div className="flex items-center gap-2">
      <label htmlFor={id} className="text-xs font-medium text-stone-500">
        {label}
      </label>
      <div className="relative">
        <select
          id={id}
          value={value ?? ""}
          onChange={(e) => onChange(e.target.value)}
          className="w-full min-w-[220px] cursor-pointer appearance-none rounded-xl border border-stone-200 bg-white py-2 pl-3 pr-9 text-[13px] font-semibold text-stone-800 transition-all duration-150 hover:border-stone-300 focus:border-burgundy-300"
        >
          {models.map((m) => (
            <option key={m.name} value={m.name}>
              {m.name}
            </option>
          ))}
        </select>
        <svg
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          className="pointer-events-none absolute right-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-stone-400"
          aria-hidden="true"
        >
          <path d="m6 9 6 6 6-6" />
        </svg>
      </div>
    </div>
  );
}