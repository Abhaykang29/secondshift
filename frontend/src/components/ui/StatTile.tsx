import Card from "./Card";

/** Stat tile (spec 3.8): big mono number, label, optional footnote. */
export default function StatTile({
  value,
  label,
  footnote,
  muted,
}: {
  value: string;
  label: string;
  footnote?: string;
  muted?: boolean;
}) {
  return (
    <Card>
      <div
        className={`font-mono text-[28px] font-semibold leading-[32px] tabular-nums ${
          muted ? "text-text-3" : "text-text"
        }`}
      >
        {value}
      </div>
      <div className="mt-1 text-[13px] text-text-3">{label}</div>
      {footnote && <div className="mt-0.5 text-[12px] text-text-3">{footnote}</div>}
    </Card>
  );
}
