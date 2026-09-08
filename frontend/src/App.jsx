import { lazy, Suspense } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import AppLayout from "./components/layout/AppLayout.jsx";
import AuthGuard from "./components/ProtectedRoute.jsx";
import LoginPage from "./pages/LoginPage.jsx";
import SignupPage from "./pages/SignupPage.jsx";
import DashboardPage from "./pages/DashboardPage.jsx";

const SubmissionDetailsPage = lazy(() => import("./pages/SubmissionDetailsPage.jsx"));
const AdminPage = lazy(() => import("./pages/AdminPage.jsx"));

function PageLoader() {
  return (
    <div className="flex items-center justify-center py-24 text-sm text-slate-400">
      Loading…
    </div>
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/signup" element={<SignupPage />} />

      <Route element={<AuthGuard />}>
        <Route element={<AppLayout />}>
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route
            path="/submissions/:id"
            element={
              <Suspense fallback={<PageLoader />}>
                <SubmissionDetailsPage />
              </Suspense>
            }
          />
        </Route>
      </Route>

      <Route element={<AuthGuard allowRoles={["admin", "reviewer"]} />}>
        <Route element={<AppLayout />}>
          <Route
            path="/admin"
            element={
              <Suspense fallback={<PageLoader />}>
                <AdminPage />
              </Suspense>
            }
          />
        </Route>
      </Route>

      <Route path="/" element={<Navigate to="/dashboard" replace />} />
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}