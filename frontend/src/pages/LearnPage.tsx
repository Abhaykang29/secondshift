import { Link } from "react-router-dom";
import {
  BadgeCheck,
  Camera,
  ChevronRight,
  ClipboardList,
  RefreshCw,
  ScanSearch,
  type LucideIcon,
} from "lucide-react";
import HonestyCard from "../components/HonestyCard";
import Card from "../components/ui/Card";
import Chip from "../components/ui/Chip";
import en from "../i18n/en.json";

/**
 * Learn tab (Pass 3 spec 4.7 + 5.4, redesign spec 5.9): how it
 * works, the Meta models and their jobs, honest limits, privacy,
 * and the engine-layer roadmap (roadmap only, nothing built).
 */

const FLOW: { title: string; line: string; icon: LucideIcon }[] = [
  { title: "Rules", line: "Plain-English rules in.", icon: ClipboardList },
  { title: "Camera", line: "A phone walkthrough or imported clip.", icon: Camera },
  { title: "Check", line: "The models look for the evidence.", icon: ScanSearch },
  { title: "Verdict + proof", line: "Yes, no, or can't tell - with the frame.", icon: BadgeCheck },
  { title: "Re-check", line: "Run it again and see what changed.", icon: RefreshCw },
];

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

const linkBtn =
  "inline-flex min-h-[44px] items-center justify-center gap-2 rounded-btn bg-surface-3 px-4 text-[15px] font-semibold text-text transition-all duration-[120ms] hover:bg-surface-3-hover active:scale-[0.98]";

export default function LearnPage() {
  return (
    <main className="mx-auto w-full max-w-[720px]">
      <h1 className="text-[24px] font-[650] leading-[30px] tracking-[-0.01em]">
        How SecondShift works
      </h1>
      <p className="mt-1 text-[15px] leading-[22px] text-text-2">
        Plain-English rules in. Yes, no, or can&rsquo;t tell out, with the frame that proves it.
      </p>

      <section aria-label="Engine flow" className="mt-6">
        <Card>
          <div className="flex flex-col gap-0 lg:flex-row lg:items-start lg:gap-1">
            {FLOW.map((node, i) => {
              const Icon = node.icon;
              return (
                <div key={node.title} className="flex flex-1 items-start gap-3 lg:flex-col lg:gap-0">
                  <div className="flex flex-col items-center self-stretch lg:hidden">
                    <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-tile bg-accent-bg">
                      <Icon size={20} strokeWidth={1.75} className="text-accent" />
                    </span>
                    {i < FLOW.length - 1 && <span className="mt-1 w-px flex-1 bg-border-strong" aria-hidden />}
                  </div>
                  <span className="hidden h-9 w-9 shrink-0 items-center justify-center rounded-tile bg-accent-bg lg:flex">
                    <Icon size={20} strokeWidth={1.75} className="text-accent" />
                  </span>
                  <div className="min-w-0 pb-4 lg:pb-0 lg:pt-2">
                    <p className="text-[15px] font-semibold leading-[22px]">{node.title}</p>
                    <p className="text-[13px] leading-[18px] text-text-2">{node.line}</p>
                    {node.title === "Check" && (
                      <div className="mt-2 flex flex-wrap gap-1.5">
                        <Chip><span className="font-mono text-[12.5px]">Muse Spark</span></Chip>
                        <Chip><span className="font-mono text-[12.5px]">SAM 3.1</span></Chip>
                        <Chip><span className="font-mono text-[12.5px]">Muse Image</span></Chip>
                      </div>
                    )}
                  </div>
                  {i < FLOW.length - 1 && (
                    <ChevronRight size={18} strokeWidth={1.75} className="mx-1 mt-2 hidden shrink-0 text-text-3 lg:block" aria-hidden />
                  )}
                </div>
              );
            })}
          </div>
        </Card>
      </section>

      <section aria-label="How it works" className="mt-8">
        <ol className="grid gap-3">
          {PIPELINE.map((p, i) => (
            <li key={p.step}>
              <Card>
                <span className="text-[15px] font-semibold">
                  <span className="font-mono tabular-nums text-text-3">{i + 1}.</span> {p.step}
                </span>
                <span className="mt-0.5 block text-[14px] leading-[20px] text-text-2">{p.text}</span>
              </Card>
            </li>
          ))}
        </ol>
        <div className="mt-3">
          <Card>
            <p className="text-[14px] leading-[20px]">
              The engine layer in one line: Checklist (plain English) →
              Capture (phone, glasses, fixed camera) → Propose (Spark) +
              Sweep (SAM) → Verify (SAM + Spark judge) → Verdict (yes / no /
              can&rsquo;t tell + evidence) → Fix &amp; Re-check.
            </p>
            <p className="mt-3 text-[14px] leading-[20px] text-text-2">
              The models: <strong>Muse Spark</strong> proposes hazards, judges
              close calls and compiles rules. <strong>SAM 3.1</strong> does the
              segmentation — a hazard is only &ldquo;confirmed&rdquo; when SAM
              actually finds it. <strong>Muse Image</strong> draws the
              watermarked after-fix pictures. <strong>Muse Voice</strong> is
              not connected in this build, so narration is not transcribed.
            </p>
          </Card>
        </div>
      </section>

      <HonestyCard />

      <section aria-label="Consistency" className="mt-8">
        <Card title="Same video, same answer">
          <p className="text-[15px] leading-[22px]">
            Results are cached per video, so the same video always gives the
            same answer. A fresh analysis can differ: in our measured pair of
            independent runs of the same video (2026-11-03), the two runs
            agreed exactly on 4 of the 8 problems found across both runs —
            1 changed verdict and 3 appeared in only one run. Every finding
            shows its evidence frame so you can judge it yourself.
          </p>
        </Card>
      </section>

      <section aria-label="Honest limits" className="mt-8">
        <Card title="Honest limits">
          <ul className="list-disc space-y-1.5 pl-6 text-[15px] leading-[22px]">
            <li>It can miss things. A clear report is not a guarantee a place is safe.</li>
            <li>Thin objects — cords, straps, towel rails — are the hardest to see on wide frames.</li>
            <li>It cannot test anything: not smoke alarms, not water temperature, not how tight a strap is. When a check needs hands, it says so.</li>
            <li>Things stored out of sight (a fire extinguisher in a cupboard) come back as &ldquo;needs a human look&rdquo;, not a fail.</li>
            <li>Rooms or moments that were not filmed cannot be checked, and the report lists them.</li>
          </ul>
        </Card>
      </section>

      <section aria-label="Privacy" className="mt-8">
        <Card title="Privacy">
          <p className="text-[15px] leading-[22px]">{en.data_note}</p>
          <p className="mt-2 text-[15px] leading-[22px]">
            People in frames are blurred before pictures are shown or shared.
            Live Check keeps no video at all — frames are checked and
            discarded, and it never runs in a bathroom.
          </p>
        </Card>
      </section>

      <section aria-label="Where the same layer goes next" className="mt-8">
        <Card title="Where the same layer goes next">
          <p className="text-[14px] leading-[20px] text-text-2">
            Roadmap only — none of this is built yet. The point of the
            engine layer is that a new checklist is words, not new code.
          </p>
          <ul className="mt-3 grid gap-2">
            {ROADMAP.map((item) => (
              <li key={item} className="flex items-start justify-between gap-3">
                <span className="text-[15px] leading-[22px]">{item}</span>
                <Chip className="shrink-0">Not built yet</Chip>
              </li>
            ))}
          </ul>
        </Card>
      </section>

      <section aria-label="Team tools" className="mt-8">
        <h2 className="text-[17px] font-semibold leading-[24px]">Team tools</h2>
        <div className="mt-2 flex flex-wrap gap-2">
          <Link to="/rules" className={linkBtn}>Rule compiler</Link>
          <Link to="/ask" className={linkBtn}>Ask about a report</Link>
          <Link to="/eval" className={linkBtn}>Eval</Link>
          <Link to="/settings" className={linkBtn}>Settings</Link>
        </div>
      </section>
    </main>
  );
}
