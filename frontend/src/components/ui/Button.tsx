import type { ButtonHTMLAttributes, ReactNode } from "react";
import type { LucideIcon } from "lucide-react";

export type ButtonVariant = "primary" | "secondary" | "ghost" | "danger";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: "md" | "lg";
  icon?: LucideIcon;
  fullWidth?: boolean;
  children: ReactNode;
}

const VARIANTS: Record<ButtonVariant, string> = {
  primary: "bg-accent text-text-inverse hover:bg-accent-hover",
  secondary: "bg-surface text-text border border-border-strong hover:bg-surface-2",
  ghost: "text-accent hover:bg-accent-bg",
  danger: "text-bad hover:bg-bad-bg",
};

/** The one button (spec 3.1): 44px md / 52px lg, radius btn, 15/600. */
export default function Button({
  variant = "secondary",
  size = "md",
  icon: Icon,
  fullWidth,
  className = "",
  children,
  ...rest
}: ButtonProps) {
  return (
    <button
      className={`inline-flex items-center justify-center gap-2 rounded-btn px-4 text-[15px] font-semibold transition-all duration-[120ms] active:scale-[0.98] disabled:pointer-events-none disabled:opacity-45 ${
        size === "lg" ? "min-h-[52px]" : "min-h-[44px]"
      } ${VARIANTS[variant]} ${fullWidth ? "w-full" : ""} ${className}`}
      {...rest}
    >
      {Icon && <Icon size={20} strokeWidth={1.75} aria-hidden />}
      {children}
    </button>
  );
}
