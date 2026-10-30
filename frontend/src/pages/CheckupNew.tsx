import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api/client";
import en from "../i18n/en.json";

/**
 * Check flow (Pass 3 spec 4.3 steps 2-3): one short consent screen,
 * then the capture guide with three ways to get footage - record in
 * the app camera, import from Photos (incl. Ray-Ban Meta clips), and
 * Consent is recorded by
 * POST /checkups before any capture exists (unchanged API usage);
 * uploads post to /checkups/{id}/captures with kind walkthrough /
 * routine. After an upload the flow hands off to the processing page.
 */
const GUIDE = [
  { icon: "🐢", title: "Walk slowly", text: "Room by room: entry, living, kitchen, hallway, bedroom, stairs." },
  { icon: "📱", title: "Hold landscape", text: "Turn the phone sideways, lights on, keep it steady." },
  { icon: "🧱", title: "Show floors and walls", text: "Include floors, stair edges, outlets and where cords run." },
  { icon: "⏸️", title: "Pause and narrate", text: "Pause on each hazard and say what it is out loud." },
];

export default function CheckupNew() {
  const navigate = useNavigate();
  const [packIds] = useState<string[]>(() => {
    try {
      const stored = JSON.parse(
        sessionStorage.getItem("pack_selection") ?? "[]",
      ) as string[];
      return stored.length > 0 ? stored.slice(0, 3) : ["falls_older_adults"];
    } catch {
      return ["falls_older_adults"];
    }
  });
  const [step, setStep] = useState<"consent" | "capture">("consent");
  const [checkupId, setCheckupId] = useState("");
  const [label, setLabel] = useState("");
  const [informed, setInformed] = useState(false);
  const [noPrivate, setNoPrivate] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [walkthrough, setWalkthrough] = useState<{ id: string; frames: number } | null>(null);
  const [uploading, setUploading] = useState<"walkthrough" | "routine" | null>(null);

  async function agree() {
    setBusy(true);
    setError("");
    try {
      const checkup = await api.createCheckup({
        pack_ids: packIds,
        resident_label: label || null,
        consent: { resident_informed: informed, no_private_moments: noPrivate },
      });
      setCheckupId(checkup.id);
      setStep("capture");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong");
    }
    setBusy(false);
  }

  async function upload(kind: "walkthrough" | "routine", file: File | undefined) {
    if (!file || !checkupId) return;
    setUploading(kind);
    setError("");
    try {
      const capture = await api.uploadCapture(checkupId, file, kind);
      if (kind === "walkthrough") {
        setWalkthrough({ id: capture.id, frames: capture.keyframe_count });
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Upload failed");
    }
    setUploading(null);
  }

  if (step === "consent") {
    return (
      <main className="p-4">
        <h1 className="text-2xl font-semibold">Before you film</h1>
        <p className="mt-3">{en.consent_intro}</p>

        <fieldset className="mt-5">
          <legend className="font-medium">Checklists for this walkthrough</legend>
          <p className="mt-1 opacity-80">
            {packIds.join(", ")} — chosen on the Check tab (up to 3). One
            walkthrough is checked against all of them.
          </p>
        </fieldset>

        <label className="mt-5 block">
          Name this place
          <input
            value={label}
            onChange={(e) => setLabel(e.target.value)}
            className="mt-1 block w-full rounded border bg-white p-3"
            placeholder="Mom's home"
          />
        </label>

        <label className="mt-5 flex items-start gap-3">
          <input
            type="checkbox"
            className="mt-1 h-6 w-6 shrink-0"
            checked={informed}
            onChange={(e) => setInformed(e.target.checked)}
          />
          <span>The person who lives or works here knows and agrees to this check.</span>
        </label>
        <label className="mt-3 flex items-start gap-3">
          <input
            type="checkbox"
            className="mt-1 h-6 w-6 shrink-0"
            checked={noPrivate}
            onChange={(e) => setNoPrivate(e.target.checked)}
          />
          <span>No one is filmed in a bathroom or while undressed.</span>
        </label>

        <p className="mt-5 rounded bg-white p-3 text-sm">{en.data_note}</p>

        {error && <p role="alert" className="mt-3 text-red-700">{error}</p>}
        <button
          type="button"
          disabled={!informed || !noPrivate || busy}
          onClick={() => void agree()}
          className="mt-6 w-full rounded bg-[#1f3d2b] px-4 py-3 text-white disabled:opacity-40"
        >
          {busy ? "Saving..." : "Agree and continue"}
        </button>
      </main>
    );
  }

  return (
    <main className="p-4">
      <h1 className="text-2xl font-semibold">Film the walkthrough</h1>

      <section aria-label="How to film" className="mt-4 grid grid-cols-2 gap-3">
        {GUIDE.map((panel) => (
          <div key={panel.title} className="rounded border bg-white p-3">
            <span className="text-3xl" aria-hidden>{panel.icon}</span>
            <h2 className="mt-1 font-medium">{panel.title}</h2>
            <p className="text-sm opacity-80">{panel.text}</p>
          </div>
        ))}
      </section>

      <section aria-label="Record now" className="mt-5 rounded border bg-white p-4">
        <h2 className="font-medium">Record now</h2>
        <p className="mt-1 text-sm opacity-80">
          Use this phone&rsquo;s camera in the app, up to 3 minutes.
        </p>
        <Link
          to={`/camera?checkup=${checkupId}`}
          className="mt-3 flex w-full items-center justify-center rounded bg-[#1f3d2b] px-4 py-3 text-white"
        >
          Open the camera
        </Link>
      </section>

      <section aria-label="Import from Photos" className="mt-4 rounded border bg-white p-4">
        <h2 className="font-medium">Import from Photos</h2>
        <p className="mt-1 text-sm opacity-80">
          Ray-Ban Meta: say &ldquo;Hey Meta, take a video&rdquo;, then import
          the clip from your Photos here.
        </p>
        <label className="mt-3 block">
          <span className="sr-only">Choose a walkthrough video</span>
          <input
            type="file"
            accept="video/*"
            className="block w-full rounded border p-3"
            onChange={(e) => void upload("walkthrough", e.target.files?.[0])}
          />
        </label>
        {uploading === "walkthrough" && <p className="mt-2 text-sm">Uploading and reading frames...</p>}
        {walkthrough && (
          <p className="mt-2 text-sm font-medium text-[#1f3d2b]">
            Video in — {walkthrough.frames} frames found.
          </p>
        )}
      </section>

      {error && <p role="alert" className="mt-3 text-red-700">{error}</p>}

      <button
        type="button"
        disabled={!walkthrough}
        onClick={() =>
          navigate(`/checkup/${checkupId}/processing?capture=${walkthrough?.id ?? ""}`)
        }
        className="mt-6 w-full rounded bg-[#1f3d2b] px-4 py-3 text-white disabled:opacity-40"
      >
        Start the check
      </button>
      <button
        type="button"
        onClick={() => navigate(`/checkup/${checkupId}/processing`)}
        className="mt-3 w-full rounded border bg-white px-4 py-3"
      >
        No video handy? Run the demo home check
      </button>
      <p className="mt-2 text-sm opacity-70">
        The demo home is a recorded scenario so the full flow works before
        real footage exists.
      </p>
    </main>
  );
}
