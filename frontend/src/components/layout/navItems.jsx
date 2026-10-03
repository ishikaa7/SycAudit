const NAV = [
  { to: "/dashboard", label: "New Analysis", icon: "sparkle" },
  { to: "/results", label: "Results", icon: "check" },
  { to: "/comparison", label: "Model Comparison", icon: "chart" },
  { to: "/benchmarks", label: "Benchmarks", icon: "flag" },
  { to: "/history", label: "History", icon: "clock" },
];

export function NavIcon({ name, className = "h-4 w-4" }) {
  const common = {
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 1.8,
    strokeLinecap: "round",
    strokeLinejoin: "round",
    className,
    "aria-hidden": true,
  };
  if (name === "sparkle") {
    return (
      <svg {...common}>
        <path d="M12 3.5 13.9 9l5.6 1.9-5.6 2L12 18.5 10.1 13l-5.6-2L10.1 9z" />
      </svg>
    );
  }
  if (name === "check") {
    return (
      <svg {...common}>
        <circle cx="12" cy="12" r="8.5" />
        <path d="m8.5 12.2 2.4 2.4 4.6-4.9" />
      </svg>
    );
  }
  if (name === "chart") {
    return (
      <svg {...common}>
        <path d="M4 19.5h16" />
        <rect x="6" y="11" width="3" height="6" rx="0.8" />
        <rect x="11.5" y="7" width="3" height="10" rx="0.8" />
        <rect x="17" y="13.5" width="3" height="3.5" rx="0.8" />
      </svg>
    );
  }
  if (name === "flag") {
    return (
      <svg {...common}>
        <path d="M6 21V4" />
        <path d="M6 4.8h11l-2.2 3.6L17 12H6z" />
      </svg>
    );
  }
  if (name === "clock") {
    return (
      <svg {...common}>
        <circle cx="12" cy="12" r="8.5" />
        <path d="M12 7.5V12l3 1.8" />
      </svg>
    );
  }
  return (
    <svg {...common}>
      <circle cx="12" cy="12" r="8.5" />
    </svg>
  );
}

export default NAV;