import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";
import en from "../i18n/en.json";

/**
 * Consent & setup (spec 5.1 steps 1-4): pack choice, resident label,
 * consent checkboxes, capture guidance, then the demo scan. Real video
 * upload posts to /captures; "Use the demo home" runs the mock scenario
 * so the full flow works before real footage exists (TODO(TEAM): footage).
 */
export default function CheckupNew() {
  const navigate = useNavigate();
  const [pack, setPack] = useState("falls_older_adults");
  const [label, setLabel] = useState("");
  const [informed, setInformed] = useState(false);
  const [noPrivate, setNoPrivate] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function start() {
    setBusy(true);
    setError("");
    try {
      const checkup = await api.createCheckup({
        pack_ids: [pack],
        resident_label: label || null,
        consent: { resident_informed: informed, no_private_moments: noPrivate },
      });
      await api.scan(checkup.id);
      navigate(`/checkup/${checkup.id}/report`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong");
      setBusy(false);
    }
  }

  return (
    <main className="mx-auto max-w-2xl p-6">
      <h1 className="text-2xl font-semibold">Check a home</h1>
      <p className="mt-3">{en.consent_intro}</p>

      <fieldset className="mt-5">
        <legend className="font-medium">Whose home?</legend>
        <label className="mt-2 block">
          <input type="radio" name="pack" checked={pack === "falls_older_adults"}
            onChange={() => setPack("falls_older_adults")} /> Parent's home (falls)
        </label>
        <label className="mt-1 block">
          <input type="radio" name="pack" checked={pack === "babyproofing"}
            onChange={() => setPack("babyproofing")} /> Baby's home (babyproofing)
        </label>
      </fieldset>

      <label className="mt-5 block">
        First name (optional)
        <input value={label} onChange={(e) => setLabel(e.target.value)}
          className="mt-1 block w-full rounded border p-3" placeholder="Mom" />
      </label>

      <label className="mt-5 block">
        <input type="checkbox" checked={informed} onChange={(e) => setInformed(e.target.checked)} />{" "}
        The person who lives here knows and agrees to this check-up.
      </label>
      <label className="mt-2 block">
        <input type="checkbox" checked={noPrivate} onChange={(e) => setNoPrivate(e.target.checked)} />{" "}
        I will not film anyone in a bathroom or while undressing.
      </label>

      <section className="mt-5 rounded bg-neutral-100 p-4">
        <h2 className="font-medium">How to film (2-3 minutes)</h2>
        <ol className="mt-2 list-decimal pl-6">
          <li>Room order: entry, living, kitchen, hallway, bedroom, bathroom, stairs.</li>
          <li>Lights on, slow pan, include floors and stair edges.</li>
          <li>Narrate as you go - tell us anything we should know.</li>
          <li>Optional routine clip: prop the phone still and film the daily path once.</li>
        </ol>
        <p className="mt-2 text-sm">{en.data_note}</p>
      </section>

      {error && <p role="alert" className="mt-3 text-red-700">{error}</p>}
      <button type="button" disabled={!informed || !noPrivate || busy} onClick={start}
        className="mt-6 w-full rounded bg-blue-700 px-4 py-3 text-white disabled:opacity-40">
        {busy ? "Checking the home..." : "Use the demo home and run the check-up"}
      </button>
      <p className="mt-2 text-sm opacity-70">
        Demo home = recorded mock scenario. Real footage upload: TODO(TEAM) footage + Phase 7 keys.
      </p>
    </main>
  );
}
