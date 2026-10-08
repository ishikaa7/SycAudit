/**
 * Status / stability presentation metadata.
 *
 * FACET and VARIANT definitions and all severity-threshold logic now live in
 * utils/scoring.js so there is a single source of truth. The re-exports at the
 * bottom are kept so existing imports keep working.
 */
import { FACET_DEFS, VARIANT_DEFS } from "./scoring.js";

export const STATUS_META = {
  pending: {
    label: "Pending",
    badge: "bg-slate-100 text-slate-600 ring-slate-200",
    dot: "bg-slate-400",
    pulse: false,
  },
  processing: {
    label: "Processing",
    badge: "bg-amber-50 text-amber-900 ring-amber-200",
    dot: "bg-amber-500",
    pulse: true,
  },
  /* Submission.status value. */
  completed: {
    label: "Completed",
    badge: "bg-emerald-50 text-emerald-800 ring-emerald-200",
    dot: "bg-emerald-500",
    pulse: false,
  },
  /* Response.status value for a successful model call. */
  success: {
    label: "Completed",
    badge: "bg-emerald-50 text-emerald-800 ring-emerald-200",
    dot: "bg-emerald-500",
    pulse: false,
  },
  failed: {
    label: "Failed",
    badge: "bg-red-50 text-red-700 ring-red-200",
    dot: "bg-red-500",
    pulse: false,
  },
  timeout: {
    label: "Timed out",
    badge: "bg-red-50 text-red-700 ring-red-200",
    dot: "bg-red-500",
    pulse: false,
  },
};

export const STABILITY_META = {
  low: {
    label: "Stable",
    detail: "Low wobble — coherent across framings, more trustworthy.",
    chip: "bg-emerald-50 text-emerald-800 ring-emerald-200",
  },
  moderate: {
    label: "Moderately stable",
    detail: "Moderate wobble — answers drift across framings.",
    chip: "bg-amber-50 text-amber-900 ring-amber-200",
  },
  high: {
    label: "Unstable",
    detail: "High wobble — answers shift heavily by framing.",
    chip: "bg-red-50 text-red-700 ring-red-200",
  },
};

/** @deprecated import from utils/scoring.js instead */
export const FACETS = FACET_DEFS.map((f) => ({ key: f.key, label: f.label, id: f.id }));

/** @deprecated import VARIANT_DEFS from utils/scoring.js instead */
export const VARIANT_ORDER = VARIANT_DEFS.map((v) => ({
  key: v.key,
  label: v.sublabel,
  letter: v.letter,
}));

export {
  severityLevel,
  scoreHex,
  scoreTextClass as scoreText,
  BACKEND_SCORE_MAX,
  DISPLAY_SCORE_MAX,
  toDisplayScore,
} from "./scoring.js";