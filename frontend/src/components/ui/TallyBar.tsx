import { plural } from "../../plural";

export interface TallyCounts {
  bad: number;
  warn: number;
  unk: number;
  ok: number;
}

interface TallyBarProps {
  counts: TallyCounts;
  /** Segment captions as [singular, plural] pairs, bad/warn/unk/ok order. */
  labels: [[string, string], [string, string], [string, string], [string, string]];
  compact?: boolean;
}

const SEGMENTS = [
  { key: "bad", cls: "bg-bad" },
  { key: "warn", cls: "bg-warn" },
  { key: "unk", cls: "bg-unk" },
  { key: "ok", cls: "bg-ok" },
] as const;

/**
 * Stacked tally bar (spec 3.5): 8px high (6px compact), segments in
 * bad -> warn -> unk -> ok order with 2px gaps, and a mono caption
 * line with zero counts omitted.
 */
export default function TallyBar({ counts, labels, compact }: TallyBarProps) {
  const values = [counts.bad, counts.warn, counts.unk, counts.ok];
  const parts = values
    .map((n, i) => (n > 0 ? plural(n, labels[i][0], labels[i][1]) : null))
    .filter((p): p is string => p !== null);
  return (
    <div>
      <div
        className={`flex w-full gap-[2px] overflow-hidden rounded-chip bg-surface-2 ${
          compact ? "h-1.5" : "h-2"
        }`}
        role="img"
        aria-label={parts.join(", ") || "No items"}
      >
        {SEGMENTS.map((seg, i) =>
          values[i] > 0 ? (
            <div key={seg.key} className={`${seg.cls} h-full`} style={{ flexGrow: values[i] }} />
          ) : null,
        )}
      </div>
      {!compact && parts.length > 0 && (
        <p className="mt-2 font-mono text-[12.5px] tabular-nums text-text-2">{parts.join(" · ")}</p>
      )}
    </div>
  );
}
