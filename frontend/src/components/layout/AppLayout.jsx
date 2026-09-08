import { Outlet } from "react-router-dom";
import Navbar from "./Navbar.jsx";

export default function AppLayout() {
  return (
    <div className="flex min-h-screen flex-col">
      <Navbar />
      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-6 sm:px-6 sm:py-10">
        <Outlet />
      </main>
      <footer className="border-t border-slate-200 py-6 text-center text-xs text-slate-400">
        SycAudit — AI sycophancy auditing
      </footer>
    </div>
  );
}