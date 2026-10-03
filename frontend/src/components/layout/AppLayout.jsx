import { useEffect, useState } from "react";
import { Outlet, useLocation } from "react-router-dom";
import Sidebar from "./Sidebar.jsx";
import TopBar from "./TopBar.jsx";
import { useAuth } from "../../context/AuthContext.jsx";

export default function AppLayout() {
  const { user } = useAuth();
  const [navOpen, setNavOpen] = useState(false);
  const location = useLocation();
  const isAdmin = ["admin", "reviewer"].includes(user?.role);

  // Close the mobile drawer whenever the route changes.
  useEffect(() => {
    setNavOpen(false);
  }, [location.pathname]);

  return (
    <div className="no-overflow flex min-h-screen bg-cream-100">
      {/* Persistent sidebar on large screens */}
      <div className="sticky top-0 hidden h-screen lg:block">
        <Sidebar isAdmin={isAdmin} />
      </div>

      {/* Mobile drawer */}
      {navOpen && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <button
            type="button"
            aria-label="Close navigation"
            onClick={() => setNavOpen(false)}
            className="absolute inset-0 animate-reveal bg-stone-900/25"
          />
          <div className="relative h-full w-[232px] animate-slide-down">
            <Sidebar isAdmin={isAdmin} onNavigate={() => setNavOpen(false)} />
          </div>
        </div>
      )}

      <div className="flex min-w-0 flex-1 flex-col">
        <TopBar onOpenNav={() => setNavOpen(true)} />
        <main className="min-w-0 flex-1 px-4 py-6 sm:px-6 sm:py-8">
          <div className="mx-auto w-full max-w-[1180px]">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}