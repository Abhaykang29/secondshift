import { useEffect, useState } from "react";
import Button from "../components/ui/Button";
import Card from "../components/ui/Card";

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

  const rowDt = "mt-3 border-t border-border pt-3 font-medium first:mt-0 first:border-0 first:pt-0";

  return (
    <main className="mx-auto max-w-2xl p-6">
      <h1 className="text-[24px] font-[650] leading-[30px] tracking-[-0.01em]">Settings</h1>
      {settings && (
        <Card className="mt-4">
          <dl>
            <dt className={rowDt}>Provider</dt><dd>{settings.provider} (cache: {settings.cache_mode})</dd>
            <dt className={rowDt}>Verify mode</dt><dd>{settings.verify_mode}</dd>
            <dt className={rowDt}>Run budget</dt><dd className="font-mono tabular-nums">${settings.budget_usd}</dd>
            <dt className={rowDt}>Video retention</dt><dd>30 days by default (set at consent)</dd>
            <dt className={rowDt}>Languages</dt>
            <dd>{settings.languages.map((l) => l.label).join("; ")}</dd>
            <dd className="text-[14px] text-text-2">{settings.translation_status}</dd>
          </dl>
        </Card>
      )}
      <section className="mt-8 rounded-card border border-border bg-surface p-4" aria-label="Privacy controls">
        <h2 className="text-[17px] font-semibold">Privacy</h2>
        <p className="mt-1">Raw video is never kept unless you ask. Deleting is one tap and total.</p>
        {message && <p role="status" className="mt-2">{message}</p>}
        <Button type="button" variant="danger" className="mt-3" onClick={() => void deleteAll()}>
          Delete everything
        </Button>
      </section>
    </main>
  );
}
