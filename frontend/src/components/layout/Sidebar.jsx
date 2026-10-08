import { Link, NavLink, useLocation } from "react-router-dom";
import NAV, { NavIcon } from "./navItems.jsx";
import {
  activeSubmissionFromPath,
  isNavItemActive,
  navTarget,
} from "../../utils/activeSubmission.js";

function BrandMark() {
  return (
    <span className="grid h-8 w-8 shrink-0 place-items-center rounded-[10px] bg-indigo-600 text-white shadow-sm">
      <svg
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.9"
        strokeLinecap="round"
        strokeLinejoin="round"
        className="h-[18px] w-[18px]"
        aria-hidden="true"
      >
        <path d="M12 3.2 20 6.4v5.3c0 4.4-3.3 7.6-8 9.1-4.7-1.5-8-4.7-8-9.1V6.4z" />
        <path d="m9.2 12.1 2 2 3.6-4" />
      </svg>
    </span>
  );
}

/** Small branded card with a minimal abstract wave. Deliberately understated. */
function BrandCard() {
  return (
    <div className="relative overflow-hidden rounded-xl bg-indigo-600 p-3.5 text-white">
      <svg
        viewBox="0 0 160 48"
        className="absolute inset-x-0 bottom-0 h-10 w-full opacity-25"
        preserveAspectRatio="none"
        aria-hidden="true"
      >
        <path
          d="M0 30 Q 20 14 40 24 T 80 20 T 120 30 T 160 18"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.4"
        />
        <path
          d="M0 40 Q 24 26 46 34 T 92 30 T 138 38 T 160 30"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.2"
        />
      </svg>
      <p className="relative text-[12.5px] font-semibold leading-snug">
        Detect Sycophancy.
        <br />
        See the Truth.
      </p>
    </div>
  );
}

export default function Sidebar({ isAdmin, onNavigate }) {
  const { pathname } = useLocation();

  // The active submission is read from the URL, not from React state, so it
  // survives a refresh. While one is open, the four analysis items point at its
  // own sections — that is what keeps navigation from silently snapping back to
  // the newest run. The item set itself is identical either way.
  const activeId = activeSubmissionFromPath(pathname).id;

  return (
    <aside className="flex h-full w-[232px] shrink-0 flex-col border-r border-slate-200/80 bg-white">
      <div className="flex items-center gap-2.5 px-4 py-4">
        <BrandMark />
        <span className="text-[15px] font-bold tracking-tight text-slate-900">SycAudit</span>
      </div>

      <nav className="flex-1 space-y-0.5 px-2.5 py-2" aria-label="Main">
        {NAV.map((item) => (
          <Link
            key={item.to}
            to={navTarget(item.to, activeId)}
            onClick={onNavigate}
            className={`nav-item ${isNavItemActive(item.to, pathname) ? "nav-item-active" : ""}`}
          >
            <NavIcon name={item.icon} />
            <span className="truncate">{item.label}</span>
          </Link>
        ))}

        {isAdmin && (
          <NavLink
            to="/admin"
            onClick={onNavigate}
            className={({ isActive }) => `nav-item ${isActive ? "nav-item-active" : ""}`}
          >
            <NavIcon name="flag" />
            <span className="truncate">Model Health</span>
          </NavLink>
        )}
      </nav>

      <div className="p-3">
        <BrandCard />
      </div>
    </aside>
  );
}