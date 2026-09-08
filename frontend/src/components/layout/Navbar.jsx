import { Link, NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "../../context/AuthContext.jsx";
import { initials } from "../../utils/format.js";
import { useState } from "react";

function Logo() {
  return (
    <span className="grid h-8 w-8 place-items-center rounded-lg bg-brand-600 text-white shadow-sm">
      <svg
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        className="h-4 w-4"
        aria-hidden="true"
      >
        <path d="M7 17V9.5a3.5 3.5 0 0 1 7 0V17" />
        <path d="M7 13h7" />
        <path d="M9 22h6" />
        <path d="M12 15v3" />
        <path d="M20 12c0-4.4-3.6-8-8-8S4 7.6 4 12" />
      </svg>
    </span>
  );
}

const linkBase =
  "rounded-lg px-3 py-2 text-sm font-medium transition-colors hidden sm:inline-block";

export default function Navbar() {
  const { user, signout } = useAuth();
  const navigate = useNavigate();
  const [busy, setBusy] = useState(false);

  const isAdmin = ["admin", "reviewer"].includes(user?.role);

  const handleLogout = async () => {
    setBusy(true);
    signout();
    navigate("/login", { replace: true });
  };

  return (
    <header className="sticky top-0 z-40 border-b border-slate-200/70 bg-white/85 backdrop-blur-md">
      <nav className="mx-auto flex h-16 w-full max-w-6xl items-center justify-between gap-4 px-4 sm:px-6">
        <Link to="/dashboard" className="flex items-center gap-2.5">
          <Logo />
          <span className="text-lg font-semibold tracking-tight text-slate-900">
            SycAudit
          </span>
        </Link>

        <div className="flex items-center gap-1 sm:gap-2">
          <NavLink
            to="/dashboard"
            className={({ isActive }) =>
              `${linkBase} ${
                isActive
                  ? "bg-brand-50 text-brand-700"
                  : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
              }`
            }
          >
            Dashboard
          </NavLink>
          {isAdmin && (
            <NavLink
              to="/admin"
              className={({ isActive }) =>
                `${linkBase} ${
                  isActive
                    ? "bg-brand-50 text-brand-700"
                    : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
                }`
              }
            >
              Model Health
            </NavLink>
          )}

          <div className="ml-2 flex items-center gap-3 border-l border-slate-200 pl-3 sm:pl-4">
            <div className="flex items-center gap-2">
              <span className="grid h-8 w-8 shrink-0 place-items-center rounded-full bg-brand-50 text-xs font-semibold text-brand-700 ring-1 ring-inset ring-brand-100">
                {initials(user?.name || user?.email)}
              </span>
              <span className="hidden max-w-[180px] truncate text-sm text-slate-600 md:block">
                {user?.email}
              </span>
            </div>
            <button
              type="button"
              onClick={handleLogout}
              disabled={busy}
              className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-50 hover:text-slate-900 disabled:opacity-60"
            >
              Log out
            </button>
          </div>
        </div>
      </nav>
    </header>
  );
}