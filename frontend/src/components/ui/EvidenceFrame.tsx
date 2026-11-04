import { EyeOff } from "lucide-react";

export interface FrameMask {
  bbox?: number[] | null;
  polygon?: number[][] | null;
  prompt?: string;
}

interface EvidenceFrameProps {
  src?: string | null;
  alt: string;
  mask?: FrameMask | null;
  /** Set for absence findings: the SAM anchor that should be there. */
  absenceAnchor?: string | null;
  t?: number | null;
  blurry?: boolean;
  /** Can't-tell treatment: dimmed, grayscale, centered EyeOff. */
  dimmed?: boolean;
  topCornersOnly?: boolean;
}

/**
 * Evidence frame (spec 3.6): 16:9, cover, SAM box in accent with a
 * `SAM · {prompt}` tag, mono timestamp chip bottom-left, "blurry
 * frame" chip bottom-right. Absence items get a dashed outline and a
 * `SAM · {anchor} · missing` tag.
 */
export default function EvidenceFrame({
  src,
  alt,
  mask,
  absenceAnchor,
  t,
  blurry,
  dimmed,
  topCornersOnly,
}: EvidenceFrameProps) {
  const bbox = mask?.bbox ?? null;
  const polygon = mask?.polygon ?? null;
  const points =
    polygon && polygon.length > 1
      ? polygon.map((p) => `${p[0] * 100},${p[1] * 100}`).join(" ")
      : null;
  const boxStyle = bbox
    ? {
        left: `${bbox[0] * 100}%`,
        top: `${bbox[1] * 100}%`,
        width: `${(bbox[2] - bbox[0]) * 100}%`,
        height: `${(bbox[3] - bbox[1]) * 100}%`,
      }
    : null;
  return (
    <div
      className={`relative aspect-video w-full overflow-hidden bg-surface-3 ${
        topCornersOnly ? "rounded-t-card" : "rounded-card"
      }`}
    >
      {src && (
        <img
          src={src}
          alt={alt}
          loading="lazy"
          className={`absolute inset-0 h-full w-full object-cover ${
            dimmed ? "opacity-45 grayscale-[0.6]" : ""
          }`}
        />
      )}
      {!dimmed && bbox && !absenceAnchor && (
        <svg
          className="pointer-events-none absolute inset-0 h-full w-full"
          viewBox="0 0 100 100"
          preserveAspectRatio="none"
          aria-hidden
        >
          {points ? (
            <polygon
              points={points}
              style={{ fill: "rgba(47,91,255,0.12)", stroke: "var(--accent)", strokeWidth: 2 }}
              vectorEffect="non-scaling-stroke"
            />
          ) : (
            <rect
              x={bbox[0] * 100}
              y={bbox[1] * 100}
              width={(bbox[2] - bbox[0]) * 100}
              height={(bbox[3] - bbox[1]) * 100}
              style={{ fill: "rgba(47,91,255,0.12)", stroke: "var(--accent)", strokeWidth: 2 }}
              vectorEffect="non-scaling-stroke"
            />
          )}
        </svg>
      )}
      {!dimmed && absenceAnchor && boxStyle && (
        <div
          className="pointer-events-none absolute rounded-[4px] border-2 border-dashed border-accent"
          style={boxStyle}
          aria-hidden
        />
      )}
      {!dimmed && (mask?.prompt || absenceAnchor) && boxStyle && (
        <span
          className="absolute z-10 max-w-[85%] truncate rounded-[4px] bg-accent px-1.5 py-0.5 text-[11px] font-semibold text-white"
          style={{
            left: `min(${bbox![0] * 100}%, calc(100% - 90px))`,
            top: `max(0%, calc(${bbox![1] * 100}% - 22px))`,
          }}
        >
          {absenceAnchor ? `SAM · ${absenceAnchor} · missing` : `SAM · ${mask?.prompt}`}
        </span>
      )}
      {dimmed && (
        <span className="absolute inset-0 flex items-center justify-center" aria-hidden>
          <span
            className="flex h-12 w-12 items-center justify-center rounded-full"
            style={{ backgroundColor: "var(--overlay)" }}
          >
            <EyeOff size={28} color="#fff" strokeWidth={1.75} />
          </span>
        </span>
      )}
      {typeof t === "number" && (
        <span
          className="absolute bottom-2 left-2 rounded-chip px-2 py-0.5 font-mono text-[12px] tabular-nums text-white"
          style={{ backgroundColor: "var(--overlay)" }}
        >
          t={t}s
        </span>
      )}
      {blurry && (
        <span
          className="absolute bottom-2 right-2 rounded-chip px-2 py-0.5 font-mono text-[12px] text-white"
          style={{ backgroundColor: "var(--overlay)" }}
        >
          blurry frame
        </span>
      )}
    </div>
  );
}
