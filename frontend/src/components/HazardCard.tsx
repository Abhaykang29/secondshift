import type { Hazard } from "../api/types";

const SEVERITY_FILL: Record<number, string> = { 3: "#d33", 2: "#e90", 1: "#ec0" };

/**
 * One hazard card: the evidence frame area with the SAM mask drawn as an
 * SVG polygon overlay (normalized coords scale to any width), a
 * "Confirmed by SAM" badge, and the plain-language why.
 * For absence hazards the anchor outline is drawn and labelled missing.
 */
export default function HazardCard({ hazard }: { hazard: Hazard }) {
  const mask = hazard.evidence.masks?.[0];
  const isAbsence = hazard.kind === "absence";
  return (
    <article className="mt-4 rounded border p-4" aria-label={hazard.title}>
      <div className="flex items-start justify-between gap-2">
        <h3 className="text-xl font-medium">
          {hazard.rank ? `#${hazard.rank} ` : ""}
          {hazard.title}
        </h3>
        {hazard.verification === "confirmed" && (
          <span className="rounded bg-green-100 px-2 py-1 text-sm">Confirmed by SAM</span>
        )}
        {hazard.verification === "needs_human" && (
          <span className="rounded bg-amber-100 px-2 py-1 text-sm">Needs a human look</span>
        )}
      </div>
      <p className="text-sm uppercase tracking-wide opacity-70">
        {hazard.room} - severity {hazard.severity}
        {hazard.on_routine_path ? " - on the walking path" : ""}
      </p>
      <div className="relative mt-3 aspect-video w-full overflow-hidden rounded bg-neutral-700">
        <span className="absolute left-2 top-2 text-sm text-white">
          Evidence frame at {hazard.evidence.timestamps[0] ?? 0}s
        </span>
        {mask?.polygon && (
          <svg
            className="absolute inset-0 h-full w-full"
            viewBox="0 0 100 100"
            preserveAspectRatio="none"
            aria-hidden
          >
            <polygon
              points={mask.polygon.map(([x, y]) => `${x * 100},${y * 100}`).join(" ")}
              fill={isAbsence ? "transparent" : SEVERITY_FILL[hazard.severity]}
              fillOpacity={isAbsence ? 0 : 0.4}
              stroke={isAbsence ? "#4ea1ff" : SEVERITY_FILL[hazard.severity]}
              strokeWidth={1.5}
              strokeDasharray={isAbsence ? "4 2" : undefined}
            />
          </svg>
        )}
        {isAbsence && (
          <span className="absolute bottom-2 right-2 rounded bg-blue-600 px-2 py-1 text-sm text-white">
            Missing here: {hazard.title}
          </span>
        )}
      </div>
      <p className="mt-3">{hazard.description}</p>
      <p className="mt-1">
        <em>Why it matters:</em> {hazard.why_it_matters}
      </p>
      <p className="mt-1 text-sm opacity-80">{hazard.verification_reason}</p>
    </article>
  );
}
