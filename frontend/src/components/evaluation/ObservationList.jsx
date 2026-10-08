/**
 * "Key observations" for one response.
 *
 * Every entry restates a number the backend actually stored for one facet. The
 * API exposes no reasoning, rationale or evidence text, so nothing here claims
 * anything about the content of the response — the caller supplies the text and
 * the tone, both derived from that facet's stored value.
 *
 * Tone is semantic and mirrors the palette used everywhere else:
 *   good - the facet recorded nothing (value 0), emerald
 *   warn - something small was recorded, amber
 *   bad  - the facet is above the midpoint of the 0-2 scale, red
 * A facet at 0 can therefore never be drawn as a problem, and a high facet can
 * never be given reassuring wording.
 */
const TONES = {
  good: { mark: "✓", chip: "bg-emerald-50 text-emerald-800 ring-emerald-200" },
  warn: { mark: "!", chip: "bg-amber-50 text-amber-800 ring-amber-200" },
  bad: { mark: "✕", chip: "bg-red-50 text-red-700 ring-red-200" },
};

export default function ObservationList({ observations }) {
  if (!Array.isArray(observations) || observations.length === 0) {
    return (
      <div className="rounded-xl border border-dashed border-slate-200 px-4 py-5 text-center">
        <p className="text-[12.5px] font-semibold text-slate-500">No observations available</p>
        <p className="mx-auto mt-1 max-w-sm text-[11.5px] leading-relaxed text-slate-400">
          Observations restate stored facet values, and this response has none stored. The API
          returns no reasoning text, so nothing is asserted about the response itself.
        </p>
      </div>
    );
  }

  return (
    <ul className="grid gap-2">
      {observations.map((o) => {
        const tone = TONES[o.tone] ?? TONES.good;
        return (
          <li key={o.id} className="flex gap-2.5">
            <span
              className={`mt-px grid h-4 w-4 shrink-0 place-items-center rounded-full text-[9px] font-bold ring-1 ring-inset ${tone.chip}`}
              aria-hidden="true"
            >
              {tone.mark}
            </span>
            <p className="min-w-0 text-[12.5px] leading-relaxed text-slate-600">
              <span className="font-semibold text-slate-700">{o.label}</span>
              <span className="text-slate-400"> — </span>
              {o.text}
            </p>
          </li>
        );
      })}
    </ul>
  );
}