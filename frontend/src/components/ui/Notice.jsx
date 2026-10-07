/** Small explanatory notice for genuine API limitations. */
export default function Notice({ tone = "info", title, children, className = "" }) {
  const tones = {
    info: "border-slate-200 bg-surface-50 text-slate-600",
    warning: "border-amber-200 bg-amber-50 text-amber-900",
    danger: "border-red-200 bg-red-50 text-red-800",
  };
  return (
    <div className={`flex gap-2.5 rounded-xl border px-3.5 py-3 ${tones[tone]} ${className}`}>
      <svg
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.7"
        strokeLinecap="round"
        strokeLinejoin="round"
        className="mt-px h-4 w-4 shrink-0 opacity-70"
        aria-hidden="true"
      >
        <circle cx="12" cy="12" r="8.6" />
        <path d="M12 11.2v5M12 8.1v.2" />
      </svg>
      <div className="min-w-0 text-[12.5px] leading-relaxed">
        {title && <p className="font-semibold">{title}</p>}
        <div className={title ? "mt-0.5" : ""}>{children}</div>
      </div>
    </div>
  );
}