export function formatDateTime(value) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

export function timeAgo(value) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  const seconds = Math.round((date.getTime() - Date.now()) / 1000);
  const abs = Math.abs(seconds);
  const units = [
    ["year", 31536000],
    ["month", 2592000],
    ["week", 604800],
    ["day", 86400],
    ["hour", 3600],
    ["minute", 60],
  ];
  for (const [unit, size] of units) {
    if (abs >= size) {
      const count = Math.round(abs / size);
      const key = count === 1 ? unit : `${unit}s`;
      return seconds < 0 ? `${count} ${key} ago` : `in ${count} ${key}`;
    }
  }
  return seconds < 0 ? "just now" : "in a moment";
}

export function truncate(text, length = 160) {
  if (!text) return "";
  const t = String(text);
  if (t.length <= length) return t;
  return `${t.slice(0, length).trimEnd()}…`;
}

export function formatScore(value, digits = 1) {
  return typeof value === "number" ? value.toFixed(digits) : "—";
}

export function formatPercent(value) {
  if (typeof value !== "number") return "—";
  return `${Math.round(value * 100)}%`;
}

export function initials(name) {
  if (!name) return "?";
  return String(name)
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0].toUpperCase())
    .join("");
}

export function normalizeList(data) {
  if (Array.isArray(data)) return data;
  if (data && Array.isArray(data.items)) return data.items;
  if (data && Array.isArray(data.results)) return data.results;
  return [];
}

export function getModelInfo(response) {
  const model = response?.model;
  if (model && model.model_name) {
    return { name: model.model_name, provider: model.provider };
  }
  return {
    name: response?.model_name ?? model?.name ?? "Unknown model",
    provider: response?.provider ?? model?.provider ?? "unknown",
  };
}