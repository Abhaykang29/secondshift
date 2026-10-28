import { useEffect, useState } from "react";

interface SettingsView {
  provider: string; cache_mode: string; budget_usd: number; verify_mode: string;
  languages: { code: string; label: string }[]; translation_status: string;
}

/**
 * Settings (spec 5.3): language (large-text respected from Home),
 * retention display, and the privacy controls - pause/watch-off live on
 * the watch pages; here: Delete everything, wired to the backend.
 */
export default function SettingsPage() {
  const [settings, setSettings] = useState<SettingsView | null>(null);
  const [message, setMessage] = useState("");

  useEffect(() => {
    fetch("/api/settings").then((r) => r.json()).then((d) => setSettings(d as SettingsView))
      .catch(() => setSettings(null));
  }, []);

  async function deleteAll() {
    if (!window.confirm("Delete ALL SecondShift data on this device? This cannot be undone.")) return;
    const res = await fetch("/api/settings/data", { method: "DELETE" });
    setMessage(res.ok ? "Everything was deleted." : "Delete failed.");
  }

  return (
    <main className="mx-auto max-w-2xl p-6">
      <h1 className="text-2xl font-semibold">Settings</h1>
      {settings && (
        <dl className="mt-4">
          <dt className="font-medium">Provider</dt><dd>{settings.provider} (cache: {settings.cache_mode})</dd>
          <dt className="mt-2 font-medium">Verify mode</dt><dd>{settings.verify_mode}</dd>
          <dt className="mt-2 font-medium">Run budget</dt><dd>${settings.budget_usd}</dd>
          <dt className="mt-2 font-medium">Video retention</dt><dd>30 days by default (set at consent)</dd>
          <dt className="mt-2 font-medium">Languages</dt>
          <dd>{settings.languages.map((l) => l.label).join("; ")}</dd>
          <dd className="text-sm opacity-80">{settings.translation_status}</dd>
        </dl>
      )}
      <section className="mt-8 rounded border border-red-400 p-4" aria-label="Privacy controls">
        <h2 className="font-semibold">Privacy</h2>
        <p className="mt-1">Raw video is never kept unless you ask. Deleting is one tap and total.</p>
        {message && <p role="status" className="mt-2">{message}</p>}
        <button type="button" onClick={() => void deleteAll()}
          className="mt-3 rounded bg-red-700 px-4 py-3 text-white">
          Delete everything
        </button>
      </section>
    </main>
  );
}
