import { useEffect, useRef, useState } from "react";
import { MoreHorizontal } from "lucide-react";

export interface MenuItem {
  label: string;
  danger?: boolean;
  onClick: () => void;
}

/** Overflow menu (spec 3.9): 44x44 ghost button, small menu with the
 * one allowed shadow; destructive items use danger styling and still
 * go through the caller's existing confirm flow. */
export default function OverflowMenu({
  items,
  label = "More actions",
}: {
  items: MenuItem[];
  label?: string;
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onDoc = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, [open ]);

  return (
    <div className="relative" ref={ref}>
      <button
        type="button"
        aria-label={label}
        aria-haspopup="menu"
        aria-expanded={open}
        onClick={() => setOpen((o) => !o)}
        className="inline-flex h-11 w-11 items-center justify-center rounded-btn text-text-2 transition-colors duration-[120ms] hover:bg-surface-2"
      >
        <MoreHorizontal size={20} strokeWidth={1.75} aria-hidden />
      </button>
      {open && (
        <div
          role="menu"
          className="absolute right-0 top-full z-30 mt-1 min-w-[220px] rounded-card bg-surface shadow-card py-1 shadow-menu"
        >
          {items.map((item) => (
            <button
              key={item.label}
              type="button"
              role="menuitem"
              onClick={() => {
                setOpen(false);
                item.onClick();
              }}
              className={`flex min-h-[44px] w-full items-center px-4 text-left text-[15px] transition-colors duration-[120ms] hover:bg-surface-2 ${
                item.danger ? "text-bad" : "text-text"
              }`}
            >
              {item.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
