import { packIdentity } from "./packs";

/** Pack icon tile (spec 3.7): 36x36, pack color at 12% alpha (20% in
 * dark mode), icon in the pack color. */
export function PackIcon({ packId, size = 36 }: { packId: string; size?: number }) {
  const pack = packIdentity(packId);
  const Icon = pack.icon;
  return (
    <span
      className="inline-flex shrink-0 items-center justify-center rounded-tile"
      style={{
        width: size,
        height: size,
        backgroundColor: `color-mix(in srgb, ${pack.color} 14%, transparent)`,
      }}
      aria-hidden
    >
      <Icon size={20} strokeWidth={1.75} style={{ color: pack.color }} />
    </span>
  );
}

/** Pack chip: neutral chip with a 6px pack-color dot + pack name. */
export function PackChip({ packId }: { packId: string }) {
  const pack = packIdentity(packId);
  return (
    <span className="inline-flex h-6 items-center gap-1.5 rounded-chip bg-surface-2 px-2.5 text-[12px] font-semibold text-text-2">
      <span
        className="h-1.5 w-1.5 rounded-full"
        style={{ backgroundColor: pack.color }}
        aria-hidden
      />
      {pack.name}
    </span>
  );
}
