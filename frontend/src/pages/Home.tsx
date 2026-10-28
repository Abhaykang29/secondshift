/**
 * Home - Phase 0 shell.
 * Two big cards (Check a home / Watch one spot), pack selector, language +
 * text-size toggles land fully in Phase 3; the cards and footer copy are
 * real from Phase 0.
 */
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import type { PackSummary } from "../api/types";
import en from "../i18n/en.json";

export default function Home() {
  const [packs, setPacks] = useState<PackSummary[]>([]);
  const [largeText, setLargeText] = useState(false);

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
        <h2 className="text-lg font-medium">Checklist packs</h2>
        {packs.length === 0 ? (
          <p className="mt-2 opacity-70">Packs load from the backend (start it with make dev).</p>
        ) : (
          <ul className="mt-2 list-disc pl-6">
            {packs.map((p) => (
              <li key={p.pack_id}>
                {p.title} — {p.item_count} checks
              </li>
            ))}
          </ul>
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
