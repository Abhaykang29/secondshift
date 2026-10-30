/**
 * Check tab (Pass 3 spec 4.3 step 1): pick up to 3 of the 10 use-case
 * checklists, then start. Places with a recent check appear as compact
 * cards linking to their latest report. Pack choice is shared with the
 * check-up flow through sessionStorage (same key as before).
 */
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import type { HomeSummary, PackSummary } from "../api/extra";
import en from "../i18n/en.json";

const PACK_ICONS: Record<string, string> = {
  falls_older_adults: "🧓",
  babyproofing: "👶",
  home_safety_inspection: "🏠",
  workplace_safety: "🦺",
  pet_safety: "🐾",
  fire_safety: "🔥",
  car_seat_check: "💺",
  earthquake_ready: "🌎",
  home_from_hospital: "🏥",
  mosquito_breeding: "🦟",
};

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
  const [packs, setPacks] = useState<PackSummary[]>([]);
  const [homes, setHomes] = useState<HomeSummary[]>([]);
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
      <h1 className="text-2xl font-semibold">Check a place</h1>
      <p className="mt-1 opacity-80">
        Film a walkthrough, get the hazards with proof — and an honest
        &ldquo;can&rsquo;t tell&rdquo; when a camera can&rsquo;t know.
      </p>

      {homes.length > 0 && (
        <section aria-label="Your places" className="mt-5">
          <h2 className="text-lg font-medium">Your places</h2>
          <div className="mt-2 grid gap-2">
            {homes.map((home) => (
              <Link
                key={home.label}
                to={`/checkup/${home.last_checkup_id}/report`}
                className="flex items-center justify-between rounded border bg-white p-3"
              >
                <span>
                  <span className="font-medium">{home.label}</span>
                  <span className="block text-sm opacity-75">
                    Last check{" "}
                    {home.last_check_at
                      ? new Date(home.last_check_at).toLocaleDateString()
                      : "—"}
                    {" · "}
                    {home.open_findings} open findings
                  </span>
                </span>
                <span aria-hidden className="text-xl opacity-60">›</span>
              </Link>
            ))}
          </div>
        </section>
      )}

      <section aria-label="Choose what to check" className="mt-6">
        <h2 className="text-lg font-medium">Choose what to check</h2>
        <p className="mt-1 text-base opacity-80">
          Pick up to 3 checklists. One walkthrough is checked against all of
          them. {selected.length > 0 ? `${selected.length} picked.` : ""}
        </p>
        {packs.length === 0 ? (
          <p className="mt-2 opacity-70">Packs load from the backend (start it with make dev).</p>
        ) : (
          <div className="mt-3 grid gap-3">
            {packs.map((p) => {
              const on = selected.includes(p.pack_id);
              return (
                <button
                  key={p.pack_id}
                  type="button"
                  aria-pressed={on}
                  onClick={() => togglePack(p.pack_id)}
                  className={`rounded border bg-white p-4 text-left ${
                    on ? "border-[#1f3d2b] bg-[#e9f2ec] ring-2 ring-[#1f3d2b]" : ""
                  }`}
                >
                  <span className="text-2xl" aria-hidden>{PACK_ICONS[p.pack_id] ?? "✓"}</span>{" "}
                  <span className="text-lg font-medium">{p.title}</span>
                  <span className="mt-1 block text-base opacity-80">{p.audience}</span>
                  <span className="block text-sm opacity-70">
                    {p.item_count} checks {on ? "· selected" : ""}
                  </span>
                </button>
              );
            })}
          </div>
        )}
      </section>

      <Link
        to="/checkup/new"
        className="mt-6 flex w-full items-center justify-center rounded bg-[#1f3d2b] px-4 py-3 text-lg font-medium text-white"
      >
        Start the check
      </Link>

      <Link
        to="/custom"
        className="mt-3 block rounded border-2 border-dashed border-emerald-900/50 bg-white/60 p-4"
      >
        <span className="text-lg font-semibold">✍️ Your own checklist</span>
        <span className="block text-sm opacity-75">
          Type 3-10 lines in your own words - checked like any pack.
          Custom checklist - not reviewed by an expert.
        </span>
      </Link>

      <p className="mt-6 text-sm opacity-80">{en.data_note}</p>
    </main>
  );
}
