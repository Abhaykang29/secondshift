/**
 * Check tab (Pass 3 spec 4.3 step 1, redesign spec 5.6): pick up to
 * 3 of the 10 use-case checklists, then start. Places with a recent
 * check appear as compact cards linking to their latest report. Pack
 * choice is shared with the check-up flow through sessionStorage
 * (same key as before).
 */
import { useEffect, useState } from "react";
import { Check, ChevronRight, Info } from "lucide-react";
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
    <main className="p-4">
      <h1 className="text-[24px] font-[650] leading-[30px] tracking-[-0.01em]">
        Check a place
      </h1>
      <p className="mt-1 text-text-2">
        Film a walkthrough, get the hazards with proof — and an honest
        &ldquo;can&rsquo;t tell&rdquo; when a camera can&rsquo;t know.
      </p>

      {homes.length > 0 && (
        <section aria-label="Your places" className="mt-5">
          <h2 className="text-[17px] font-semibold leading-[24px]">Your places</h2>
          <div className="mt-2 grid gap-2">
            {homes.map((home) => (
              <Link
                key={home.label}
                to={`/checkup/${home.last_checkup_id}/report`}
                className="flex items-center justify-between rounded-card border border-border bg-surface p-3 transition-colors duration-[120ms] hover:border-border-strong"
              >
                <span>
                  <span className="font-semibold">{home.label}</span>
                  <span className="block text-[13px] text-text-3">
                    Last check{" "}
                    {home.last_check_at
                      ? new Date(home.last_check_at).toLocaleDateString()
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

      <section aria-label="Choose what to check" className="mt-6">
        <div className="flex items-baseline justify-between gap-2">
          <h2 className="text-[17px] font-semibold leading-[24px]">Choose what to check</h2>
          <span className="font-mono text-[12.5px] tabular-nums text-text-3">
            {selected.length} / 3
          </span>
        </div>
        <p className="mt-1 text-[14px] leading-[20px] text-text-2">
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
                Type 3-10 lines in your own words - checked like any pack.
                Custom checklist - not reviewed by an expert.
              </span>
            </Link>
          </div>
        )}
      </section>

      <div className="mt-6">
        <Banner kind="privacy">{en.data_note}</Banner>
      </div>

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
