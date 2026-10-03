/**
 * @type {import('tailwindcss').Config}
 */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        /* Primary: deep burgundy / wine. Primary actions, active nav, high scores. */
        burgundy: {
          50: "#faf3f5",
          100: "#f2e2e7",
          200: "#e4c3cc",
          300: "#d09aa8",
          400: "#b56c80",
          500: "#9c4a63",
          600: "#843553",
          700: "#6f1d3a",
          800: "#5c1830",
          900: "#4d1528",
          950: "#2c0a16",
        },
        /* Secondary: muted olive. Low sycophancy, success, healthy behaviour. */
        olive: {
          50: "#f7f9f1",
          100: "#edf1dd",
          200: "#dbe3bd",
          300: "#c3d096",
          400: "#8b9c52",
          500: "#667a3a",
          600: "#55662f",
          700: "#465425",
          800: "#3a451f",
          900: "#323b1d",
          950: "#1b2010",
        },
        /* Accent: muted butter yellow. Used sparingly - warnings and medium band only. */
        butter: {
          50: "#fdfaef",
          100: "#faf3d8",
          200: "#f5ebbd",
          300: "#efe09b",
          400: "#e8d98a",
          500: "#dcc46b",
          600: "#c9a74c",
          700: "#a9853a",
          800: "#8a6a33",
          900: "#72582e",
        },
        /* Warm off-white / cream surfaces. */
        cream: {
          50: "#fdfcfa",
          100: "#faf8f4",
          200: "#f3efe8",
          300: "#e8e2d7",
          400: "#d8d0c1",
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
        card: "0 1px 2px 0 rgb(45 33 30 / 0.04), 0 1px 3px 0 rgb(45 33 30 / 0.03)",
        "card-hover":
          "0 2px 4px -1px rgb(45 33 30 / 0.05), 0 8px 20px -6px rgb(45 33 30 / 0.09)",
        panel: "0 1px 3px 0 rgb(45 33 30 / 0.05), 0 12px 32px -12px rgb(45 33 30 / 0.10)",
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