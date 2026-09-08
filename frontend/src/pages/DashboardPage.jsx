import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { createSubmission, getSubmission, getSubmissions } from "../api/submissions.js";
import { errorMessage } from "../api/client.js";
import { formatDateTime, normalizeList, truncate } from "../utils/format.js";
import StatusBadge from "../components/ui/StatusBadge.jsx";
import Spinner from "../components/ui/Spinner.jsx";
import usePolling from "../hooks/usePolling.js";

export default function DashboardPage() {
  const navigate = useNavigate();

  const [submissions, setSubmissions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [listError, setListError] = useState("");

  const [prompt, setPrompt] = useState("");
  const [promptError, setPromptError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState("");

  const loadList = useCallback(async (silent = false) => {
    if (!silent) setLoading(true);
    try {
      const res = await getSubmissions();
      setSubmissions(normalizeList(res.data));
      setListError("");
    } catch (err) {
      if (!silent) setListError(errorMessage(err));
    } finally {
      if (!silent) setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadList();
  }, [loadList]);

  const activeIds = submissions
    .filter((s) => s?.status === "pending" || s?.status === "processing")
    .map((s) => s.submission_id);

  const refreshActive = useCallback(async () => {
    if (activeIds.length === 0) return;
    const results = await Promise.allSettled(activeIds.map((id) => getSubmission(id)));
    setSubmissions((prev) => {
      const byId = new Map(prev.map((s) => [s.submission_id, s]));
      results.forEach((result) => {
        if (result.status === "fulfilled" && result.value?.data?.submission_id) {
          byId.set(result.value.data.submission_id, result.value.data);
        }
      });
      return Array.from(byId.values());
    });
  }, [activeIds]);

  usePolling(refreshActive, { enabled: activeIds.length > 0, delay: 4000 });

  const handleSubmit = async (e) => {
    e.preventDefault();
    const text = prompt.trim();
    if (!text) {
      setPromptError("Enter a prompt or statement to audit.");
      return;
    }
    setPromptError("");
    setSubmitError("");
    setSubmitting(true);
    try {
      const res = await createSubmission(text);
      const id = res.data?.submission_id;
      if (id) {
        navigate(`/submissions/${id}`);
        return;
      }
      await loadList(true);
      setPrompt("");
    } catch (err) {
      setSubmitError(errorMessage(err));
    } finally {
      setSubmitting(false);
    }
  };

  const sorted = [...submissions].sort(
    (a, b) => new Date(b.created_at ?? 0) - new Date(a.created_at ?? 0)
  );

  return (
    <div className="space-y-8">
      <section className="rounded-2xl bg-white p-5 shadow-sm ring-1 ring-slate-200 sm:p-6">
        <h2 className="text-base font-semibold text-slate-900">New submission</h2>
        <p className="mt-1 max-w-2xl text-sm text-slate-500">
          Paste a prompt or statement, and SycAudit will rewrite it into four framings,
          score responses from several models for sycophancy, and report the least
          sycophantic answer.
        </p>
        <form onSubmit={handleSubmit} className="mt-4">
          <label htmlFor="prompt" className="sr-only">
            Prompt to audit
          </label>
          <textarea
            id="prompt"
            value={prompt}
            onChange={(e) => {
              setPrompt(e.target.value);
              setPromptError("");
              setSubmitError("");
            }}
            rows={4}
            placeholder="e.g. My startup idea is definitely going to change the world, right?"
            className={`block w-full rounded-xl border bg-white px-3.5 py-3 text-sm text-slate-900 shadow-sm outline-none transition-colors placeholder:text-slate-400 focus:ring-2 ${
              promptError
                ? "border-red-300 focus:border-red-400 focus:ring-red-200"
                : "border-slate-200 focus:border-brand-500 focus:ring-brand-200"
            }`}
          />
          {promptError && <p className="mt-1.5 text-xs text-red-600">{promptError}</p>}
          {submitError && (
            <p className="mt-1.5 text-xs text-red-600">{submitError}</p>
          )}
          <div className="mt-4 flex items-center justify-between gap-4">
            <p className="text-xs text-slate-400">Submissions are audited in the background.</p>
            <button
              type="submit"
              disabled={submitting || !prompt.trim()}
              className="inline-flex shrink-0 items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-brand-700 focus:outline-none focus:ring-2 focus:ring-brand-400 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {submitting ? <Spinner className="h-4 w-4" /> : (
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="h-4 w-4">
                  <path d="M5 12h14" />
                  <path d="m12 5 7 7-7 7" />
                </svg>
              )}
              {submitting ? "Submitting…" : "Audit prompt"}
            </button>
          </div>
        </form>
      </section>

      <section>
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-base font-semibold text-slate-900">Past submissions</h2>
          {activeIds.length > 0 && (
            <span className="inline-flex items-center gap-1.5 text-xs text-amber-600">
              <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-amber-500" />
              {activeIds.length} running
            </span>
          )}
        </div>

        {loading ? (
          <div className="flex items-center justify-center rounded-xl bg-white py-12 text-slate-400 shadow-sm ring-1 ring-slate-200">
            <Spinner className="h-6 w-6" />
          </div>
        ) : listError ? (
          <div className="rounded-xl bg-red-50 px-4 py-8 text-center text-sm text-red-700 ring-1 ring-inset ring-red-200">
            Could not load submissions — {listError}
          </div>
        ) : sorted.length === 0 ? (
          <div className="rounded-xl bg-white px-6 py-12 text-center shadow-sm ring-1 ring-slate-200">
            <p className="text-sm font-medium text-slate-700">No submissions yet</p>
            <p className="mt-1 text-sm text-slate-400">
              Create your first one above — results appear here as they complete.
            </p>
          </div>
        ) : (
          <ul className="flex flex-col gap-3">
            {sorted.map((submission) => (
              <li key={submission.submission_id}>
                <button
                  type="button"
                  onClick={() => navigate(`/submissions/${submission.submission_id}`)}
                  className="group flex w-full items-center gap-4 rounded-xl bg-white p-4 text-left shadow-sm ring-1 ring-slate-200 transition-all hover:ring-brand-300 hover:shadow-md"
                >
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium text-slate-800 group-hover:text-brand-700">
                      {submission.original_prompt || "Untitled prompt"}
                    </p>
                    <p className="mt-1 text-xs text-slate-400">
                      {formatDateTime(submission.created_at)}
                    </p>
                  </div>
                  <StatusBadge status={submission.status} className="shrink-0" />
                  <svg
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    className="h-4 w-4 shrink-0 text-slate-300 transition-colors group-hover:text-brand-600"
                    aria-hidden="true"
                  >
                    <path d="m9 18 6-6-6-6" />
                  </svg>
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}