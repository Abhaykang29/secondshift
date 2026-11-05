/**
 * Check tab (Pass 3 spec 4.3 step 1, redesign spec 5.6): pick up to
 * 3 of the 10 use-case checklists, then start. Places with a recent
 * check appear as compact cards linking to their latest report. Pack
 * choice is shared with the check-up flow through sessionStorage
 * (same key as before).
 */
import { useEffect, useState } from "react";
import { BadgeCheck, Bot, Check, ChevronRight, Info, type LucideIcon } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api/client";
import { plural } from "../plural";
import type { HomeSummary, PackSummary } from "../api/extra";
import en from "../i18n/en.json";
import Banner from "../components/ui/Banner";
import Button from "../components/ui/Button";
import { PackIcon } from "../components/ui/PackIcon";
import { PACKS } from "../components/ui/packs";

/** Use-case order from the Pass 3 spec (falls is the hero). */
const PACK_ORDER = [
  "robot_task_check",
  "falls_older_adults",
  "babyproofing",
  "home_safety_inspection",
  "workplace_safety",
  "pet_safety",
  "fire_safety",
  "car_seat_check",
  "earthquake_ready",
  "home_from_hospital",
  "mosquito_breeding",
];

function orderPacks(packs: PackSummary[]): PackSummary[] {
  const rank = (id: string) => {
    const i = PACK_ORDER.indexOf(id);
    return i === -1 ? PACK_ORDER.length : i;
  };
  return [...packs].sort((a, b) => rank(a.pack_id) - rank(b.pack_id));
}

export default function Home() {
  const navigate = useNavigate();
  const [packs, setPacks] = useState<PackSummary[]>([]);
  const [homes, setHomes] = useState<HomeSummary[]>([]);
  const [about, setAbout] = useState<PackSummary | null>(null);
  const [selected, setSelected] = useState<string[]>(() => {
    try {
      return JSON.parse(sessionStorage.getItem("pack_selection") ?? "[]") as string[];
    } catch {
      return [];
    }
  });

  function quickStart(packIds: string[]) {
    try {
      sessionStorage.setItem("pack_selection", JSON.stringify(packIds));
    } catch {
      /* private mode: the selection still applies for this navigation */
    }
    setSelected(packIds);
    navigate("/checkup/new");
  }

  function togglePack(packId: string) {
    setSelected((prev) => {
      const next = prev.includes(packId)
        ? prev.filter((x) => x !== packId)
        : prev.length >= 3
          ? prev
          : [...prev, packId];
      sessionStorage.setItem("pack_selection", JSON.stringify(next));
      return next;
    });
  }

  useEffect(() => {
    api
      .packs()
      .then((r) => setPacks(orderPacks(r.packs)))
      .catch(() => setPacks([]));
    api
      .homes()
      .then((r) => setHomes(r.homes))
      .catch(() => setHomes([]));
  }, []);

  return (
    <main className="pt-1">
      <h1 className="px-1 text-[26px] font-extrabold leading-[32px]">
        Check a place
      </h1>
      <p className="mt-1 px-1 text-[15px] text-text-3">
        Film a walkthrough, get the hazards with proof — and an honest
        &ldquo;can&rsquo;t tell&rdquo; when a camera can&rsquo;t know.
      </p>

      <section aria-label="Just film it" className="mt-6">
        <QuickCard
          icon={Bot}
          title="Just film it: is the job done, and is it safe?"
          line="No choosing, no typing. Film the room after any task (cooking, cleaning, tidying, leaving) done by a robot or a person. It checks what was left undone and anything unsafe: stove left on, things near the stove, electronics by the sink, table not cleared, open doors, spills, clutter, plus home and fire safety."
          onClick={() => quickStart(["robot_task_check", "fire_safety", "home_safety_inspection"])}
          hero
        />
      </section>

      {homes.length > 0 && (
        <section aria-label="Recent checks" className="mt-5">
          <div className="flex items-baseline justify-between px-1">
            <h2 className="text-[19px] font-bold leading-[24px]">Recent checks</h2>
            <Link to="/homes" className="rounded-btn px-2 py-1 text-[15px] font-semibold text-accent hover:bg-accent-bg">
              See all
            </Link>
          </div>
          <div className="mt-2 overflow-hidden rounded-card bg-surface shadow-card">
            {homes.slice(0, 3).map((home, i) => (
              <Link
                key={home.label}
                to={`/checkup/${home.last_checkup_id}/report`}
                className={`flex min-h-[60px] items-center gap-3 px-3 py-2.5 transition-colors duration-[120ms] hover:bg-surface-2 ${
                  i > 0 ? "border-t border-border" : ""
                }`}
              >
                <PackIcon packId={home.pack_ids[0] ?? "custom"} size={36} />
                <span className="min-w-0 flex-1">
                  <span className="flex items-center gap-1 font-semibold">
                    <span className="truncate">{home.label.replace(/\s*\(recorded\)\s*$/i, "")}</span>
                    {/\(recorded\)\s*$/i.test(home.label) && (
                      <BadgeCheck size={15} strokeWidth={2.25} className="shrink-0 text-accent" aria-label="Recorded real result" />
                    )}
                  </span>
                  <span className="block text-[13px] text-text-3">
                    {home.last_check_at
                      ? new Date(home.last_check_at).toLocaleDateString(undefined, { month: "short", day: "numeric" })
                      : "—"}
                    {" · "}
                    {plural(home.open_findings, "open finding")}
                  </span>
                </span>
                <ChevronRight size={20} strokeWidth={1.75} className="shrink-0 text-text-3" aria-hidden />
              </Link>
            ))}
          </div>
        </section>
      )}

      <details className="group mt-6" open={selected.length > 0}>
        <summary className="flex min-h-[44px] cursor-pointer list-none items-center justify-between rounded-card bg-surface px-4 py-3 shadow-card">
          <span className="text-[16px] font-bold">More checklists</span>
          <span className="text-[13px] text-text-3">{packs.length} specialised checks, optional</span>
        </summary>
      <section aria-label="Choose what to check" className="mt-4">
        <div className="flex items-baseline justify-between gap-2 px-1">
          <h2 className="text-[19px] font-bold leading-[24px]">Choose what to check</h2>
          <span className="font-mono text-[12.5px] tabular-nums text-text-3">
            {selected.length} / 3
          </span>
        </div>
        <p className="mt-1 px-1 text-[14px] leading-[20px] text-text-3">
          Pick up to 3. One walkthrough is checked against all of them.
        </p>
        {packs.length === 0 ? (
          <p className="mt-2 text-text-3">Packs load from the backend (start it with make dev).</p>
        ) : (
          <div className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-3">
            {packs.map((p) => {
              const on = selected.includes(p.pack_id);
              const blocked = !on && selected.length >= 3;
              const name = PACKS[p.pack_id]?.name ?? p.title;
              return (
                <div
                  key={p.pack_id}
                  className={`relative rounded-card transition-colors duration-[120ms] ${
                    on
                      ? "border-2 border-accent bg-accent-bg"
                      : "border border-border bg-surface hover:border-border-strong"
                  } ${blocked ? "opacity-50" : ""}`}
                >
                  <button
                    type="button"
                    aria-pressed={on}
                    disabled={blocked}
                    onClick={() => togglePack(p.pack_id)}
                    className="flex min-h-[112px] w-full flex-col p-[14px] text-left"
                  >
                    <PackIcon packId={p.pack_id} />
                    <span className="mt-2 line-clamp-2 text-[15px] font-semibold leading-[20px]">
                      {name}
                    </span>
                    <span className="mt-auto pt-2 font-mono text-[12.5px] tabular-nums text-text-3">
                      {p.item_count} checks
                    </span>
                  </button>
                  {on ? (
                    <span
                      className="pointer-events-none absolute right-2 top-2 flex h-5 w-5 items-center justify-center rounded-full bg-accent"
                      aria-hidden
                    >
                      <Check size={12} strokeWidth={2.5} className="text-text-inverse" />
                    </span>
                  ) : (
                    <button
                      type="button"
                      aria-label={`About ${name}`}
                      onClick={() => setAbout(p)}
                      className="absolute right-1 top-1 inline-flex h-11 w-11 items-center justify-center rounded-btn text-text-3 transition-colors duration-[120ms] hover:bg-surface-2"
                    >
                      <Info size={18} strokeWidth={1.75} aria-hidden />
                    </button>
                  )}
                </div>
              );
            })}
            <Link
              to="/custom"
              className="flex min-h-[112px] flex-col rounded-card border border-dashed border-border-strong bg-surface p-[14px] transition-colors duration-[120ms] hover:border-accent"
            >
              <PackIcon packId="custom" />
              <span className="mt-2 text-[15px] font-semibold leading-[20px]">
                Your own checklist
              </span>
              <span className="mt-1 block text-[13px] leading-[18px] text-text-2">
                Type 1-10 lines in your own words, e.g. &ldquo;Nothing blocking the exit door.&rdquo; Checked like any pack.
                Custom checklist - not reviewed by an expert.
              </span>
            </Link>
          </div>
        )}
      </section>
      </details>

      <div className="mt-6">
        <Banner kind="privacy">{en.data_note}</Banner>
      </div>

      {selected.length > 0 && (
      <div className="sticky bottom-16 z-20 -mx-4 mt-6 border-t border-border bg-surface px-4 py-3">
        <Button
          variant="primary"
          size="lg"
          fullWidth
          disabled={selected.length === 0}
          onClick={() => navigate("/checkup/new")}
        >
          Start the check
        </Button>
      </div>
      )}

      {about && (
        <div className="fixed inset-0 z-50" role="dialog" aria-modal="true" aria-label={PACKS[about.pack_id]?.name ?? about.title}>
          <button
            type="button"
            aria-label="Close"
            onClick={() => setAbout(null)}
            className="absolute inset-0 h-full w-full cursor-default"
            style={{ backgroundColor: "var(--overlay)" }}
          />
          <div className="absolute inset-x-0 bottom-0 rounded-t-card border-t border-border bg-surface p-4 pb-8 shadow-menu">
            <div className="flex items-start gap-3">
              <PackIcon packId={about.pack_id} />
              <div className="min-w-0 flex-1">
                <h3 className="text-[16px] font-semibold leading-[22px]">
                  {PACKS[about.pack_id]?.name ?? about.title}
                </h3>
                <p className="mt-1 text-[14px] leading-[20px] text-text-2">{about.audience}</p>
                <p className="mt-2 font-mono text-[12.5px] tabular-nums text-text-3">
                  {about.item_count} checks
                </p>
              </div>
            </div>
            <div className="mt-4">
              <Button variant="secondary" fullWidth onClick={() => setAbout(null)}>
                Close
              </Button>
            </div>
          </div>
        </div>
      )}
    </main>
  );
}

function QuickCard({
  icon: Icon,
  title,
  line,
  onClick,
  hero,
}: {
  icon: LucideIcon;
  title: string;
  line: string;
  onClick: () => void;
  hero?: boolean;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`flex w-full items-start gap-3 rounded-card p-4 text-left shadow-card transition-colors duration-[120ms] ${
        hero ? "bg-accent text-text-inverse hover:bg-accent-hover" : "bg-surface hover:bg-surface-2"
      }`}
    >
      <span className={`inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-full ${hero ? "bg-white/20" : "bg-accent"} text-text-inverse`} aria-hidden>
        <Icon size={22} strokeWidth={2} />
      </span>
      <span className="min-w-0">
        <span className={`block font-bold ${hero ? "text-[18px] leading-[23px]" : "text-[16px] leading-[21px]"}`}>{title}</span>
        <span className={`mt-1 block text-[13.5px] leading-[19px] ${hero ? "text-white/90" : "text-text-2"}`}>{line}</span>
      </span>
      <ChevronRight size={20} strokeWidth={1.75} className={`ml-auto mt-3 shrink-0 ${hero ? "text-white" : "text-text-3"}`} aria-hidden />
    </button>
  );
}
