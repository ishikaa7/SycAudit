/**
 * Compact dropdown used by Sycophancy Analysis for both the model selector and
 * the variant selector.
 *
 * Options are always built by the caller from the active submission, so a name
 * can only appear here if that model or variant has a real scored response in
 * this analysis. Nothing is invented, and when there is nothing to choose the
 * control renders an explicit N/A rather than an empty select.
 */
export default function ModelSelect({ options = [], value, onChange, id, label }) {
  if (!options.length) {
    return (
      <span className="inline-flex items-center rounded-xl border border-slate-200 bg-surface-50 px-3 py-2 text-[12.5px] font-medium text-slate-400">
        N/A
      </span>
    );
  }

  return (
    <div className="relative">
      <select
        id={id}
        aria-label={label}
        value={value ?? ""}
        onChange={(e) => onChange(e.target.value)}
        className="min-w-[190px] cursor-pointer appearance-none rounded-xl border border-slate-200 bg-white py-2 pl-3 pr-9 text-[13px] font-semibold text-slate-800 transition-all duration-150 hover:border-slate-300 focus:border-indigo-300"
      >
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
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
        className="pointer-events-none absolute right-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-400"
        aria-hidden="true"
      >
        <path d="m6 9 6 6 6-6" />
      </svg>
    </div>
  );
}