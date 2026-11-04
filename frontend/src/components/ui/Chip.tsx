import type { ReactNode } from "react";
import type { LucideIcon } from "lucide-react";

interface ChipProps {
  variant?: "neutral" | "accent";
  icon?: LucideIcon;
  className?: string;
  children: ReactNode;
}

/** Pill chip (spec 3.2): 24px high, 12/600, optional 14px icon. */
export default function Chip({ variant = "neutral", icon: Icon, className = "", children }: ChipProps) {
  return (
    <span
      className={`inline-flex h-6 items-center gap-1.5 rounded-chip px-2.5 text-[12px] font-semibold ${
        variant === "accent" ? "bg-accent-bg text-accent" : "bg-surface-2 text-text-2"
      } ${className}`}
    >
      {Icon && <Icon size={14} strokeWidth={1.75} aria-hidden />}
      {children}
    </span>
  );
}
