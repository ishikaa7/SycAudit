/**
 * Polished empty / unavailable state.
 * Used for real gaps in the API (no benchmark endpoint, no human-reference
 * metrics, unresolvable recommendation) so those read as designed rather than
 * broken. Never a place to stand in a fabricated value.
 */
export default function EmptyState({
  title = "Nothing here yet",
  subtitle,
  icon = "spark",
  action,
  tone = "neutral",
  compact = false,
}) {
  const toneRing =
    tone === "warning" ? "border-amber-200 bg-amber-50" : "border-slate-200 bg-surface-50";

  return (
    <div
      className={`flex flex-col items-center justify-center rounded-card border border-dashed ${toneRing} text-center ${compact ? "px-5 py-8" : "px-6 py-14"}`}
    >
      <span className="mb-3 grid h-10 w-10 place-items-center rounded-xl border border-slate-200 bg-white text-slate-400 shadow-card">
        <svg
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.6"
          strokeLinecap="round"
          strokeLinejoin="round"
          className="h-[18px] w-[18px]"
          aria-hidden="true"
        >
          {icon === "spark" && <path d="M12 3.5 13.9 9l5.6 1.9-5.6 2L12 18.5 10.1 13l-5.6-2L10.1 9z" />}
          {icon === "chart" && (
            <>
              <path d="M4 19.5h16" />
              <path d="M7 17v-5M12 17V8M17 17v-3" />
            </>
          )}
          {icon === "flag" && (
            <>
              <path d="M6 21V4" />
              <path d="M6 4.8h11l-2.2 3.6L17 12H6z" />
            </>
          )}
          {icon === "alert" && (
            <>
              <path d="M12 4.5 21 20H3z" />
              <path d="M12 10v4M12 17.2v.2" />
            </>
          )}
          {icon === "doc" && (
            <>
              <path d="M6 3.5h8l4 4v13H6z" />
              <path d="M14 3.5v4h4" />
            </>
          )}
        </svg>
      </span>
      <p className="text-[14.5px] font-semibold text-slate-800">{title}</p>
      {subtitle && (
        <p className="mt-1.5 max-w-md text-[13px] leading-relaxed text-slate-500">{subtitle}</p>
      )}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}