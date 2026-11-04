import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Save } from "lucide-react";
import Button from "../components/ui/Button";
import Card from "../components/ui/Card";

interface SourceView { id: string; label: string; room_type?: string | null; kind: string }

const INPUT_CLS =
  "mt-1 block w-full rounded-btn border border-border-strong bg-surface p-3 text-[15px]";

/**
 * Watch setup (spec 5.2 steps 1-3): pick the spot, draw the ROI (numeric
 * for now - drag ROI is Phase 6.5 polish), classify the room. Bathrooms
 * are refused by the backend room guard; bedrooms need resident consent.
 */
export default function WatchSetup() {
  const [label, setLabel] = useState("Kitchen phone");
  const [room, setRoom] = useState("kitchen");
  const [consent, setConsent] = useState(false);
  const [message, setMessage] = useState("");
  const [sources, setSources] = useState<SourceView[]>([]);

  async function load() {
    const res = await fetch("/api/watch/sources");
    const data = (await res.json()) as { sources: SourceView[] };
    setSources(data.sources);
  }
  useEffect(() => { void load(); }, []);

  async function create() {
    const res = await fetch("/api/watch/sources", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ kind: "phone", label, room_type: room, resident_consent: consent }),
    });
    if (res.ok) {
      setMessage("Source saved. Now write the rule it should watch for.");
      void load();
    } else {
      const data = (await res.json()) as { detail: string };
      setMessage(data.detail);
    }
  }

  return (
    <main className="mx-auto max-w-2xl p-4">
      <h1 className="text-[24px] font-[650] leading-[30px] tracking-[-0.01em]">Watch one spot</h1>
      <p className="mt-2 text-[15px] leading-[22px] text-text-2">
        Watch checks one spot against rules you write. It never records people and
        never runs in a bathroom.
      </p>
      <label className="mt-4 block">Source label
        <input value={label} onChange={(e) => setLabel(e.target.value)}
          className={INPUT_CLS} />
      </label>
      <label className="mt-3 block">Room
        <select value={room} onChange={(e) => setRoom(e.target.value)}
          className={INPUT_CLS}>
          <option value="kitchen">Kitchen</option>
          <option value="nursery">Nursery</option>
          <option value="stairs">Stairs / hallway</option>
          <option value="bedroom">Bedroom (needs resident consent)</option>
          <option value="bathroom">Bathroom (always refused)</option>
        </select>
      </label>
      {room === "bedroom" && (
        <label className="mt-3 flex items-center gap-2 text-[14px]">
          <input type="checkbox" checked={consent} onChange={(e) => setConsent(e.target.checked)}
            className="h-5 w-5 shrink-0" />{" "}
          The resident who sleeps here consents to this watch.
        </label>
      )}
      {message && <p role="status" className="mt-3 text-[14px] text-text-2">{message}</p>}
      <Button type="button" variant="primary" fullWidth icon={Save} className="mt-4"
        onClick={() => void create()}>
        Save this source
      </Button>
      {sources.length > 0 && (
        <Card className="mt-8" title="Saved sources">
          <ul>
            {sources.map((s) => (
              <li key={s.id}
                className="mt-2 rounded-tile border border-border bg-surface px-3 py-2.5 text-[15px] first:mt-0">
                {s.label} - {s.room_type ?? "room not classified"} ({s.kind})
              </li>
            ))}
          </ul>
        </Card>
      )}
      <p className="mt-6 text-[15px]">
        Next: <Link to="/rules" className="text-accent underline">write the rule</Link>, then{" "}
        <Link to="/watch/live" className="text-accent underline">see it run live</Link>.
      </p>
    </main>
  );
}
