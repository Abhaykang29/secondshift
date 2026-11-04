import { NavLink } from "react-router-dom";
import { BookOpen, House, Radio, ScanLine, type LucideIcon } from "lucide-react";

/**
 * Bottom tab bar (redesign spec 4.2): Check / Live / Homes / Learn.
 * 64px + safe-area inset, surface, top border; active tab is accent
 * with a 2px indicator bar at its top edge.
 */

const TABS: { to: string; label: string; end: boolean; icon: LucideIcon }[] = [
  { to: "/", label: "Check", end: true, icon: ScanLine },
  { to: "/live", label: "Live", end: false, icon: Radio },
  { to: "/homes", label: "Homes", end: false, icon: House },
  { to: "/learn", label: "Learn", end: false, icon: BookOpen },
];

export default function TabBar() {
  return (
    <nav
      aria-label="Main"
      className="fixed inset-x-0 bottom-0 z-40 border-t border-border bg-surface"
      style={{ paddingBottom: "env(safe-area-inset-bottom)" }}
    >
      <div className="mx-auto grid h-[60px] w-full max-w-[640px] grid-cols-4">
        {TABS.map((tab) => {
          const Icon = tab.icon;
          return (
            <NavLink
              key={tab.to}
              to={tab.to}
              end={tab.end}
              className={({ isActive }) =>
                `relative mx-1 flex flex-col items-center justify-center gap-1 px-2 text-[11.5px] font-semibold transition-colors duration-[120ms] ${
                  isActive ? "text-accent" : "text-text-3 hover:text-text-2"
                }`
              }
            >
              {({ isActive }) => (
                <>
                  {isActive && (
                    <span className="absolute inset-x-3 top-0 h-[3px] rounded-b-full bg-accent" aria-hidden />
                  )}
                  <Icon size={23} strokeWidth={isActive ? 2.25 : 1.75} aria-hidden />
                  {tab.label}
                </>
              )}
            </NavLink>
          );
        })}
      </div>
    </nav>
  );
}
