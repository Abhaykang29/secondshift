import {
  AlertTriangle,
  BellRing,
  CheckCircle2,
  Eye,
  EyeOff,
  HelpCircle,
  PlusCircle,
  type LucideIcon,
} from "lucide-react";

/**
 * The verdict chip (spec 3.3): one component for every verdict and
 * status. Color is never the only signal - icon + exact label always.
 * Kinds map from the existing Verification / re-check / live enums.
 */
export type VerdictKind =
  | "confirmed" // Problem found
  | "needs_human" // Needs a human look
  | "rejected" // No problem
  | "cannot" // Can't tell
  | "fixed" // Re-check: fixed
  | "still" // Re-check: still there
  | "new" // Re-check: new
  | "not_filmed" // Re-check: not filmed
  | "live_ok" // Live: OK
  | "live_alert" // Live: Alert
  | "live_cant"; // Live: Can't see

const VERDICTS: Record<VerdictKind, { label: string; icon: LucideIcon; cls: string }> = {
  confirmed: { label: "Problem found", icon: AlertTriangle, cls: "bg-bad-bg text-bad" },
  needs_human: { label: "Needs a human look", icon: Eye, cls: "bg-warn-bg text-warn" },
  rejected: { label: "No problem", icon: CheckCircle2, cls: "bg-ok-bg text-ok" },
  cannot: {
    label: "Can't tell",
    icon: HelpCircle,
    cls: "bg-unk-bg text-unk border border-dashed border-border-strong",
  },
  fixed: { label: "Fixed", icon: CheckCircle2, cls: "bg-ok-bg text-ok" },
  still: { label: "Still there", icon: AlertTriangle, cls: "bg-bad-bg text-bad" },
  new: { label: "New", icon: PlusCircle, cls: "bg-bad-bg text-bad" },
  not_filmed: {
    label: "Not filmed",
    icon: HelpCircle,
    cls: "bg-unk-bg text-unk border border-dashed border-border-strong",
  },
  live_ok: { label: "OK", icon: CheckCircle2, cls: "bg-ok-bg text-ok" },
  live_alert: { label: "Alert", icon: BellRing, cls: "bg-bad-bg text-bad" },
  live_cant: {
    label: "Can't see",
    icon: EyeOff,
    cls: "bg-unk-bg text-unk border border-dashed border-border-strong",
  },
};

export default function VerdictChip({ kind }: { kind: VerdictKind }) {
  const v = VERDICTS[kind];
  const Icon = v.icon;
  return (
    <span
      className={`inline-flex h-6 items-center gap-1.5 rounded-chip px-2.5 text-[12px] font-semibold ${v.cls}`}
    >
      <Icon size={14} strokeWidth={1.75} aria-hidden />
      {v.label}
    </span>
  );
}
