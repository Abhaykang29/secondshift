import type { ReactNode } from "react";
import type { Hazard } from "../api/types";

/* Severity colours (Pass 3 spec 4.8): high red, medium amber, low
   yellow - the SAM overlay uses a 40% fill with a 2px outline. */
const SEVERITY_FILL: Record<number, string> = { 3: "#d33", 2: "#e90", 1: "#ec0" };
const SEVERITY_LABEL: Record<number, string> = { 3: "High", 2: "Medium", 1: "Low" };

/**
 * One hazard card: the evidence frame area with the SAM mask drawn as
 * an SVG overlay (polygon when the mask has one, otherwise the SAM
 * bounding box - normalized coords scale to any width), a
 * "Found by SAM (box)" badge, pack chips, and the plain-language why.
 * For absence hazards the anchor outline is drawn and labelled missing.
 * The evidence is the single selected SAM frame (backend guarantee);
 * a missing timestamp is shown as no timestamp, never as 0s.
 */
export default function HazardCard({
  hazard,
  packTitles,
  footer,
}: {
  hazard: Hazard;
  packTitles?: Record<string, string>;
  footer?: ReactNode;
}) {
  const mask = hazard.evidence.masks?.[0];
  const isAbsence = hazard.kind === "absence";
  const evidenceT = hazard.evidence.timestamps?.[0];
  const color = SEVERITY_FILL[hazard.severity] ?? "#888";
  const tags = hazard.pack_tags && hazard.pack_tags.length > 0
    ? hazard.pack_tags
    : [hazard.pack_id];
  return (
    <article
      className="mt-4 rounded border-2 bg-white p-4"
      style={{ borderColor: color }}
      aria-label={hazard.title}
    >
      <div className="flex items-start justify-between gap-2">
        <h3 className="text-xl font-medium">
          {hazard.rank ? `#${hazard.rank} ` : ""}
          {hazard.title}
        </h3>
        {hazard.verification === "confirmed" && mask && (
          <span className="shrink-0 rounded bg-green-100 px-2 py-1 text-sm">Found by SAM (box)</span>
        )}
        {hazard.verification === "confirmed" && !mask && (
          <span className="shrink-0 rounded bg-green-100 px-2 py-1 text-sm">Confirmed</span>
        )}
        {hazard.verification === "needs_human" && (
          <span className="shrink-0 rounded bg-amber-100 px-2 py-1 text-sm">Needs a human look</span>
        )}
      </div>
      <p className="text-sm uppercase tracking-wide opacity-70">
        {hazard.room} - {SEVERITY_LABEL[hazard.severity] ?? ""} severity
        {hazard.on_routine_path ? " - on the walking path" : ""}
      </p>
      <div className="mt-2 flex flex-wrap gap-1">
        {tags.map((tag) => (
          <span key={tag} className="rounded-full bg-[#e9f2ec] px-2 py-0.5 text-xs font-medium text-[#1f3d2b]">
            {packTitles?.[tag] ?? tag}
          </span>
        ))}
      </div>
      <div className="relative mt-3 aspect-video w-full overflow-hidden rounded bg-neutral-700">
        <span className="absolute left-2 top-2 text-sm text-white">
          {evidenceT !== undefined ? `Evidence frame at ${evidenceT}s` : "Evidence frame"}
        </span>
        {mask && (
          <svg
            className="absolute inset-0 h-full w-full"
            viewBox="0 0 100 100"
            preserveAspectRatio="none"
            aria-hidden
          >
            {mask.polygon ? (
              <polygon
                points={mask.polygon.map(([x, y]) => `${x * 100},${y * 100}`).join(" ")}
                fill={isAbsence ? "transparent" : color}
                fillOpacity={isAbsence ? 0 : 0.4}
                stroke={isAbsence ? "#4ea1ff" : color}
                strokeWidth={2}
                strokeDasharray={isAbsence ? "4 2" : undefined}
                vectorEffect="non-scaling-stroke"
              />
            ) : (
              <rect
                x={mask.bbox[0] * 100}
                y={mask.bbox[1] * 100}
                width={(mask.bbox[2] - mask.bbox[0]) * 100}
                height={(mask.bbox[3] - mask.bbox[1]) * 100}
                fill={isAbsence ? "transparent" : color}
                fillOpacity={isAbsence ? 0 : 0.4}
                stroke={isAbsence ? "#4ea1ff" : color}
                strokeWidth={2}
                strokeDasharray={isAbsence ? "4 2" : undefined}
                vectorEffect="non-scaling-stroke"
              />
            )}
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
      {footer}
    </article>
  );
}
