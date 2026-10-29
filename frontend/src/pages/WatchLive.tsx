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
interface LiveStartResult {
  started: boolean; status?: string; message?: string; session_id?: string; room?: string;
}

export default function WatchLive() {
  const [result, setResult] = useState<DemoResult | null>(null);
  const [live, setLive] = useState<LiveStartResult | null>(null);
  const [liveEvents, setLiveEvents] = useState<EventView[]>([]);
  const [roomClaim, setRoomClaim] = useState("hallway");
  const [consent, setConsent] = useState(false);

  async function startLive() {
    const res = await fetch("/api/watch/live/start", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        rule_text: rule, source_id: "phone-1",
        room_claim: roomClaim, resident_consent: consent,
      }),
    });
    const data = (await res.json()) as LiveStartResult;
    setLive(data);
    if (data.started && data.session_id) {
      const source = new EventSource(`/api/watch/live/${data.session_id}/events`);
      source.onmessage = (msg) => {
        const event = JSON.parse(msg.data as string) as EventView;
        setLiveEvents((prev) => [...prev, event]);
      };
    }
  }

  async function stopLive() {
    if (live?.session_id) {
      await fetch(`/api/watch/live/${live.session_id}/stop`, { method: "POST" });
      setLive({ started: false, status: "stopped", message: "Live watch stopped." });
    }
  }
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
      <section className="mt-6 rounded border p-4" aria-label="Live watch">
        <h2 className="font-semibold">Live watch (real camera)</h2>
        <p className="mt-1 text-sm">
          Uses the phone streaming at /camera. The room is classified from the
          camera and checked against your answer - bathrooms are always
          refused, bedrooms need the resident's consent.
        </p>
        <label className="mt-3 block">What room is the camera in?
          <input value={roomClaim} onChange={(e) => setRoomClaim(e.target.value)}
            className="mt-1 block w-full rounded border p-2" />
        </label>
        <label className="mt-2 flex items-center gap-2 text-sm">
          <input type="checkbox" checked={consent}
            onChange={(e) => setConsent(e.target.checked)} />
          The person who sleeps in this room (if a bedroom) agreed to this watch.
        </label>
        <div className="mt-3 flex gap-2">
          <button type="button" onClick={() => void startLive()}
            className="rounded bg-emerald-700 px-4 py-2 text-white">Start live watch</button>
          <button type="button" onClick={() => void stopLive()}
            className="rounded border px-4 py-2">Stop</button>
        </div>
        {live && (
          <p className="mt-2 text-sm">
            {live.started ? `Watching (room: ${live.room ?? "?"}). ` : ""}{live.message ?? live.status ?? ""}
          </p>
        )}
        {liveEvents.length > 0 && (
          <ol className="mt-2">
            {liveEvents.map((e) => (
              <li key={e.id} className="mt-1 rounded border p-2 text-sm">
                {e.state_from} to {e.state_to} - {e.reason}
              </li>
            ))}
          </ol>
        )}
      </section>
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
