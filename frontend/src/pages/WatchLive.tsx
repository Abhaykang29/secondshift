import { useEffect, useRef, useState } from "react";
import { Radio, Square, Video } from "lucide-react";
import en from "../i18n/en.json";
import Banner from "../components/ui/Banner";
import Button from "../components/ui/Button";
import Card from "../components/ui/Card";
import Chip from "../components/ui/Chip";
import VerdictChip from "../components/ui/VerdictChip";

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

function timeLabel(at: string): string {
  const d = new Date(at);
  return Number.isNaN(d.getTime()) ? at : d.toLocaleTimeString("en-GB");
}

/** One event-log row: mono timestamp, verdict chip, one-line reason. */
function EventRow({ e }: { e: EventView }) {
  return (
    <li className="flex items-start gap-3 py-2.5">
      <span className="w-[76px] shrink-0 pt-0.5 font-mono text-[12.5px] tabular-nums text-text-3">
        {timeLabel(e.at)}
      </span>
      {e.state_to === "alert" || e.state_to === "not_met" ? (
        <VerdictChip kind="live_alert" />
      ) : e.state_to === "cannot_see" || e.state_to === "cannot_tell" ? (
        <VerdictChip kind="live_cant" />
      ) : e.state_to === "ok" || e.state_to === "met" ? (
        <VerdictChip kind="live_ok" />
      ) : (
        <Chip>{e.state_to}</Chip>
      )}
      <span className="min-w-0 text-[14px] leading-[20px]">{e.reason}</span>
    </li>
  );
}

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
    ? { text: "Checking…", cls: "bg-accent-bg text-accent" }
    : lastState === "alert"
      ? { text: "ALERT", cls: "bg-bad-bg text-bad" }
      : lastState === "cannot_see"
        ? { text: "Can't see", cls: "bg-unk-bg text-unk border border-dashed border-border-strong" }
        : lastState === "pending"
          ? { text: "Pending", cls: "bg-warn-bg text-warn" }
          : live?.started
            ? { text: "Watching", cls: "bg-ok-bg text-ok" }
            : live && live.status === "no_frames"
              ? { text: "Can't see", cls: "bg-unk-bg text-unk border border-dashed border-border-strong" }
              : null;
  const banner = en.watch_banner.replace(
    "<spot>",
    live?.room ?? roomClaim ?? "one spot",
  );

  return (
    <div className="p-4">
      <h1 className="text-[24px] font-[650] leading-[30px] tracking-[-0.01em]">Live Check</h1>
      {DEV_MODE && (
        <>
          <div className="mt-4">
            <Banner kind="mock">
              Simulation — not a camera. Scripted timeline for trying rules without a camera.
            </Banner>
          </div>
          <div className="relative mt-3 aspect-video w-full overflow-hidden rounded-card bg-surface-3">
            <span
              className="absolute bottom-2 right-2 rounded-chip px-2 py-1 font-mono text-[12px] tabular-nums text-white"
              style={{ backgroundColor: "var(--overlay)" }}
            >
              State: {result?.events[result.events.length - 1]?.state_to ?? "idle"}
            </span>
          </div>
        </>
      )}
      <label className="mt-4 block">Rule
        <textarea value={rule} onChange={(e) => setRule(e.target.value)} rows={2}
          className="mt-1 block w-full rounded-btn border border-border-strong bg-surface p-3 text-[15px]" />
      </label>
      {DEV_MODE && (
        <Button type="button" variant="primary" fullWidth className="mt-3" onClick={() => void run()}>
          Run the simulated watch (dev)
        </Button>
      )}
      <Card
        className="mt-6"
        title="Live watch (real camera)"
        action={
          <div className="flex items-center gap-2">
            {live?.started && (
              <span className="inline-flex items-center gap-1.5 rounded-chip bg-bad px-2.5 py-1 font-mono text-[12px] font-semibold text-white">
                <Radio size={14} strokeWidth={1.75} aria-hidden />
                LIVE
                <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-white" aria-hidden />
              </span>
            )}
            {chip && (
              <span
                className={`inline-flex h-6 items-center rounded-chip px-2.5 text-[12px] font-semibold ${chip.cls}`}
              >
                {chip.text}
              </span>
            )}
          </div>
        }
      >
        <p
          className={`rounded-card p-3 text-[14px] font-medium ${
            live?.started ? "bg-accent-bg text-accent" : "bg-surface-2 text-text-2"
          }`}
          role="status"
        >
          {banner}
        </p>
        <p className="mt-2 text-[14px] leading-[20px] text-text-2">
          Uses the phone streaming at /camera. The room is classified from the
          camera and checked against your answer - bathrooms are always
          refused, bedrooms need the resident's consent.
          {checking ? " Checking with the model now..." : ""}
        </p>
        <label className="mt-3 block">What room is the camera in?
          <input value={roomClaim} onChange={(e) => setRoomClaim(e.target.value)}
            className="mt-1 block w-full rounded-btn border border-border-strong bg-surface p-3 text-[15px]" />
        </label>
        <label className="mt-2 flex items-center gap-2 text-[14px]">
          <input type="checkbox" checked={consent}
            onChange={(e) => setConsent(e.target.checked)}
            className="h-5 w-5 shrink-0" />
          The person who sleeps in this room (if a bedroom) agreed to this watch.
        </label>
        <div className="mt-3 flex gap-2">
          <Button type="button" variant="primary" icon={Video} onClick={() => void startLive()}>
            Start live watch
          </Button>
          <Button type="button" variant="secondary" icon={Square} onClick={() => void stopLive()}>
            Stop
          </Button>
        </div>
        {live && (
          <p className="mt-2 text-[14px] text-text-2">
            {live.started ? `Watching (room: ${live.room ?? "?"}). ` : ""}{live.message ?? live.status ?? ""}
          </p>
        )}
        {liveEvents.length > 0 && (
          <ol className="mt-2 divide-y divide-border border-t border-border">
            {liveEvents.map((e) => (
              <EventRow key={e.id} e={e} />
            ))}
          </ol>
        )}
      </Card>
      {DEV_MODE && result && (
        <section className="mt-5" aria-label="Simulated watch events">
          <p className="font-medium">
            Alerts sent: <span className="font-mono tabular-nums">{result.alerts}</span>
          </p>
          {result.note && <p className="mt-1 text-[14px] text-text-2">{result.note}</p>}
          <ol className="mt-2 divide-y divide-border">
            {result.events.map((e) => (
              <EventRow key={e.id} e={e} />
            ))}
          </ol>
        </section>
      )}
    </div>
  );
}
