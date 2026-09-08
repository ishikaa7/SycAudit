import { STATUS_META } from "../../utils/constants.js";

export default function StatusBadge({ status, className = "" }) {
  const meta = STATUS_META[status] ?? STATUS_META.pending;
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium ring-1 ring-inset ${meta.badge} ${className}`}
    >
      <span
        className={`h-1.5 w-1.5 rounded-full ${meta.dot} ${meta.pulse ? "animate-pulse" : ""}`}
      />
      {meta.label}
    </span>
  );
}