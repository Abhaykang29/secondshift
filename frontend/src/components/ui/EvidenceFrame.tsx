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
  /** Edge-to-edge inside a card: no rounding. */
  flush?: boolean;
  /** Cap the photo height; tall (vertical) frames are letterboxed on a dark
   * band instead of cropped, so the SAM overlay stays aligned. */
  maxHeight?: number;
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
  flush,
  maxHeight,
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
  // The frame renders at its natural aspect (not a cropped 16:9
  // cover): the SAM overlay uses normalized coordinates, and a cover
  // crop would misalign the box on vertical footage.
  const rounding = flush ? "" : topCornersOnly ? "rounded-t-card" : "rounded-card";
  const frame = (
    <div
      className={`relative overflow-hidden bg-surface-3 ${
        maxHeight ? "inline-block align-top" : `w-full ${rounding}`
      }`}
    >
      {src ? (
        <img
          src={src}
          alt={alt}
          loading="lazy"
          className={`block ${maxHeight ? "h-auto w-auto max-w-full" : "h-auto w-full"} ${dimmed ? "opacity-45 grayscale-[0.6]" : ""}`}
          style={maxHeight ? { maxHeight } : undefined}
        />
      ) : (
        <div className="aspect-video w-full" />
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
              style={{ fill: "rgba(8,102,255,0.14)", stroke: "var(--accent)", strokeWidth: 2.5 }}
              vectorEffect="non-scaling-stroke"
            />
          ) : (
            <rect
              x={bbox[0] * 100}
              y={bbox[1] * 100}
              width={(bbox[2] - bbox[0]) * 100}
              height={(bbox[3] - bbox[1]) * 100}
              style={{ fill: "rgba(8,102,255,0.14)", stroke: "var(--accent)", strokeWidth: 2.5 }}
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
          className="absolute z-10 max-w-[85%] truncate rounded-[6px] bg-accent px-2 py-0.5 text-[11.5px] font-semibold text-white shadow-raised"
          style={{
            ...(bbox![0] > 0.5
              ? { right: `max(8px, ${(1 - bbox![2]) * 100}%)` }
              : { left: `max(8px, ${bbox![0] * 100}%)` }),
            top: `max(8px, calc(${bbox![1] * 100}% - 26px))`,
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
            <EyeOff size={28} color="white" strokeWidth={1.75} />
          </span>
        </span>
      )}
      {typeof t === "number" && (
        <span
          className="absolute bottom-2.5 left-2.5 rounded-chip px-2.5 py-1 font-mono text-[12px] font-semibold tabular-nums text-white backdrop-blur-sm"
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
  if (!maxHeight) return frame;
  return (
    <div className={`flex w-full justify-center overflow-hidden bg-letterbox ${rounding}`}>
      {frame}
    </div>
  );
}
