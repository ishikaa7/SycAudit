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
    badge: "bg-stone-100 text-stone-600 ring-stone-200",
    dot: "bg-stone-400",
    pulse: false,
  },
  processing: {
    label: "Processing",
    badge: "bg-butter-50 text-butter-900 ring-butter-200",
    dot: "bg-butter-500",
    pulse: true,
  },
  /* Submission.status value. */
  completed: {
    label: "Completed",
    badge: "bg-olive-50 text-olive-800 ring-olive-200",
    dot: "bg-olive-500",
    pulse: false,
  },
  /* Response.status value for a successful model call. */
  success: {
    label: "Completed",
    badge: "bg-olive-50 text-olive-800 ring-olive-200",
    dot: "bg-olive-500",
    pulse: false,
  },
  failed: {
    label: "Failed",
    badge: "bg-burgundy-50 text-burgundy-800 ring-burgundy-200",
    dot: "bg-burgundy-500",
    pulse: false,
  },
  timeout: {
    label: "Timed out",
    badge: "bg-burgundy-50 text-burgundy-800 ring-burgundy-200",
    dot: "bg-burgundy-500",
    pulse: false,
  },
};

export const STABILITY_META = {
  low: {
    label: "Stable",
    detail: "Low wobble — coherent across framings, more trustworthy.",
    chip: "bg-olive-50 text-olive-800 ring-olive-200",
  },
  moderate: {
    label: "Moderately stable",
    detail: "Moderate wobble — answers drift across framings.",
    chip: "bg-butter-50 text-butter-900 ring-butter-200",
  },
  high: {
    label: "Unstable",
    detail: "High wobble — answers shift heavily by framing.",
    chip: "bg-burgundy-50 text-burgundy-800 ring-burgundy-200",
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