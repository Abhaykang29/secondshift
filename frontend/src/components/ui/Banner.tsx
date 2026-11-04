import type { ReactNode } from "react";
import { AlertTriangle, Database, FlaskConical, Info, type LucideIcon } from "lucide-react";

export type BannerKind = "recorded" | "mock" | "privacy" | "info" | "warn";

const KINDS: Record<BannerKind, { icon: LucideIcon; cls: string }> = {
  recorded: { icon: Database, cls: "bg-accent-bg text-accent" },
  mock: { icon: FlaskConical, cls: "bg-warn-bg text-warn" },
  privacy: { icon: Info, cls: "bg-surface-2 text-text-2" },
  info: { icon: Info, cls: "bg-surface-2 text-text-2" },
  warn: { icon: AlertTriangle, cls: "bg-warn-bg text-warn" },
};

/** Full-width banner strip (spec 3.10): 13/500, icon left. */
export default function Banner({ kind, children }: { kind: BannerKind; children: ReactNode }) {
  const { icon: Icon, cls } = KINDS[kind];
  return (
    <div
      role={kind === "mock" ? "alert" : undefined}
      className={`flex min-h-[40px] w-full items-center gap-2 rounded-card px-3 py-2 text-[13px] font-medium ${cls}`}
    >
      <Icon size={18} strokeWidth={1.75} className="shrink-0" aria-hidden />
      <span>{children}</span>
    </div>
  );
}
