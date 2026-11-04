import type { ReactNode } from "react";

interface CardProps {
  title?: ReactNode;
  action?: ReactNode;
  footer?: ReactNode;
  dashed?: boolean;
  className?: string;
  children: ReactNode;
}

/** Card: white surface lifted by a soft shadow (no hard border), radius 12, 16px padding. Dashed variant = can't tell. */
export default function Card({ title, action, footer, dashed, className = "", children }: CardProps) {
  return (
    <section
      className={`rounded-card bg-surface p-4 ${
        dashed ? "border border-dashed border-border-strong" : "shadow-card"
      } ${className}`}
    >
      {(title || action) && (
        <header className="mb-3 flex items-start justify-between gap-2">
          {title && <h3 className="text-[17px] font-bold leading-[22px]">{title}</h3>}
          {action}
        </header>
      )}
      {children}
      {footer && <div className="mt-3 border-t border-border pt-3">{footer}</div>}
    </section>
  );
}
