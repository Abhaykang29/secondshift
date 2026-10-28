import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

interface SourceView { id: string; label: string; room_type?: string | null; kind: string }

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
    <main className="mx-auto max-w-2xl p-6">
      <h1 className="text-2xl font-semibold">Watch one spot</h1>
      <p className="mt-2">
        Watch checks one spot against rules you write. It never records people and
        never runs in a bathroom.
      </p>
      <label className="mt-4 block">Source label
        <input value={label} onChange={(e) => setLabel(e.target.value)}
          className="mt-1 block w-full rounded border p-3" />
      </label>
      <label className="mt-3 block">Room
        <select value={room} onChange={(e) => setRoom(e.target.value)}
          className="mt-1 block w-full rounded border p-3">
          <option value="kitchen">Kitchen</option>
          <option value="nursery">Nursery</option>
          <option value="stairs">Stairs / hallway</option>
          <option value="bedroom">Bedroom (needs resident consent)</option>
          <option value="bathroom">Bathroom (always refused)</option>
        </select>
      </label>
      {room === "bedroom" && (
        <label className="mt-3 block">
          <input type="checkbox" checked={consent} onChange={(e) => setConsent(e.target.checked)} />{" "}
          The resident who sleeps here consents to this watch.
        </label>
      )}
      {message && <p role="status" className="mt-3">{message}</p>}
      <button type="button" onClick={() => void create()}
        className="mt-4 w-full rounded bg-blue-700 px-4 py-3 text-white">
        Save this source
      </button>
      {sources.length > 0 && (
        <section className="mt-6" aria-label="Saved sources">
          <h2 className="text-lg font-semibold">Saved sources</h2>
          <ul className="mt-2">
            {sources.map((s) => (
              <li key={s.id} className="mt-1">{s.label} - {s.room_type ?? "room not classified"} ({s.kind})</li>
            ))}
          </ul>
        </section>
      )}
      <p className="mt-6">
        Next: <Link to="/rules" className="underline">write the rule</Link>, then{" "}
        <Link to="/watch/live" className="underline">see it run live</Link>.
      </p>
    </main>
  );
}
