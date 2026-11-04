import { useCallback, useEffect, useState } from "react";
import { BadgeCheck, FileText, House, Plus, RefreshCw, Wrench, type LucideIcon } from "lucide-react";
import { plural } from "../plural";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";
import type { HomeSummary } from "../api/extra";
import type { Report } from "../api/types";
import Button from "../components/ui/Button";
import EvidenceFrame from "../components/ui/EvidenceFrame";
import VerdictChip from "../components/ui/VerdictChip";
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
    iso
      ? new Date(iso).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" })
      : "—";

  return (
    <main className="pt-1">
      <header className="mb-4 flex items-end justify-between gap-3 px-1">
        <div>
          <h1 className="text-[26px] font-extrabold leading-[32px]">Your places</h1>
          <p className="mt-0.5 text-[15px] text-text-3">
            Every check, with the frame that proves it.
          </p>
        </div>
        <Button variant="soft" icon={Plus} className="shrink-0 whitespace-nowrap" onClick={() => navigate("/")}>
          New
        </Button>
      </header>
      {error && (
        <p role="alert" className="mt-3 text-bad">
          {error}
        </p>
      )}
      {homes === null && !error && (
        <div className="grid gap-3" aria-busy="true">
          {[0, 1].map((i) => (
            <div key={i} className="h-[360px] animate-pulse rounded-card bg-surface shadow-card" />
          ))}
        </div>
      )}
      {homes !== null && homes.length === 0 && (
        <EmptyState
          icon={House}
          title="No places yet"
          line="Film a walkthrough to start."
          actionLabel="Start a check"
          onAction={() => navigate("/")}
        />
      )}
      <div className="grid items-start gap-3 lg:grid-cols-2">
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
          const lead = report
            ? report.hazards.find(
                (h) => h.verification === "confirmed" && h.evidence.keyframe_ids.length > 0,
              ) ??
              report.hazards.find(
                (h) => h.verification === "needs_human" && h.evidence.keyframe_ids.length > 0,
              ) ??
              null
            : null;
          const leadMask = lead?.evidence.masks?.[0];
          const title = home.label.replace(/\s*\(recorded\)\s*$/i, "");
          const packCount = home.pack_ids.length;
          return (
            <article
              key={home.label}
              className="overflow-hidden rounded-card bg-surface shadow-card"
            >
              <div className="flex items-start gap-3 px-4 pb-3 pt-3.5">
                <PackIcon packId={home.pack_ids[0] ?? "custom"} />
                <div className="min-w-0 flex-1">
                  <h2 className="flex items-center gap-1.5 text-[16px] font-bold leading-[21px]">
                    <span className="truncate">{title}</span>
                    {report?.recorded && (
                      <BadgeCheck
                        size={17}
                        strokeWidth={2.25}
                        className="shrink-0 text-accent"
                        aria-label="Recorded real result"
                      />
                    )}
                  </h2>
                  <p className="mt-0.5 text-[13px] leading-[18px] text-text-3">
                    {report?.recorded && (
                      <span className="font-semibold text-accent">Recorded real result · </span>
                    )}
                    {fmtDate(home.last_check_at)} · {packCount}{" "}
                    {packCount === 1 ? "checklist" : "checklists"}
                  </p>
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

              {report && lead && (
                <button
                  type="button"
                  className="block w-full text-left"
                  onClick={() => navigate(`/checkup/${home.last_checkup_id}/report`)}
                  aria-label={`Open report: ${lead.title}`}
                >
                  <EvidenceFrame
                    src={api.frameUrl(home.last_checkup_id, lead.evidence.keyframe_ids[0])}
                    alt={`Evidence frame for ${lead.title}`}
                    mask={
                      leadMask
                        ? { bbox: leadMask.bbox, polygon: leadMask.polygon, prompt: leadMask.prompt }
                        : null
                    }
                    t={lead.evidence.timestamps?.[0]}
                    flush
                    maxHeight={340}
                  />
                  <div className="flex items-center gap-2 bg-surface-2 px-4 py-2.5">
                    <span className="truncate text-[14px] font-semibold text-text">
                      {lead.title}
                    </span>
                    <span className="ml-auto shrink-0">
                      <VerdictChip kind={lead.verification === "confirmed" ? "confirmed" : "needs_human"} />
                    </span>
                  </div>
                </button>
              )}

              {report && counts && (
                <div className="px-4 pt-3">
                  <TallyBar
                    compact
                    counts={counts}
                    labels={[["problem", "problems"], ["needs a human look", "need a human look"], ["can't tell", "can't tell"], ["checked, no problem", "checked, no problem"]]}
                  />
                  <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-[13px] text-text-3">
                    <Stat color="var(--bad)" n={counts.bad} label="found" />
                    <Stat color="var(--warn)" n={counts.warn} label="need a look" />
                    <Stat color="var(--unk)" n={counts.unk} label="can't tell" />
                  </div>
                  <p className="mt-1 text-[13px] text-text-3">
                    {plural(home.open_findings, "open finding")} · re-check due {fmtDate(home.recheck_due)}
                  </p>
                </div>
              )}

              <div className="mx-4 mt-3 border-t border-border" />
              <div className="grid grid-cols-3 gap-1 px-2 py-1.5">
                <ActionButton
                  icon={FileText}
                  label="Report"
                  accent
                  onClick={() => navigate(`/checkup/${home.last_checkup_id}/report`)}
                />
                <ActionButton
                  icon={RefreshCw}
                  label="Re-check"
                  onClick={() => navigate(`/checkup/${home.last_checkup_id}/recheck`)}
                />
                <ActionButton
                  icon={Wrench}
                  label="Fixes"
                  onClick={() => navigate(`/checkup/${home.last_checkup_id}/fixes`)}
                />
              </div>

              {confirming === home.label && (
                <div className="mx-4 mb-4 rounded-card bg-bad-bg p-3">
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
            </article>
          );
        })}
      </div>
    </main>
  );
}

function Stat({ color, n, label }: { color: string; n: number; label: string }) {
  if (n === 0) return null;
  return (
    <span className="inline-flex items-center gap-1.5">
      <span className="h-2 w-2 rounded-full" style={{ backgroundColor: color }} aria-hidden />
      <span className="font-mono font-semibold text-text-2">{n}</span> {label}
    </span>
  );
}

function ActionButton({
  icon: Icon,
  label,
  onClick,
  accent,
}: {
  icon: LucideIcon;
  label: string;
  onClick: () => void;
  accent?: boolean;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`inline-flex min-h-[40px] items-center justify-center gap-2 rounded-btn text-[14.5px] font-semibold transition-colors duration-[120ms] hover:bg-surface-2 ${
        accent ? "text-accent" : "text-text-2"
      }`}
    >
      <Icon size={19} strokeWidth={2} aria-hidden />
      {label}
    </button>
  );
}
