import { useState } from "react";

export default function Toggle({ checked, onChange, disabled = false, label }) {
  const [pending, setPending] = useState(false);

  const handleToggle = async () => {
    if (disabled || pending) return;
    setPending(true);
    try {
      await onChange(!checked);
    } finally {
      setPending(false);
    }
  };

  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={label}
      onClick={handleToggle}
      disabled={disabled || pending}
      className={`relative inline-flex h-6 w-11 shrink-0 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-brand-400 focus:ring-offset-1 disabled:cursor-not-allowed disabled:opacity-50 ${
        checked ? "bg-brand-600" : "bg-slate-300"
      }`}
    >
      <span
        className={`inline-block h-4 w-4 transform rounded-full bg-white shadow transition-transform ${
          checked ? "translate-x-6" : "translate-x-1"
        } ${pending ? "opacity-70" : ""}`}
      />
    </button>
  );
}