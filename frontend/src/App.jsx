import { lazy, Suspense } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import AppLayout from "./components/layout/AppLayout.jsx";
import SubmissionLayout from "./components/layout/SubmissionLayout.jsx";
import ActiveSubmissionRoute from "./components/layout/ActiveSubmissionRoute.jsx";
import AuthGuard from "./components/ProtectedRoute.jsx";
import LoginPage from "./pages/LoginPage.jsx";
import SignupPage from "./pages/SignupPage.jsx";
import DashboardPage from "./pages/DashboardPage.jsx";
import Spinner from "./components/ui/Spinner.jsx";

const SubmissionDetailsPage = lazy(() => import("./pages/SubmissionDetailsPage.jsx"));
const VariantsPage = lazy(() => import("./pages/VariantsPage.jsx"));
const AnalysisPage = lazy(() => import("./pages/AnalysisPage.jsx"));
const MetricsPage = lazy(() => import("./pages/MetricsPage.jsx"));
const ComparisonPage = lazy(() => import("./pages/ComparisonPage.jsx"));
const HistoryPage = lazy(() => import("./pages/HistoryPage.jsx"));
const AdminPage = lazy(() => import("./pages/AdminPage.jsx"));
const BenchmarksPage = lazy(() => import("./pages/BenchmarksPage.jsx"));

function PageLoader() {
  return (
    <div className="flex min-h-[40vh] items-center justify-center gap-2.5 text-sm text-slate-400">
      <Spinner className="h-4 w-4 text-indigo-700" />
      Loading…
    </div>
  );
}

const withLoader = (element) => <Suspense fallback={<PageLoader />}>{element}</Suspense>;

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/signup" element={<SignupPage />} />

      <Route element={<AuthGuard />}>
        <Route element={<AppLayout />}>
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route
            path="/results"
            element={
              <ActiveSubmissionRoute
                segment=""
                eyebrow="Overview"
                title="Results"
                subtitle="The recommended response for your most recent completed analysis."
                icon="check"
              />
            }
          />
          <Route
            path="/comparison"
            element={
              <ActiveSubmissionRoute
                segment="comparison"
                eyebrow="Model comparison"
                title="Model Comparison"
                subtitle="Compare how each model responded within a single analysis."
              />
            }
          />
          <Route
            path="/metrics"
            element={
              <ActiveSubmissionRoute
                segment="metrics"
                eyebrow="Metrics & evaluation"
                title="Metrics"
                subtitle="Evaluator-quality metrics for the active analysis."
                icon="gauge"
              />
            }
          />
          <Route
            path="/analysis"
            element={
              <ActiveSubmissionRoute
                segment="analysis"
                eyebrow="Sycophancy analysis"
                title="Sycophancy Analysis"
                subtitle="Detailed analysis of model behaviour for the active analysis."
                icon="search"
              />
            }
          />
          <Route path="/history" element={withLoader(<HistoryPage />)} />
          <Route path="/benchmarks" element={withLoader(<BenchmarksPage />)} />

          <Route element={<SubmissionLayout />}>
            <Route path="/submissions/:id" element={withLoader(<SubmissionDetailsPage />)} />
            <Route path="/submissions/:id/variants" element={withLoader(<VariantsPage />)} />
            <Route path="/submissions/:id/analysis" element={withLoader(<AnalysisPage />)} />
            <Route path="/submissions/:id/metrics" element={withLoader(<MetricsPage />)} />
            <Route path="/submissions/:id/comparison" element={withLoader(<ComparisonPage />)} />
          </Route>
        </Route>
      </Route>

      <Route element={<AuthGuard allowRoles={["admin", "reviewer"]} />}>
        <Route element={<AppLayout />}>
          <Route path="/admin" element={withLoader(<AdminPage />)} />
        </Route>
      </Route>

      <Route path="/" element={<Navigate to="/dashboard" replace />} />
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}


