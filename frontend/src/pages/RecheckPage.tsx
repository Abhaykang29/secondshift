import { useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "../api/client";

interface RecheckItemView {
  item_id: string; room: string; status: string; reason: string;
}
interface RecheckView {
  items: RecheckItemView[];
  score_before: number; score_after: number;
  rule_outcomes: { rule_id: string; outcome: string; reason: string }[];
}

const ICON: Record<string, string> = {
  resolved: "Resolved", still_present: "Still there", new: "New", cannot_tell: "Couldn't tell",
};

/**
 * Re-check page (spec 5.1 step 8): run the fixed-home re-check and show
 * the diff - Resolved / Still there / New / Couldn't tell - plus the
 * home score before and after, and saved rule outcomes.
 */
export default function RecheckPage() {
  const { id = "" } = useParams();
  const [recheck, setRecheck] = useState<RecheckView | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function run() {
    setBusy(true);
    try {
      const result = (await api.recheck(id, "parent_home_fixed")) as unknown as RecheckView;
      setRecheck(result);
    } catch {
      setError("Run a scan first - a re-check needs a report to compare with.");
    }
    setBusy(false);
  }

  return (
    <main className="mx-auto max-w-2xl p-6">
      <h1 className="text-2xl font-semibold">Re-check</h1>
      <p className="mt-2">
        Film the home again the same way. I'll show what was fixed, what's still there,
        and anything new. (Demo: the "fixed home" re-check.)
      </p>
      {error && <p role="alert" className="mt-3 text-red-700">{error}</p>}
      <button type="button" disabled={busy} onClick={() => void run()}
        className="mt-4 w-full rounded bg-blue-700 px-4 py-3 text-white disabled:opacity-40">
        {busy ? "Re-checking..." : "Run the re-check"}
      </button>
      {recheck && (
        <section className="mt-6" aria-label="Re-check results">
          <p className="text-xl">
            Home score: {recheck.score_before} to {recheck.score_after}
          </p>
          <ul className="mt-3">
            {recheck.items.map((item) => (
              <li key={item.item_id} className="mt-2 rounded border p-3">
                <strong>{ICON[item.status] ?? item.status}</strong> - {item.item_id} ({item.room})
                <span className="block text-sm opacity-80">{item.reason}</span>
              </li>
            ))}
          </ul>
          {recheck.rule_outcomes.length > 0 && (
            <>
              <h2 className="mt-5 text-lg font-semibold">Saved rules</h2>
              <ul>
                {recheck.rule_outcomes.map((o) => (
                  <li key={o.rule_id} className="mt-1">
                    {o.outcome.toUpperCase()} - {o.reason}
                  </li>
                ))}
              </ul>
            </>
          )}
        </section>
      )}
    </main>
  );
}
