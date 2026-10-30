import { NavLink } from "react-router-dom";

/**
 * Bottom tab bar (Pass 3 spec 4.2): Check / Live / Homes / Learn.
 * Fixed to the bottom, safe-area aware, 48px+ tap targets, icon + label.
 * Inline SVG icons only - no stock imagery.
 */

const TABS = [
  {
    to: "/",
    label: "Check",
    end: true,
    icon: (
      <path
        d="M4 11.5 12 4l8 7.5M6.5 10v9h11v-9M9.5 14.5l2 2 3.5-4"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    ),
  },
  {
    to: "/live",
    label: "Live",
    end: false,
    icon: (
      <>
        <circle cx="12" cy="12" r="3.2" />
        <path
          d="M5.5 9.5a9 9 0 0 1 13 0M8 6.8a13 13 0 0 1 8 0M5.5 14.5a9 9 0 0 0 13 0M8 17.2a13 13 0 0 0 8 0"
          strokeLinecap="round"
        />
      </>
    ),
  },
  {
    to: "/homes",
    label: "Homes",
    end: false,
    icon: (
      <path
        d="M4 20V9.5L12 3l8 6.5V20h-5.5v-6h-5v6H4z"
        strokeLinejoin="round"
      />
    ),
  },
  {
    to: "/learn",
    label: "Learn",
    end: false,
    icon: (
      <path
        d="M12 5.5C10 4 7.5 3.5 4.5 3.8v13.4c3-.3 5.5.2 7.5 1.7 2-1.5 4.5-2 7.5-1.7V3.8c-3-.3-5.5.2-7.5 1.7zm0 0v13.4"
        strokeLinejoin="round"
      />
    ),
  },
];

export default function TabBar() {
  return (
    <nav
      aria-label="Main"
      className="fixed inset-x-0 bottom-0 z-40 border-t border-[#d8d2c4] bg-[#faf7f2]/95 backdrop-blur"
      style={{ paddingBottom: "env(safe-area-inset-bottom)" }}
    >
      <div className="mx-auto grid max-w-md grid-cols-4">
        {TABS.map((tab) => (
          <NavLink
            key={tab.to}
            to={tab.to}
            end={tab.end}
            className={({ isActive }) =>
              `flex min-h-[56px] flex-col items-center justify-center gap-0.5 px-2 py-2 text-sm ${
                isActive ? "font-semibold text-[#1f3d2b]" : "text-neutral-600"
              }`
            }
          >
            {({ isActive }) => (
              <>
                <svg
                  viewBox="0 0 24 24"
                  className="h-6 w-6"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth={isActive ? 2 : 1.6}
                  aria-hidden
                >
                  {tab.icon}
                </svg>
                {tab.label}
              </>
            )}
          </NavLink>
        ))}
      </div>
    </nav>
  );
}
