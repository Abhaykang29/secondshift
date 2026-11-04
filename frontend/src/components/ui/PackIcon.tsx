import { packIdentity } from "./packs";

/** Pack icon tile (spec 3.7): 36x36, pack color at 12% alpha (20% in
 * dark mode), icon in the pack color. */
export function PackIcon({ packId, size = 40 }: { packId: string; size?: number }) {
  const pack = packIdentity(packId);
  const Icon = pack.icon;
  return (
    <span
      className="inline-flex shrink-0 items-center justify-center rounded-full"
      style={{
        width: size,
        height: size,
        backgroundColor: `color-mix(in srgb, ${pack.color} 14%, transparent)`,
      }}
      aria-hidden
    >
      <Icon size={Math.round(size * 0.5)} strokeWidth={2} style={{ color: pack.color }} />
    </span>
  );
}

/** Pack chip: neutral chip with a 6px pack-color dot + pack name. */
export function PackChip({ packId }: { packId: string }) {
  const pack = packIdentity(packId);
  return (
    <span className="inline-flex h-7 items-center gap-1.5 rounded-chip bg-surface-3 px-3 text-[12.5px] font-semibold text-text-2">
      <span
        className="h-1.5 w-1.5 rounded-full"
        style={{ backgroundColor: pack.color }}
        aria-hidden
      />
      {pack.name}
    </span>
  );
}
