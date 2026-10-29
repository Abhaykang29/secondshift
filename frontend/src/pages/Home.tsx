/**
 * Home - Phase 0 shell.
 * Two big cards (Check a home / Watch one spot), pack selector, language +
 * text-size toggles land fully in Phase 3; the cards and footer copy are
 * real from Phase 0.
 */
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import type { PackSummary } from "../api/extra";
import en from "../i18n/en.json";

const PACK_ICONS: Record<string, string> = {
  falls_older_adults: "🧓",
  babyproofing: "👶",
  fire_safety: "🔥",
  earthquake_ready: "🌎",
  pet_safety: "🐾",
  home_from_hospital: "🏥",
  mosquito_breeding: "🦟",
};

export default function Home() {
  const [packs, setPacks] = useState<PackSummary[]>([]);
  const [largeText, setLargeText] = useState(false);
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
      .then((r) => setPacks(r.packs))
      .catch(() => setPacks([]));
  }, []);

  useEffect(() => {
    document.documentElement.classList.toggle("large-text", largeText);
  }, [largeText]);

  return (
    <main className="mx-auto max-w-2xl p-6">
      <h1 className="text-3xl font-semibold">SecondShift</h1>
      <p className="mt-2">Check spaces, not people.</p>

      <div className="mt-6 grid gap-4">
        <Link to="/checkup/new" className="block rounded border p-6 text-xl">
          {en.check_a_home}
          <span className="mt-1 block text-base opacity-80">
            Film a short walkthrough. Get a ranked list of hazards, confirmed by SAM.
          </span>
        </Link>
        <Link to="/watch/setup" className="block rounded border p-6 text-xl">
          {en.watch_one_spot}
          <span className="mt-1 block text-base opacity-80">
            One spot, one plain-English rule. Answers: met, not met, or cannot tell.
          </span>
        </Link>
      </div>

      <section className="mt-6">
        <h2 className="text-lg font-medium">What should we check for?</h2>
        <p className="mt-1 text-base opacity-80">
          Pick up to 3 checklists. One walkthrough is checked against all of them.
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
                  className={`rounded border p-4 text-left ${on ? "border-blue-700 bg-blue-50" : ""}`}
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

      <div className="mt-6 flex gap-3">
        <button
          type="button"
          className="rounded border px-4"
          onClick={() => setLargeText((v) => !v)}
        >
          Large text: {largeText ? "on" : "off"}
        </button>
        <span className="self-center">Language: English / हिन्दी (needs native review)</span>
      </div>

      <p className="mt-6 text-sm opacity-80">{en.data_note}</p>
    </main>
  );
}
