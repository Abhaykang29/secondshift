import { useEffect, useState } from "react";
import { plural } from "../plural";
import { useParams } from "react-router-dom";
import { api } from "../api/client";
import type { Report } from "../api/types";
import Button from "../components/ui/Button";
import TallyBar from "../components/ui/TallyBar";
import VerdictChip from "../components/ui/VerdictChip";

/**
 * Fix tracker (spec 5.1 step 7): check off fixes; progress bar; the
 * statuses persist in the report and drive the re-check baseline.
 */
export default function Fixes() {
  const { id = "" } = useParams();
  const [report, setReport] = useState<Report | null>(null);
  const [notes, setNotes] = useState<Record<string, string>>({});

  useEffect(() => {
    api.report(id).then(setReport).catch(() => setReport(null));
  }, [id]);

  if (!report) return <main className="mx-auto w-full max-w-[720px] p-4"><p>Loading fixes...</p></main>;
  const done = report.fixes.filter((f) => f.status === "done").length;

  async function toggle(fixId: string, status: string) {
    const updated = await api.updateFix(id, fixId, status === "done" ? "todo" : "done");
    setReport((r) => (r ? { ...r, fixes: r.fixes.map((f) => (f.id === fixId ? updated : f)) } : r));
  }

  async function saveNote(fixId: string, status: string) {
    const note = (notes[fixId] ?? "").trim();
    const updated = await api.updateFix(id, fixId, status, note || undefined);
    setReport((r) => (r ? { ...r, fixes: r.fixes.map((f) => (f.id === fixId ? updated : f)) } : r));
  }

  return (
    <main className="mx-auto w-full max-w-[720px] p-4">
      <h1 className="text-[24px] font-[650] leading-[30px] tracking-[-0.01em]">Fix tracker</h1>
      <p className="mt-2 font-mono text-[12.5px] tabular-nums text-text-2">
        {done} of {plural(report.fixes.length, "fix", "fixes")} done
      </p>
      <div className="mt-2">
        <TallyBar
          compact
          counts={{ bad: 0, warn: 0, unk: report.fixes.length - done, ok: done }}
          labels={[["problem", "problems"], ["need a look", "need a look"], ["to-do", "to-dos"], ["done", "done"]]}
        />
      </div>
      {report.fixes.map((card) => (
        <div key={card.id} className="mt-3 rounded-card bg-surface shadow-card p-4">
          <label className="flex items-start gap-3">
            <input type="checkbox" checked={card.status === "done"} className="mt-1 h-6 w-6"
              onChange={() => void toggle(card.id, card.status ?? "todo")} />
            <span>
              <span className="flex flex-wrap items-center gap-2">
                <span className="text-[16px] font-semibold leading-[22px]">{card.chosen.title}</span>
                {card.status === "done" && <VerdictChip kind="fixed" />}
              </span>
              <span className="block text-[14px] text-text-2">
                {card.chosen.difficulty} - estimate: {card.chosen.cost_estimate}
              </span>
            </span>
          </label>
          <div className="mt-3 flex gap-2">
            <input
              type="text"
              aria-label={`Note for ${card.chosen.title}`}
              placeholder={card.note ? `Note: ${card.note}` : "Add a note (who, when, cost...)"}
              value={notes[card.id] ?? ""}
              onChange={(e) => setNotes((n) => ({ ...n, [card.id]: e.target.value }))}
              className="min-h-[48px] flex-1 rounded-btn border border-border-strong bg-surface p-3 text-[15px]"
            />
            <Button
              type="button"
              variant="secondary"
              onClick={() => void saveNote(card.id, card.status ?? "todo")}
            >
              Save
            </Button>
          </div>
        </div>
      ))}
    </main>
  );
}
