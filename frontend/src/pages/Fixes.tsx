import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "../api/client";
import type { Report } from "../api/types";

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

  if (!report) return <main className="p-4"><p>Loading fixes...</p></main>;
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
    <main className="p-4">
      <h1 className="text-2xl font-semibold">Fix tracker</h1>
      <p className="mt-2">{done} of {report.fixes.length} fixes done</p>
      <div className="mt-2 h-3 w-full rounded bg-neutral-200" role="progressbar"
        aria-valuenow={done} aria-valuemax={report.fixes.length}>
        <div className="h-3 rounded bg-green-600"
          style={{ width: `${report.fixes.length ? (done / report.fixes.length) * 100 : 0}%` }} />
      </div>
      {report.fixes.map((card) => (
        <div key={card.id} className="mt-3 rounded border bg-white p-4">
          <label className="flex items-start gap-3">
            <input type="checkbox" checked={card.status === "done"} className="mt-1 h-6 w-6"
              onChange={() => void toggle(card.id, card.status ?? "todo")} />
            <span>
              <span className="font-medium">{card.chosen.title}</span>
              <span className="block text-sm opacity-80">
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
              className="min-h-[48px] flex-1 rounded border p-2"
            />
            <button
              type="button"
              onClick={() => void saveNote(card.id, card.status ?? "todo")}
              className="rounded border px-3"
            >
              Save
            </button>
          </div>
        </div>
      ))}
    </main>
  );
}
