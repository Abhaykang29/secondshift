import { useCallback, useEffect, useState } from "react";
import { House } from "lucide-react";
import { plural } from "../plural";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";
import type { HomeSummary } from "../api/extra";
import type { Report } from "../api/types";
import Button from "../components/ui/Button";
import Card from "../components/ui/Card";
import Chip from "../components/ui/Chip";
import EmptyState from "../components/ui/EmptyState";
import OverflowMenu from "../components/ui/OverflowMenu";
import { PackIcon } from "../components/ui/PackIcon";
import TallyBar from "../components/ui/TallyBar";

/**
 * Homes tab (Pass 3 spec 4.5, redesign spec 5.1): every place that
 * has been checked, one Card per place with its last check, tally of
 * the latest report, and re-check due date. Deleting a place deletes
 * all of its data (checkups, reports, captures) via
 * DELETE /api/homes/{label} - started from the overflow menu, behind
 * the existing confirm panel.
 */
export default function HomesPage() {
  const navigate = useNavigate();
  const [homes, setHomes] = useState<HomeSummary[] | null>(null);
  const [reports, setReports] = useState<Record<string, Report | null>>({});
  const [error, setError] = useState("");
  const [confirming, setConfirming] = useState<string | null>(null);

  const load = useCallback(() => {
    api
      .homes()
      .then((r) => {
        setHomes(r.homes);
        r.homes.forEach((home) => {
          api
            .report(home.last_checkup_id)
            .then((rep) =>
              setReports((prev) => ({ ...prev, [home.label]: rep })),
            )
            .catch(() =>
              setReports((prev) => ({ ...prev, [home.label]: null })),
            );
        });
      })
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
      <h1 className="text-[24px] font-[650] leading-[30px] tracking-[-0.01em]">
        Your places
      </h1>
      {error && (
        <p role="alert" className="mt-3 text-bad">
          {error}
        </p>
      )}
      {homes === null && !error && (
        <p className="mt-3 text-text-2">Loading places...</p>
      )}
      {homes !== null && homes.length === 0 && (
        <div className="mt-4">
          <EmptyState
            icon={House}
            title="No places yet"
            line="Film a walkthrough to start."
            actionLabel="Start a check"
            onAction={() => navigate("/")}
          />
        </div>
      )}
      <div className="mt-4 grid gap-3">
        {(homes ?? []).map((home) => {
          const report = reports[home.label] ?? null;
          const counts = report
            ? {
                bad: report.hazards.filter((h) => h.verification === "confirmed").length,
                warn: report.hazards.filter((h) => h.verification === "needs_human").length,
                unk: report.cannot_assess.length,
                ok: report.hazards.filter((h) => h.verification === "rejected").length,
              }
            : null;
          const title = home.label.replace(/\s*\(recorded\)\s*$/i, "");
          return (
            <Card key={home.label}>
              <div className="flex items-start gap-3">
                <PackIcon packId={home.pack_ids[0] ?? "custom"} />
                <div className="min-w-0 flex-1">
                  <h2 className="text-[16px] font-semibold leading-[22px]">
                    {title}
                  </h2>
                  <div className="mt-1 flex flex-wrap items-center gap-2">
                    {report?.recorded && <Chip variant="accent">Recorded</Chip>}
                    <span className="text-[13px] text-text-3">
                      Last check {fmtDate(home.last_check_at)}
                    </span>
                  </div>
                </div>
                <OverflowMenu
                  items={[
                    {
                      label: "Delete this place",
                      danger: true,
                      onClick: () => setConfirming(home.label),
                    },
                  ]}
                />
              </div>

              {report && counts && (
                <div className="mt-3">
                  <TallyBar
                    compact
                    counts={counts}
                    labels={[["problem", "problems"], ["needs a human look", "need a human look"], ["can't tell", "can't tell"], ["checked, no problem", "checked, no problem"]]}
                  />
                  <p className="mt-2 font-mono text-[12.5px] tabular-nums text-text-2">
                    {plural(home.open_findings, "open finding")} · re-check{" "}
                    {fmtDate(home.recheck_due)}
                  </p>
                </div>
              )}

              <div className="mt-3 flex flex-wrap items-center gap-2">
                <Button
                  variant="primary"
                  onClick={() => navigate(`/checkup/${home.last_checkup_id}/report`)}
                >
                  Open report
                </Button>
                <Button
                  variant="secondary"
                  onClick={() => navigate(`/checkup/${home.last_checkup_id}/recheck`)}
                >
                  Re-check
                </Button>
              </div>
              <button
                type="button"
                onClick={() => navigate(`/checkup/${home.last_checkup_id}/fixes`)}
                className="mt-1 inline-flex min-h-[44px] items-center rounded-btn px-2 text-[14px] font-semibold text-accent transition-colors duration-[120ms] hover:bg-accent-bg"
              >
                Fix tracker →
              </button>

              {confirming === home.label && (
                <div className="mt-3 rounded-card bg-bad-bg p-3">
                  <p className="text-[14px] font-medium">
                    Delete {home.label} and ALL of its data — checks,
                    reports and videos? This cannot be undone.
                  </p>
                  <div className="mt-2 flex gap-2">
                    <Button variant="danger" onClick={() => void remove(home.label)}>
                      Yes, delete everything
                    </Button>
                    <Button variant="secondary" onClick={() => setConfirming(null)}>
                      Keep it
                    </Button>
                  </div>
                </div>
              )}
            </Card>
          );
        })}
      </div>
    </main>
  );
}
