import { NavLink } from "react-router-dom";

const SECTIONS = [
  { to: "", label: "Final Result", end: true },
  { to: "variants", label: "Variants & Responses" },
  { to: "analysis", label: "Sycophancy Analysis" },
  { to: "metrics", label: "Metrics" },
  { to: "comparison", label: "Comparison" },
];

/** Secondary navigation across the five result sections of one submission. */
export default function SubmissionNav() {
  return (
    <nav
      className="scroll-x -mx-1 mb-6 flex gap-1 rounded-xl border border-stone-200 bg-white p-1.5"
      aria-label="Result sections"
    >
      {SECTIONS.map((s) => (
        <NavLink
          key={s.label}
          to={s.to}
          end={s.end}
          className={({ isActive }) =>
            `shrink-0 rounded-lg px-3 py-1.5 text-[12.5px] font-semibold transition-all duration-150 ${
              isActive
                ? "bg-burgundy-700 text-white shadow-sm"
                : "text-stone-600 hover:bg-cream-200 hover:text-stone-900"
            }`
          }
        >
          {s.label}
        </NavLink>
      ))}
    </nav>
  );
}