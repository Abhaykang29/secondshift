import type { ReactNode } from "react";

interface CardProps {
  title?: ReactNode;
  action?: ReactNode;
  footer?: ReactNode;
  dashed?: boolean;
  className?: string;
  children: ReactNode;
}

/** Card (spec 3.4): surface, 1px border, radius card, 16px padding. */
export default function Card({ title, action, footer, dashed, className = "", children }: CardProps) {
  return (
    <section
      className={`rounded-card border bg-surface p-4 ${
        dashed ? "border-dashed border-border-strong" : "border-border"
      } ${className}`}
    >
      {(title || action) && (
        <header className="mb-3 flex items-start justify-between gap-2">
          {title && <h3 className="text-[16px] font-semibold leading-[22px]">{title}</h3>}
          {action}
        </header>
      )}
      {children}
      {footer && <div className="mt-3 border-t border-border pt-3">{footer}</div>}
    </section>
  );
}
