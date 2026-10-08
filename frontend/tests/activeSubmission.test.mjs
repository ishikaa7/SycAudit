/**
 * Verifies the active-submission rules in utils/activeSubmission.js.
 *
 * These are the guarantees the whole navigation architecture rests on:
 * History is the only list, the URL is the source of truth for the active
 * submission, and navigating between sections never drops back to the newest run.
 *
 * Run with: npm test. Plain assertions, no framework installed.
 */
import assert from "node:assert/strict";
import {
  NAV_TO_SEGMENT,
  activeSubmissionFromPath,
  completedSubmissionsNewestFirst,
  isNavItemActive,
  latestCompletedSubmission,
  navTarget,
  submissionRoute,
} from "../src/utils/activeSubmission.js";

let passed = 0;
function check(name, fn) {
  try {
    fn();
    passed++;
    console.log(`  ok  ${name}`);
  } catch (err) {
    console.error(`  FAIL  ${name}`);
    console.error(String(err.message).split("\n").slice(0, 12).join("\n"));
    process.exitCode = 1;
  }
}

console.log("\n-- active submission is read from the URL --");
check("a submission path yields its id and section", () => {
  assert.deepEqual(activeSubmissionFromPath("/submissions/123/comparison"), {
    id: "123",
    segment: "comparison",
  });
});
check("the bare submission path is the Results section", () => {
  assert.deepEqual(activeSubmissionFromPath("/submissions/123"), { id: "123", segment: null });
});
check("a trailing slash is still Results", () => {
  assert.deepEqual(activeSubmissionFromPath("/submissions/123/"), { id: "123", segment: null });
});
check("a real uuid segment is read whole", () => {
  const uuid = "3f6c1d2e-9b44-4a1f-8c77-2b0e5a91d3aa";
  assert.equal(activeSubmissionFromPath(`/submissions/${uuid}/analysis`).id, uuid);
});
check("non-submission routes report no active submission", () => {
  ["/results", "/history", "/dashboard", "/", ""].forEach((p) => {
    assert.deepEqual(activeSubmissionFromPath(p), { id: null, segment: null });
  });
});
check("a path that merely contains /submissions is not treated as one", () => {
  assert.deepEqual(activeSubmissionFromPath("/help/submissions/123"), {
    id: null,
    segment: null,
  });
});
check("a query string or hash does not leak into the id", () => {
  assert.equal(activeSubmissionFromPath("/submissions/123/analysis?tab=2").id, "123");
  assert.equal(activeSubmissionFromPath("/submissions/123/analysis#top").id, "123");
});
check("a malformed percent-escape does not throw during render", () => {
  assert.equal(activeSubmissionFromPath("/submissions/%E0%A4%A").id, "%E0%A4%A");
});

console.log("\n-- canonical submission routes --");
check("each section maps to its nested route", () => {
  assert.equal(submissionRoute("123", ""), "/submissions/123");
  assert.equal(submissionRoute("123", "comparison"), "/submissions/123/comparison");
  assert.equal(submissionRoute("123", "analysis"), "/submissions/123/analysis");
});
check("the sidebar sections map onto the existing route table", () => {
  assert.deepEqual(NAV_TO_SEGMENT, {
    "/results": "",
    "/comparison": "comparison",
    "/metrics": "metrics",
    "/analysis": "analysis",
  });
});

console.log("\n-- sidebar hrefs follow the active submission --");
check("with a submission open, sections point at that submission", () => {
  assert.equal(navTarget("/results", "123"), "/submissions/123");
  assert.equal(navTarget("/comparison", "123"), "/submissions/123/comparison");
  assert.equal(navTarget("/metrics", "123"), "/submissions/123/metrics");
  assert.equal(navTarget("/analysis", "123"), "/submissions/123/analysis");
});
check("with no submission open, sections keep their top-level path", () => {
  assert.equal(navTarget("/results", null), "/results");
  assert.equal(navTarget("/comparison", null), "/comparison");
});
check("New Analysis and History never become submission-scoped", () => {
  assert.equal(navTarget("/dashboard", "123"), "/dashboard");
  assert.equal(navTarget("/history", "123"), "/history");
});

console.log("\n-- sidebar highlight follows the current page --");
check("a nested section highlights its own item", () => {
  assert.equal(isNavItemActive("/comparison", "/submissions/123/comparison"), true);
  assert.equal(isNavItemActive("/metrics", "/submissions/123/metrics"), true);
  assert.equal(isNavItemActive("/analysis", "/submissions/123/analysis"), true);
  assert.equal(isNavItemActive("/results", "/submissions/123"), true);
});
check("only the current section is highlighted", () => {
  const p = "/submissions/123/comparison";
  assert.equal(isNavItemActive("/results", p), false);
  assert.equal(isNavItemActive("/metrics", p), false);
  assert.equal(isNavItemActive("/analysis", p), false);
});
check("Results does not stay lit while viewing another section", () => {
  assert.equal(isNavItemActive("/results", "/submissions/123/analysis"), false);
});
check("History and New Analysis highlight on their own paths only", () => {
  assert.equal(isNavItemActive("/history", "/history"), true);
  assert.equal(isNavItemActive("/history", "/submissions/123/results"), false);
  assert.equal(isNavItemActive("/dashboard", "/dashboard"), true);
});
check("an unlisted section highlights nothing", () => {
  assert.equal(isNavItemActive("/results", "/submissions/123/variants"), false);
  assert.equal(isNavItemActive("/analysis", "/submissions/123/variants"), false);
});
check("a historical submission highlights the same items as a current one", () => {
  const historical = "/submissions/abc-999/comparison";
  const current = "/submissions/zzz-111/comparison";
  const items = Object.keys(NAV_TO_SEGMENT).concat(["/dashboard", "/history"]);
  const lit = (p) => items.filter((i) => isNavItemActive(i, p));
  assert.deepEqual(lit(historical), lit(current));
  assert.deepEqual(lit(historical), ["/comparison"]);
});

console.log("\n-- latest completed submission resolution --");
const items = [
  { submission_id: "old", status: "completed", created_at: "2026-09-09T09:41:00Z" },
  { submission_id: "newest", status: "completed", created_at: "2026-09-18T11:10:00Z" },
  { submission_id: "mid", status: "completed", created_at: "2026-09-17T16:13:00Z" },
  { submission_id: "running", status: "processing", created_at: "2026-09-19T12:00:00Z" },
  { submission_id: "failed", status: "failed", created_at: "2026-09-19T13:00:00Z" },
];
check("the newest completed run wins", () => {
  assert.equal(latestCompletedSubmission(items).submission_id, "newest");
});
check("unfinished runs are never chosen", () => {
  assert.notEqual(latestCompletedSubmission(items).submission_id, "running");
  assert.notEqual(latestCompletedSubmission(items).submission_id, "failed");
});
check("input order does not change the result", () => {
  assert.equal(latestCompletedSubmission(items.slice().reverse()).submission_id, "newest");
});
check("only completed runs are openable in history, newest first", () => {
  assert.deepEqual(
    completedSubmissionsNewestFirst(items).map((s) => s.submission_id),
    ["newest", "mid", "old"]
  );
});
check("no completed run -> nothing to open", () => {
  assert.equal(latestCompletedSubmission([{ status: "processing" }]), null);
  assert.equal(latestCompletedSubmission([]), null);
  assert.deepEqual(completedSubmissionsNewestFirst([{ status: "failed" }]), []);
});
check("a missing payload does not throw", () => {
  assert.equal(latestCompletedSubmission(null), null);
  assert.deepEqual(completedSubmissionsNewestFirst(undefined), []);
});
check("an identical created_at still returns exactly one submission", () => {
  const tie = [
    { submission_id: "a", status: "completed", created_at: "2026-09-18T11:10:00Z" },
    { submission_id: "b", status: "completed", created_at: "2026-09-18T11:10:00Z" },
  ];
  const chosen = latestCompletedSubmission(tie);
  assert.ok(tie.map((t) => t.submission_id).includes(chosen.submission_id));
});

console.log("\n-- no silent switch back to the newest run --");
check("walking every section keeps one submission id", () => {
  const id = "abc-999";
  const walk = ["/results", "/comparison", "/metrics", "/analysis"].map((top) =>
    navTarget(top, id)
  );
  assert.deepEqual(walk, [
    `/submissions/${id}`,
    `/submissions/${id}/comparison`,
    `/submissions/${id}/metrics`,
    `/submissions/${id}/analysis`,
  ]);
  walk.forEach((p) => assert.equal(activeSubmissionFromPath(p).id, id));
});
check("a full History -> open -> compare round trip stays on that run", () => {
  const opened = submissionRoute("abc-999", ""); // History "View Analysis"
  assert.equal(activeSubmissionFromPath(opened).id, "abc-999");
  const compared = navTarget("/comparison", activeSubmissionFromPath(opened).id);
  assert.equal(compared, "/submissions/abc-999/comparison");
  const analysed = navTarget("/analysis", activeSubmissionFromPath(compared).id);
  assert.equal(analysed, "/submissions/abc-999/analysis");
});
check("the top-level path still resolves rather than 404ing", () => {
  // These stay routable and are resolved by ActiveSubmissionRoute.
  ["/results", "/comparison", "/metrics", "/analysis", "/history"].forEach((p) => {
    assert.equal(activeSubmissionFromPath(p).id, null);
  });
});

console.log(`\n${passed} checks passed\n`);