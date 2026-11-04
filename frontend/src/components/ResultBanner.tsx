import { useEffect, useState } from "react";

/**
 * Provenance banner for a report (judge fix, 2026-11-04): recorded
 * real results are labeled as recorded replays and never show the
 * mock banner; mock-generated reports carry the MOCK banner; a live
 * scan shows nothing.
 */
export default function ResultBanner({ recorded }: { recorded?: string | null }) {
  const [mode, setMode] = useState<string>("");

  useEffect(() => {
    if (recorded) return;
    fetch("/api/settings")
      .then((r) => r.json())
      .then((d: { provider_mode?: string }) => setMode(d.provider_mode ?? ""))
      .catch(() => setMode(""));
  }, [recorded]);

  if (recorded) {
    const when = new Date(`${recorded}T12:00:00`).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
    return (
      <div className="mb-3 rounded bg-emerald-700 px-4 py-2 text-center font-semibold text-white">
        Recorded real result (Meta models, {when}) — replayed, no key needed
      </div>
    );
  }
  if (mode !== "mock") return null;
  return (
    <div role="alert" className="mb-3 rounded bg-red-700 px-4 py-2 text-center font-semibold text-white">
      MOCK MODE — not real results
    </div>
  );
}
