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

// Submission / analysis pages
const SubmissionDetailsPage = lazy(
  () => import("./pages/SubmissionDetailsPage.jsx")
);
const VariantsPage = lazy(() => import("./pages/VariantsPage.jsx"));
const ComparisonPage = lazy(() => import("./pages/ComparisonPage.jsx"));
const HistoryPage = lazy(() => import("./pages/HistoryPage.jsx"));
const MetricsPage = lazy(() => import("./pages/MetricsPage.jsx"));
const BenchmarksPage = lazy(() => import("./pages/BenchmarksPage.jsx"));
          <Route
            path="/response-comparison"
            element={<ActiveSubmissionRoute segment="response-comparison" eyebrow="Response Analysis" title="Response Analysis" subtitle="Analyze individual responses." icon="chart" />}
          />
const AdminPage = lazy(() => import("./pages/AdminPage.jsx"));

// IMPORTANT:
// ResponseComparisonPage is now the individual Response Analysis page.
// It receives the real submission from SubmissionLayout.
const ResponseComparisonPage = lazy(
  () => import("./pages/ResponseComparisonPage.jsx")
);

function PageLoader() {
  return (
    <div className="flex min-h-[40vh] items-center justify-center gap-2.5 text-sm text-slate-400">
      <Spinner className="h-4 w-4 text-indigo-700" />
      Loading…
    </div>
  );
}

const withLoader = (element) => (
  <Suspense fallback={<PageLoader />}>
    {element}
  </Suspense>
);

export default function App() {
  return (
    <Routes>
      {/* =========================================================
          PUBLIC ROUTES
      ========================================================= */}

      <Route path="/login" element={<LoginPage />} />
      <Route path="/signup" element={<SignupPage />} />

      {/* =========================================================
          AUTHENTICATED APPLICATION
      ========================================================= */}

      <Route element={<AuthGuard />}>
        <Route element={<AppLayout />}>

          {/* =====================================================
              DASHBOARD
          ===================================================== */}

          <Route
            path="/dashboard"
            element={<DashboardPage />}
          />

          {/* =====================================================
              ACTIVE SUBMISSION SHORTCUT ROUTES

              These routes work with whichever submission is
              currently active.
          ===================================================== */}

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

          {/* =====================================================
              HISTORY
          ===================================================== */}

          <Route
            path="/history"
            element={withLoader(<HistoryPage />)}
          />

          {/* =====================================================
              BENCHMARKS
          ===================================================== */}

          <Route
            path="/benchmarks"
            element={withLoader(<BenchmarksPage />)}
          />

          {/* =====================================================
              SUBMISSION-SPECIFIC ROUTES

              IMPORTANT:
              Everything inside SubmissionLayout receives the
              actual submission through useSubmissionContext().
          ===================================================== */}

          <Route element={<SubmissionLayout />}>

            {/* ---------------------------------------------------
                SUBMISSION RESULTS
                /submissions/:id
            --------------------------------------------------- */}

            <Route
              path="/submissions/:id"
              element={withLoader(<SubmissionDetailsPage />)}
            />

            {/* ---------------------------------------------------
                PROMPT VARIANTS
                /submissions/:id/variants
            --------------------------------------------------- */}

            <Route
              path="/submissions/:id/variants"
              element={withLoader(<VariantsPage />)}
            />

            {/* ---------------------------------------------------
                RESPONSE ANALYSIS
                /submissions/:id/analysis

                This is now the page with:

                Response A / B / C selector
                ↓
                Selected response
                ↓
                Real F1–F5
                ↓
                WOBBLE
                ↓
                Severity
                ↓
                Rank
            --------------------------------------------------- */}

            <Route
              path="/submissions/:id/analysis"
              element={withLoader(<ResponseComparisonPage />)}
            />

            {/* ---------------------------------------------------
                MODEL COMPARISON
                /submissions/:id/comparison

                This is the separate page for comparing multiple
                models/responses side-by-side.
            --------------------------------------------------- */}

            <Route
              path="/submissions/:id/comparison"
              element={withLoader(<ComparisonPage />)}
            />

            {/* ---------------------------------------------------
                METRICS
                /submissions/:id/metrics
            --------------------------------------------------- */}

            <Route
              path="/submissions/:id/metrics"
              element={withLoader(<MetricsPage />)}
            />
          </Route>
        </Route>
      </Route>

      {/* =========================================================
          ADMIN / REVIEWER
      ========================================================= */}

      <Route element={<AuthGuard allowRoles={["admin", "reviewer"]} />}>
        <Route element={<AppLayout />}>
          <Route
            path="/admin"
            element={withLoader(<AdminPage />)}
          />
        </Route>
      </Route>

      {/* =========================================================
          DEFAULT ROUTES
      ========================================================= */}

      <Route
        path="/"
        element={<Navigate to="/dashboard" replace />}
      />

      <Route
        path="*"
        element={<Navigate to="/dashboard" replace />}
      />
    </Routes>
  );
}

