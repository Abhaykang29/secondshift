import { Link } from "react-router-dom";
import en from "../i18n/en.json";

/**
 * Learn tab (Pass 3 spec 4.7 + 5.4): how it works, the Meta models and
 * their jobs, honest limits, privacy, and the engine-layer page -
 * the same reusable layer under every checklist, with a roadmap of
 * where it goes next (roadmap only, nothing built).
 */

const PIPELINE = [
  { step: "Checklist", text: "Plain-English items - expert packs, or your own words compiled into checks." },
  { step: "Capture", text: "A phone walkthrough, an imported clip (including Ray-Ban Meta glasses), or a fixed camera." },
  { step: "Propose + Sweep", text: "Muse Spark proposes hazards; SAM 3.1 also sweeps filmed rooms on its own, so a miss by one is caught by the other." },
  { step: "Verify", text: "SAM 3.1 must actually find the object (or its anchor, for things that are missing) and Muse Spark judges the close calls." },
  { step: "Verdict", text: "Yes, no, or can't tell - always with the evidence frame and the SAM box. Never a guess dressed up as a fact." },
  { step: "Fix & Re-check", text: "A fix plan from the checklist's own library, a watermarked 'after' picture from Muse Image, and a re-check that confirms the fix." },
];

const ROADMAP = [
  "Robots: an independent check that a chore was actually done and nothing was left on the walking path",
  "Workplaces: daily safety walks",
  "Trucking: walk-around and cargo-securement checks against written rules",
  "Rentals and returns: before/after condition proof",
  "Disaster response: coarse damage triage from residents' videos",
];

export default function LearnPage() {
  return (
    <main className="p-4">
      <h1 className="text-2xl font-semibold">How SecondShift works</h1>

      <section aria-label="How it works" className="mt-4">
        <ol className="grid gap-2">
          {PIPELINE.map((p, i) => (
            <li key={p.step} className="rounded border bg-white p-3">
              <span className="font-semibold">
                {i + 1}. {p.step}
              </span>
              <span className="block text-sm opacity-85">{p.text}</span>
            </li>
          ))}
        </ol>
        <p className="mt-3 rounded bg-[#e9f2ec] p-3 text-sm">
          The engine layer in one line: Checklist (plain English) →
          Capture (phone, glasses, fixed camera) → Propose (Spark) +
          Sweep (SAM) → Verify (SAM + Spark judge) → Verdict (yes / no /
          can&rsquo;t tell + evidence) → Fix &amp; Re-check.
        </p>
        <p className="mt-3 text-sm opacity-85">
          The models: <strong>Muse Spark</strong> proposes hazards, judges
          close calls and compiles rules. <strong>SAM 3.1</strong> does the
          segmentation — a hazard is only &ldquo;confirmed&rdquo; when SAM
          actually finds it. <strong>Muse Image</strong> draws the
          watermarked after-fix pictures. <strong>Muse Voice</strong> is
          not connected in this build, so narration is not transcribed.
        </p>
      </section>

      <section aria-label="Honest limits" className="mt-6">
        <h2 className="text-xl font-semibold">Honest limits</h2>
        <ul className="mt-2 list-disc pl-6">
          <li>It can miss things. A clear report is not a guarantee a place is safe.</li>
          <li>Thin objects — cords, straps, towel rails — are the hardest to see on wide frames.</li>
          <li>It cannot test anything: not smoke alarms, not water temperature, not how tight a strap is. When a check needs hands, it says so.</li>
          <li>Things stored out of sight (a fire extinguisher in a cupboard) come back as &ldquo;needs a human look&rdquo;, not a fail.</li>
          <li>Rooms or moments that were not filmed cannot be checked, and the report lists them.</li>
        </ul>
      </section>

      <section aria-label="Privacy" className="mt-6">
        <h2 className="text-xl font-semibold">Privacy</h2>
        <p className="mt-2">{en.data_note}</p>
        <p className="mt-2">
          People in frames are blurred before pictures are shown or shared.
          Live Check keeps no video at all — frames are checked and
          discarded, and it never runs in a bathroom.
        </p>
      </section>

      <section aria-label="Where the same layer goes next" className="mt-6">
        <h2 className="text-xl font-semibold">Where the same layer goes next</h2>
        <p className="mt-1 text-sm opacity-80">
          Roadmap only — none of this is built yet. The point of the
          engine layer is that a new checklist is words, not new code.
        </p>
        <ul className="mt-2 list-disc pl-6">
          {ROADMAP.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </section>

      <section aria-label="Team tools" className="mt-6">
        <h2 className="text-xl font-semibold">Team tools</h2>
        <div className="mt-2 flex flex-wrap gap-2">
          <Link to="/rules" className="rounded border bg-white px-3 py-2">Rule compiler</Link>
          <Link to="/ask" className="rounded border bg-white px-3 py-2">Ask about a report</Link>
          <Link to="/eval" className="rounded border bg-white px-3 py-2">Eval</Link>
          <Link to="/settings" className="rounded border bg-white px-3 py-2">Settings</Link>
        </div>
      </section>
    </main>
  );
}
