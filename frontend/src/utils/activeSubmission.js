/**
 * ACTIVE SUBMISSION â€” one rule, used by the sidebar and the top-level routes.
 *
 * The application has a single active submission:
 *
 *   /submissions/:id/...   -> that submission is active (the URL is the state)
 *   /results, /comparison, /metrics, /analysis
 *                          -> no explicit id, so the latest completed run is
 *                             resolved and the route redirects into
 *                             /submissions/<latest-id>/<section>
 *
 * Two properties fall out of this and are the reason it lives in one place:
 *
 *  - Refreshing keeps the submission. The id is read back out of the URL rather
 *    than held in React state, so a reload of /submissions/123/comparison shows
 *    123 again.
 *  - The sidebar can stay a fixed six items. It simply rewrites its own hrefs to
 *    the active submission when one is open, so moving between sections never
 *    silently drops back to the newest run.
 *
 * These are pure string functions over the pathname: no data, no hooks, so they
 * are unit-testable and cannot drift from the route table in App.jsx.
 */

/** Sidebar destination -> nested route segment. "" is the Results index route. */
export const NAV_TO_SEGMENT = {
  "/results": "",
  "/comparison": "comparison",
  "/metrics": "metrics",
  "/analysis": "analysis",
};

/** Canonical path for one submission's section. */
export function submissionRoute(id, segment) {
  const base = `/submissions/${id}`;
  return segment ? `${base}/${segment}` : base;
}

/**
 * Read the active submission out of a pathname.
 * Returns { id: null, segment: null } on any non-submission route.
 */
export function activeSubmissionFromPath(pathname) {
  const match = /^\/submissions\/([^/]+)(?:\/([^/?#]+))?/.exec(pathname ?? "");
  if (!match) return { id: null, segment: null };
  let id = match[1];
  try {
    id = decodeURIComponent(id);
  } catch {
    /* a malformed id is used verbatim rather than throwing during render */
  }
  return { id, segment: match[2] ?? null };
}

/**
 * Where a sidebar item should point right now.
 *
 * Global items (New Analysis, History) always keep their own path. The four
 * analysis sections are rewritten onto the active submission when one is open,
 * and left at their top-level path when none is, where the route resolves the
 * latest completed run.
 */
export function navTarget(topPath, activeId) {
  const segment = NAV_TO_SEGMENT[topPath];
  if (segment === undefined || !activeId) return topPath;
  return submissionRoute(activeId, segment);
}

/**
 * Whether a sidebar item represents the page currently being viewed, so that
 * /submissions/123/comparison highlights Model Comparison rather than nothing.
 */
export function isNavItemActive(topPath, pathname) {
  if (pathname === topPath) return true;
  const segment = NAV_TO_SEGMENT[topPath];
  if (segment === undefined) return false;
  const active = activeSubmissionFromPath(pathname);
  if (!active.id) return false;
  return (active.segment ?? "") === segment;
}

/**
 * Newest completed submission, from a GET /submissions payload.
 * SubmissionListItem exposes submission_id, original_prompt, status, created_at
 * and updated_at only; runs that have not finished are skipped because they
 * cannot describe an analysis.
 */
export function latestCompletedSubmission(items) {
  if (!Array.isArray(items)) return null;
  return (
    items
      .filter((s) => s?.status === "completed")
      .slice()
      .sort((a, b) => new Date(b?.created_at ?? 0) - new Date(a?.created_at ?? 0))[0] ?? null
  );
}

/** Completed runs, newest first â€” the single list History is allowed to show. */
export function completedSubmissionsNewestFirst(items) {
  if (!Array.isArray(items)) return [];
  return items
    .filter((s) => s?.status === "completed")
    .slice()
    .sort((a, b) => new Date(b?.created_at ?? 0) - new Date(a?.created_at ?? 0));
}
