import { useEffect, useRef, useState } from "react";
import en from "../i18n/en.json";

interface EventView {
  id: string; state_from: string; state_to: string; reason: string; at: string;
}
interface DemoResult { events: EventView[]; alerts: number; note?: string }

/**
 * Live Check view: compile a plain-English rule, claim the room, get
 * consent, and run the real live watch against the phone camera
 * stream (events arrive over SSE). A scripted simulation of the same
 * flow exists for development only and renders solely with ?dev=1
 * in the URL - it is never part of the product surface.
 */
interface LiveStartResult {
  started: boolean; status?: string; message?: string; session_id?: string; room?: string;
}

const DEV_MODE =
  typeof window !== "undefined" &&
  new URLSearchParams(window.location.search).has("dev");

export default function WatchLive() {
  const [result, setResult] = useState<DemoResult | null>(null);
  const [live, setLive] = useState<LiveStartResult | null>(null);
  const [liveEvents, setLiveEvents] = useState<EventView[]>([]);
  const [roomClaim, setRoomClaim] = useState("hallway");
  const [consent, setConsent] = useState(false);
  const [checking, setChecking] = useState(false);
  const sourceRef = useRef<EventSource | null>(null);

  useEffect(() => () => sourceRef.current?.close(), []);

  async function startLive() {
    setChecking(true);
    try {
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
        sourceRef.current?.close();
        const source = new EventSource(`/api/watch/live/${data.session_id}/events`);
        sourceRef.current = source;
        source.onmessage = (msg) => {
          const event = JSON.parse(msg.data as string) as EventView;
          setLiveEvents((prev) => [...prev, event]);
        };
      }
    } finally {
      setChecking(false);
    }
  }

  async function stopLive() {
    sourceRef.current?.close();
    sourceRef.current = null;
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

  // Live status chip (spec 4.4): driven by the session state and the
  // latest event from the watch loop's state machine.
  const lastState = liveEvents[liveEvents.length - 1]?.state_to;
  const chip: { text: string; cls: string } | null = checking
    ? { text: "Checking…", cls: "bg-blue-100 text-blue-900" }
    : lastState === "alert"
      ? { text: "ALERT", cls: "bg-red-700 text-white" }
      : lastState === "cannot_see"
        ? { text: "Can't see", cls: "bg-neutral-300 text-neutral-900" }
        : lastState === "pending"
          ? { text: "Pending", cls: "bg-amber-200 text-amber-900" }
          : live?.started
            ? { text: "Watching", cls: "bg-green-700 text-white" }
            : live && live.status === "no_frames"
              ? { text: "Can't see", cls: "bg-neutral-300 text-neutral-900" }
              : null;
  const banner = en.watch_banner.replace(
    "<spot>",
    live?.room ?? roomClaim ?? "one spot",
  );

  return (
    <div className="p-4">
      <h1 className="text-2xl font-semibold">Live Check</h1>
      {DEV_MODE && (
        <div className="relative mt-4 aspect-video w-full rounded bg-neutral-700">
          <span className="absolute left-2 top-2 text-sm text-white">
            Simulation — not a camera. Scripted timeline for trying rules without a camera.
          </span>
          <span className="absolute bottom-2 right-2 rounded bg-black/60 px-2 py-1 text-sm text-white">
            State: {result?.events[result.events.length - 1]?.state_to ?? "idle"}
          </span>
        </div>
      )}
      <label className="mt-4 block">Rule
        <textarea value={rule} onChange={(e) => setRule(e.target.value)} rows={2}
          className="mt-1 block w-full rounded border p-3" />
      </label>
      {DEV_MODE && (
        <button type="button" onClick={() => void run()}
          className="mt-3 w-full rounded bg-blue-700 px-4 py-3 text-white">
          Run the simulated watch (dev)
        </button>
      )}
      <section className="mt-6 rounded border bg-white p-4" aria-label="Live watch">
        <div className="flex items-center justify-between gap-2">
          <h2 className="font-semibold">Live watch (real camera)</h2>
          {chip && (
            <span className={`rounded-full px-3 py-1 text-sm font-semibold ${chip.cls}`}>
              {chip.text}
            </span>
          )}
        </div>
        <p
          className={`mt-3 rounded p-3 text-sm font-medium ${
            live?.started ? "bg-[#1f3d2b] text-white" : "bg-neutral-100"
          }`}
          role="status"
        >
          {banner}
        </p>
        <p className="mt-2 text-sm">
          Uses the phone streaming at /camera. The room is classified from the
          camera and checked against your answer - bathrooms are always
          refused, bedrooms need the resident's consent.
          {checking ? " Checking with the model now..." : ""}
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
      {DEV_MODE && result && (
        <section className="mt-5" aria-label="Simulated watch events">
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
    </div>
  );
}
