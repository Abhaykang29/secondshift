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

  useEffect(() => {
    api.report(id).then(setReport).catch(() => setReport(null));
  }, [id]);

  if (!report) return <main className="mx-auto max-w-2xl p-6"><p>Loading fixes...</p></main>;
  const done = report.fixes.filter((f) => f.status === "done").length;

  async function toggle(fixId: string, status: string) {
    const updated = await api.updateFix(id, fixId, status === "done" ? "todo" : "done");
    setReport((r) => (r ? { ...r, fixes: r.fixes.map((f) => (f.id === fixId ? updated : f)) } : r));
  }

  return (
    <main className="mx-auto max-w-2xl p-6">
      <h1 className="text-2xl font-semibold">Fix tracker</h1>
      <p className="mt-2">{done} of {report.fixes.length} fixes done</p>
      <div className="mt-2 h-3 w-full rounded bg-neutral-200" role="progressbar"
        aria-valuenow={done} aria-valuemax={report.fixes.length}>
        <div className="h-3 rounded bg-green-600"
          style={{ width: `${report.fixes.length ? (done / report.fixes.length) * 100 : 0}%` }} />
      </div>
      {report.fixes.map((card) => (
        <label key={card.id} className="mt-3 flex items-start gap-3 rounded border p-4">
          <input type="checkbox" checked={card.status === "done"} className="mt-1 h-6 w-6"
            onChange={() => void toggle(card.id, card.status ?? "todo")} />
          <span>
            <span className="font-medium">{card.chosen.title}</span>
            <span className="block text-sm opacity-80">
              {card.chosen.difficulty} - estimate: {card.chosen.cost_estimate}
              {card.note ? ` - ${card.note}` : ""}
            </span>
          </span>
        </label>
      ))}
    </main>
  );
}
