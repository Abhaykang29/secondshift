import { useState } from "react";

interface EventView {
  id: string; state_from: string; state_to: string; reason: string; at: string;
}
interface DemoResult { events: EventView[]; alerts: number; note?: string }

/**
 * Watch live view (spec 5.2 step 5): run the demo timeline (gate opens
 * for 60 seconds) through the real engine and show the state timeline -
 * exactly one alert. The still-frame strip is a placeholder panel: live
 * frames need a real source (TODO(TEAM) phone setup).
 */
export default function WatchLive() {
  const [result, setResult] = useState<DemoResult | null>(null);
  const [rule, setRule] = useState(
    "Tell me if the baby gate at the top of the stairs is left open for more than 30 seconds.",
  );

  async function run() {
    const res = await fetch("/api/watch/simulate", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ rule_text: rule, mode_hint: "watch" }),
    });
    setResult((await res.json()) as DemoResult);
  }

  return (
    <main className="mx-auto max-w-2xl p-6">
      <h1 className="text-2xl font-semibold">Watch — simulation</h1>
      <div className="relative mt-4 aspect-video w-full rounded bg-neutral-700">
        <span className="absolute left-2 top-2 text-sm text-white">
          Simulation — not a camera. Scripted timeline (gate opens 10s–70s). For a real camera, open /camera on a phone (live loop: pass 2 Phase G).
        </span>
        <span className="absolute bottom-2 right-2 rounded bg-black/60 px-2 py-1 text-sm text-white">
          State: {result?.events[result.events.length - 1]?.state_to ?? "idle"}
        </span>
      </div>
      <label className="mt-4 block">Rule
        <textarea value={rule} onChange={(e) => setRule(e.target.value)} rows={2}
          className="mt-1 block w-full rounded border p-3" />
      </label>
      <button type="button" onClick={() => void run()}
        className="mt-3 w-full rounded bg-blue-700 px-4 py-3 text-white">
        Run the demo watch
      </button>
      {result && (
        <section className="mt-5" aria-label="Watch events">
          <p className="font-medium">Alerts sent: {result.alerts}</p>
          {result.note && <p className="mt-1">{result.note}</p>}
          <ol className="mt-2">
            {result.events.map((e) => (
              <li key={e.id} className="mt-1 rounded border p-2 text-sm">
                {e.state_from} to {e.state_to} - {e.reason}
              </li>
            ))}
          </ol>
        </section>
      )}
    </main>
  );
}
