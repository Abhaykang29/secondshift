import { useCallback, useEffect, useState } from "react";
import { plural } from "../plural";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import type { HomeSummary } from "../api/extra";

/**
 * Homes tab (Pass 3 spec 4.5): every place that has been checked,
 * with its last check, open fixes, and re-check due date. Deleting a
 * place deletes all of its data (checkups, reports, captures) via
 * DELETE /api/homes/{label} - behind a two-tap confirm.
 */
export default function HomesPage() {
  const [homes, setHomes] = useState<HomeSummary[] | null>(null);
  const [error, setError] = useState("");
  const [confirming, setConfirming] = useState<string | null>(null);

  const load = useCallback(() => {
    api
      .homes()
      .then((r) => setHomes(r.homes))
      .catch(() => setError("Could not load your places. Is the backend running?"));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function remove(label: string) {
    try {
      await api.deleteHome(label);
      setConfirming(null);
      load();
    } catch {
      setError(`Could not delete ${label}.`);
    }
  }

  const fmtDate = (iso: string) =>
    iso ? new Date(iso).toLocaleDateString() : "—";

  return (
    <main className="p-4">
      <h1 className="text-2xl font-semibold">Your places</h1>
      {error && <p role="alert" className="mt-3 text-red-700">{error}</p>}
      {homes === null && !error && <p className="mt-3">Loading places...</p>}
      {homes !== null && homes.length === 0 && (
        <p className="mt-3 opacity-80">
          No places yet. Run your first check from the Check tab — the
          place you name will show up here with its report, open fixes
          and re-check date.
        </p>
      )}
      <div className="mt-4 grid gap-3">
        {(homes ?? []).map((home) => (
          <article key={home.label} className="rounded border bg-white p-4">
            <h2 className="text-lg font-semibold">{home.label}</h2>
            <ul className="mt-1 text-sm opacity-85">
              <li>Last check: {fmtDate(home.last_check_at)}</li>
              <li>{plural(home.open_findings, "open finding")}</li>
              <li>{plural(home.open_fixes, "open fix", "open fixes")}</li>
              <li>Re-check due: {fmtDate(home.recheck_due)}</li>
            </ul>
            <div className="mt-3 flex flex-wrap gap-2">
              <Link
                to={`/checkup/${home.last_checkup_id}/report`}
                className="rounded bg-[#1f3d2b] px-3 py-2 text-white"
              >
                Latest report
              </Link>
              <Link
                to={`/checkup/${home.last_checkup_id}/fixes`}
                className="rounded border px-3 py-2"
              >
                Fix tracker
              </Link>
              <Link
                to={`/checkup/${home.last_checkup_id}/recheck`}
                className="rounded border px-3 py-2"
              >
                Re-check
              </Link>
            </div>
            {confirming === home.label ? (
              <div className="mt-3 rounded bg-red-50 p-3">
                <p className="text-sm font-medium">
                  Delete {home.label} and ALL of its data — checks,
                  reports and videos? This cannot be undone.
                </p>
                <div className="mt-2 flex gap-2">
                  <button
                    type="button"
                    onClick={() => void remove(home.label)}
                    className="rounded bg-red-700 px-3 py-2 text-white"
                  >
                    Yes, delete everything
                  </button>
                  <button
                    type="button"
                    onClick={() => setConfirming(null)}
                    className="rounded border bg-white px-3 py-2"
                  >
                    Keep it
                  </button>
                </div>
              </div>
            ) : (
              <button
                type="button"
                onClick={() => setConfirming(home.label)}
                className="mt-3 rounded border border-red-700 px-3 py-2 text-red-700"
              >
                Delete this place
              </button>
            )}
          </article>
        ))}
      </div>
    </main>
  );
}
