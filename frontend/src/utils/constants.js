export const FACETS = [
  { key: "agreement", label: "Agreement" },
  { key: "flattery", label: "Flattery" },
  { key: "avoiding_disagreement", label: "Avoiding Disagreement" },
  { key: "preference_alignment", label: "Preference Alignment" },
  { key: "validation_seeking", label: "Validation Seeking" },
];

export const VARIANT_ORDER = [
  { key: "original", label: "Original" },
  { key: "question", label: "Question" },
  { key: "third_person", label: "Third-Person" },
  { key: "hedged", label: "Hedged" },
];

export const STATUS_META = {
  pending: {
    label: "Pending",
    badge: "bg-slate-100 text-slate-600 ring-slate-200",
    dot: "bg-slate-400",
    pulse: false,
  },
  processing: {
    label: "Processing",
    badge: "bg-amber-100 text-amber-700 ring-amber-200",
    dot: "bg-amber-500",
    pulse: true,
  },
  completed: {
    label: "Completed",
    badge: "bg-emerald-100 text-emerald-700 ring-emerald-200",
    dot: "bg-emerald-500",
    pulse: false,
  },
  failed: {
    label: "Failed",
    badge: "bg-red-100 text-red-700 ring-red-200",
    dot: "bg-red-500",
    pulse: false,
  },
};

export const STABILITY_META = {
  low: {
    label: "Stable",
    detail: "Low wobble — coherent across framings, trustworthy",
    chip: "bg-emerald-50 text-emerald-700 ring-emerald-200",
  },
  moderate: {
    label: "Moderately stable",
    detail: "Moderate wobble — answers drift across framings",
    chip: "bg-amber-50 text-amber-700 ring-amber-200",
  },
  high: {
    label: "Unstable",
    detail: "High wobble — answers shift heavily by framing",
    chip: "bg-red-50 text-red-700 ring-red-200",
  },
};

export const SCORE_HEX = { low: "#059669", mid: "#d97706", high: "#dc2626" };
export const SCORE_TEXT = {
  low: "text-emerald-700",
  mid: "text-amber-700",
  high: "text-red-600",
};
export const SCORE_BG = {
  low: "bg-emerald-50",
  mid: "bg-amber-50",
  high: "bg-red-50",
};
export const SCORE_RING = {
  low: "ring-emerald-200",
  mid: "ring-amber-200",
  high: "ring-red-200",
};

export function severityLevel(value, max = 5) {
  const ratio = max > 0 ? value / max : 0;
  if (ratio < 0.4) return "low";
  if (ratio < 0.7) return "mid";
  return "high";
}

export function scoreHex(value, max = 5) {
  return SCORE_HEX[severityLevel(value, max)];
}

export function scoreText(value, max = 5) {
  return SCORE_TEXT[severityLevel(value, max)];
}

export function scoreBg(value, max = 5) {
  return SCORE_BG[severityLevel(value, max)];
}

export function scoreRing(value, max = 5) {
  return SCORE_RING[severityLevel(value, max)];
}