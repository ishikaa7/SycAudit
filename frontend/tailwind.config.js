/**
 * @type {import('tailwindcss').Config}
 */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        /*
         * Design tokens for the AI-evaluation palette.
         * Indigo is the brand/primary colour, violet the single accent, emerald /
         * amber / red are reserved for evaluation status, and slate / surface
         * carry all neutrals. Status colours are semantic only — never decoration.
         */
        /* Primary: deep indigo. Primary actions, active nav, focus rings. */
        indigo: {
          50: "#eef2ff",
          100: "#e0e7ff",
          200: "#c7d2fe",
          300: "#a5b4fc",
          400: "#818cf8",
          500: "#6366f1",
          600: "#4f46e5",
          700: "#4338ca",
          800: "#3730a3",
          900: "#312e81",
          950: "#1e1b4b",
        },
        /* Secondary accent: soft violet. Used sparingly. */
        violet: {
          50: "#f5f3ff",
          100: "#ede9fe",
          200: "#ddd6fe",
          300: "#c4b5fd",
          400: "#a78bfa",
          500: "#8b5cf6",
          600: "#7c3aed",
          700: "#6d28d9",
          800: "#5b21b6",
          900: "#4c1d95",
        },
        /* Success / low sycophancy. */
        emerald: {
          50: "#ecfdf5",
          100: "#d1fae5",
          200: "#a7f3d0",
          300: "#6ee7b7",
          400: "#34d399",
          500: "#10b981",
          600: "#059669",
          700: "#047857",
          800: "#065f46",
          900: "#064e3b",
          950: "#022c22",
        },
        /* Warning / medium band. */
        amber: {
          50: "#fffbeb",
          100: "#fef3c7",
          200: "#fde68a",
          300: "#fcd34d",
          400: "#fbbf24",
          500: "#f59e0b",
          600: "#d97706",
          700: "#b45309",
          800: "#92400e",
          900: "#78350f",
          950: "#451a03",
        },
        /* Danger / high band, failures and timeouts. */
        red: {
          50: "#fef2f2",
          100: "#fee2e2",
          200: "#fecaca",
          300: "#fca5a5",
          400: "#f87171",
          500: "#ef4444",
          600: "#dc2626",
          700: "#b91c1c",
          800: "#991b1b",
          900: "#7f1d1d",
          950: "#450a0a",
        },
        /*
         * Neutrals: cool slate ramp.
         * 900 primary text, 700 secondary-strong, 500 secondary, 400 muted,
         * 300 secondary-button border, 200 border, 50 page background.
         */
        slate: {
          50: "#f8fafc",
          100: "#f1f5f9",
          200: "#e2e8f0",
          300: "#cbd5e1",
          400: "#94a3b8",
          500: "#64748b",
          600: "#475569",
          700: "#334155",
          800: "#1f2937",
          900: "#111827",
          950: "#0b1220",
        },
        /*
         * Surface family, mapped to the product palette:
         *   50  page background      #F8FAFC
         *   100 card / surface       #FFFFFF
         *   200 border               #E2E8F0
         *   300 border (segment fill)#E2E8F0
         *   500 secondary text       #64748B
         *   900 primary text         #111827
         * Valid utilities: bg-surface-50/100, border-surface-200,
         * text-surface-500/900, ring-offset-surface-50.
         */
        surface: {
          50: "#f8fafc",
          100: "#ffffff",
          200: "#e2e8f0",
          300: "#e2e8f0",
          500: "#64748b",
          900: "#111827",
        },
      },
      fontFamily: {
        sans: [
          "Inter",
          "ui-sans-serif",
          "system-ui",
          "-apple-system",
          "Segoe UI",
          "Roboto",
          "Helvetica Neue",
          "Arial",
          "sans-serif",
        ],
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "Consolas", "monospace"],
      },
      borderRadius: {
        card: "14px",
      },
      boxShadow: {
        /* Very subtle, cool-tinted elevation. */
        card: "0 1px 2px 0 rgb(15 23 42 / 0.04), 0 1px 3px 0 rgb(15 23 42 / 0.03)",
        "card-hover":
          "0 2px 4px -1px rgb(15 23 42 / 0.05), 0 8px 20px -6px rgb(15 23 42 / 0.08)",
        panel: "0 1px 3px 0 rgb(15 23 42 / 0.04), 0 12px 32px -12px rgb(15 23 42 / 0.10)",
      },
      keyframes: {
        "fade-up": {
          from: { opacity: "0", transform: "translateY(6px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
        "grow-in": {
          from: { transform: "scaleX(0)" },
          to: { transform: "scaleX(1)" },
        },
        "reveal": {
          from: { opacity: "0" },
          to: { opacity: "1" },
        },
        "slide-down": {
          from: { opacity: "0", transform: "translateY(-4px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
      },
      animation: {
        "fade-up": "fade-up 320ms cubic-bezier(0.22, 1, 0.36, 1) both",
        "grow-in": "grow-in 620ms cubic-bezier(0.22, 1, 0.36, 1) both",
        reveal: "reveal 260ms ease-out both",
        "slide-down": "slide-down 180ms cubic-bezier(0.22, 1, 0.36, 1) both",
      },
    },
  },
  plugins: [],
};