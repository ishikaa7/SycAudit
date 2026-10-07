import { Link, useNavigate } from "react-router-dom";
import { useEffect, useRef, useState } from "react";
import { useAuth } from "../../context/AuthContext.jsx";
import { initials } from "../../utils/format.js";

export default function TopBar({ onOpenNav }) {
  const { user, signout } = useAuth();
  const navigate = useNavigate();
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef(null);

  // Close on outside pointerdown. Deliberately NOT onBlur: blurring the trigger
  // unmounts the menu before the browser finishes the click, which swallows the
  // click on the menu items.
  useEffect(() => {
    if (!menuOpen) return undefined;
    const onPointerDown = (e) => {
      if (menuRef.current && !menuRef.current.contains(e.target)) setMenuOpen(false);
    };
    const onKeyDown = (e) => {
      if (e.key === "Escape") setMenuOpen(false);
    };
    document.addEventListener("pointerdown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("pointerdown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [menuOpen]);

  const handleLogout = () => {
    setMenuOpen(false);
    signout();
    navigate("/login", { replace: true });
  };

  const displayName = user?.name || user?.email || "Account";
  const isAdmin = ["admin", "reviewer"].includes(user?.role);

  return (
    <header className="sticky top-0 z-30 flex h-14 shrink-0 items-center justify-between gap-3 border-b border-slate-200/80 bg-white/90 px-4 backdrop-blur-md sm:px-6">
      <div className="flex min-w-0 items-center gap-2.5">
        <button
          type="button"
          onClick={onOpenNav}
          aria-label="Open navigation"
          className="btn-ghost -ml-1 !px-2 lg:hidden"
        >
          <svg
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.9"
            strokeLinecap="round"
            className="h-5 w-5"
            aria-hidden="true"
          >
            <path d="M4 7h16M4 12h16M4 17h16" />
          </svg>
        </button>

        <Link to="/dashboard" className="flex items-center gap-2 lg:hidden">
          <span className="grid h-7 w-7 place-items-center rounded-[9px] bg-indigo-600 text-white">
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
              <path d="M12 3.2 20 6.4v5.3c0 4.4-3.3 7.6-8 9.1-4.7-1.5-8-4.7-8-9.1V6.4z" />
            </svg>
          </span>
          <span className="text-sm font-bold tracking-tight text-slate-900">SycAudit</span>
        </Link>
      </div>

      <div className="flex items-center gap-2.5">
        {isAdmin && (
          <Link to="/admin" className="hidden text-xs font-medium text-slate-400 hover:text-slate-700 sm:block">
            Model Health
          </Link>
        )}

        <div className="relative" ref={menuRef}>
          <button
            type="button"
            onClick={() => setMenuOpen((v) => !v)}
            aria-haspopup="menu"
            aria-expanded={menuOpen}
            className="flex items-center gap-2 rounded-xl border border-slate-200 bg-surface-50 py-1 pl-1 pr-2.5 transition-all duration-150 hover:border-slate-300"
          >
            <span className="grid h-7 w-7 place-items-center rounded-lg bg-indigo-50 text-[11px] font-bold text-indigo-700">
              {initials(user?.name || user?.email)}
            </span>
            <span className="hidden max-w-[150px] truncate text-[13px] font-medium text-slate-700 sm:block">
              {displayName}
            </span>
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              className="h-3.5 w-3.5 text-slate-400"
              aria-hidden="true"
            >
              <path d="m6 9 6 6 6-6" />
            </svg>
          </button>

          {menuOpen && (
            <div
              role="menu"
              className="absolute right-0 z-40 mt-2 w-56 animate-slide-down rounded-xl border border-slate-200 bg-white p-1.5 shadow-panel"
            >
              <div className="border-b border-slate-100 px-3 py-2.5">
                <p className="truncate text-[13px] font-semibold text-slate-800">{displayName}</p>
                {user?.email && (
                  <p className="truncate text-xs text-slate-400">{user.email}</p>
                )}
                {user?.role && (
                  <p className="mt-1 inline-flex rounded-md bg-surface-200 px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-slate-500">
                    {user.role}
                  </p>
                )}
              </div>
              <button
                type="button"
                role="menuitem"
                onClick={handleLogout}
                className="mt-1 flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-[13px] font-medium text-slate-600 transition-colors hover:bg-indigo-50 hover:text-indigo-800"
              >
                <svg
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.8"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  className="h-4 w-4"
                  aria-hidden="true"
                >
                  <path d="M15 5V4.5A1.5 1.5 0 0 0 13.5 3h-7A1.5 1.5 0 0 0 5 4.5v15A1.5 1.5 0 0 0 6.5 21h7a1.5 1.5 0 0 0 1.5-1.5V19" />
                  <path d="M10 12h10m0 0-3-3m3 3-3 3" />
                </svg>
                Log out
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}