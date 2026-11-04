import { useCallback, useEffect, useMemo, useState } from "react";
import { plural } from "../plural";
import { Link, useParams } from "react-router-dom";
import { Camera, Tag, ThumbsDown, ThumbsUp } from "lucide-react";
import { api } from "../api/client";
import type { PackItemSummary } from "../api/extra";
import type { Keyframe, Report } from "../api/types";
import BeforeAfter from "../components/BeforeAfter";
import HazardCard from "../components/HazardCard";
import ResultBanner from "../components/ResultBanner";
import RefilmCard from "../components/RefilmCard";
import Button from "../components/ui/Button";
import EvidenceFrame from "../components/ui/EvidenceFrame";
import { PackChip } from "../components/ui/PackIcon";
import TallyBar from "../components/ui/TallyBar";
import VerdictChip from "../components/ui/VerdictChip";
import en from "../i18n/en.json";

const linkBtnPrimary =
  "inline-flex min-h-[44px] items-center justify-center gap-2 rounded-btn bg-accent px-4 text-[15px] font-semibold text-text-inverse transition-all duration-[120ms] hover:bg-accent-hover active:scale-[0.98]";
const linkBtnSecondary =
  "inline-flex min-h-[44px] items-center justify-center gap-2 rounded-btn bg-surface-3 px-4 text-[15px] font-semibold text-text transition-all duration-[120ms] hover:bg-surface-3-hover active:scale-[0.98]";

/**
 * The report page (Pass 3 spec 4.3 step 5 + 4.6) - the money screen:
 * summary counts, fix-these-first, hazard cards with SAM overlays and
 * pack chips, before/after sliders, needs-a-human, couldn't-check
 * grouped by reason, share - plus the review UI: Right/Wrong marks
 * and a "something it missed?" form, all stored as eval labels.
 */

const ROOMS = [
  "kitchen", "bathroom", "bedroom", "living", "hallway",
  "stairs", "entry", "nursery", "unlabeled area",
];

const REASON_LABELS: Record<string, string> = {
  not_filmed: "Not filmed",
  too_dark: "Too dark",
  too_blurry: "Too blurry",
  occluded: "Hidden behind something",
  needs_measurement: "Needs measuring in person",
  not_visible_by_design: "Can't be seen on video",
};

export default function ReportPage() {
  const { id = "" } = useParams();
  const [report, setReport] = useState<Report | null>(null);
  const [justRefilmed, setJustRefilmed] = useState(false);
  const [error, setError] = useState("");
  const [shareUrl, setShareUrl] = useState("");
  const [packTitles, setPackTitles] = useState<Record<string, string>>({});
  const [marks, setMarks] = useState<Record<string, "right" | "wrong">>({});
  const [labelCount, setLabelCount] = useState(0);
  const [packItems, setPackItems] = useState<PackItemSummary[]>([]);
  const [missedItem, setMissedItem] = useState("");
  const [missedRoom, setMissedRoom] = useState("living");
  const [missedTs, setMissedTs] = useState("");
  const [missedSaved, setMissedSaved] = useState(false);
  // Evidence-first UI (2026-11-03): the report's capture keyframes,
  // for evidence frame URLs + the blurry-frame tag + can't-tell
  // closest frames. Derived from the first evidence keyframe id.
  const [kfById, setKfById] = useState<Map<string, Keyframe>>(new Map());

  useEffect(() => {
    if (!report) return;
    const kfId = report.hazards.find((h) => h.evidence?.keyframe_ids?.length)?.evidence
      .keyframe_ids[0];
    if (!kfId) return;
    const captureId = kfId.split("-kf-")[0];
    api
      .keyframes(captureId)
      .then((r) => setKfById(new Map(r.keyframes.map((k) => [k.id, k]))))
      .catch(() => undefined);
  }, [report]);

  const refreshLabelCount = useCallback(() => {
    api
      .reviewsSummary()
      .then((s) => setLabelCount(s.total_labels))
      .catch(() => undefined);
  }, []);

  useEffect(() => {
    api.report(id).then(setReport).catch(() => setError("No report yet - run a scan first."));
    api.share(id).then((s) => setShareUrl(s.whatsapp_url)).catch(() => setShareUrl(""));
    api
      .packs()
      .then((r) =>
        setPackTitles(Object.fromEntries(r.packs.map((p) => [p.pack_id, p.title]))),
      )
      .catch(() => setPackTitles({}));
    api
      .reviews(id)
      .then((r) => {
        const map: Record<string, "right" | "wrong"> = {};
        for (const label of r.labels) {
          if (label.type === "verdict" && label.hazard_id && label.mark) {
            map[label.hazard_id] = label.mark;
          }
        }
        setMarks(map);
      })
      .catch(() => setMarks({}));
    refreshLabelCount();
  }, [id, refreshLabelCount]);

  // Items of this checkup's packs feed the "something it missed?" form.
  useEffect(() => {
    if (!report) return;
    let live = true;
    Promise.all(report.pack_ids.map((pid) => api.pack(pid).catch(() => null)))
      .then((packs) => {
        if (!live) return;
        const items = packs.flatMap((p) => p?.items ?? []);
        setPackItems(items);
        setMissedItem((prev) => prev || items[0]?.id || "");
      })
      .catch(() => undefined);
    return () => {
      live = false;
    };
  }, [report]);

  async function mark(hazardId: string, value: "right" | "wrong") {
    try {
      await api.postReview(id, hazardId, value);
      setMarks((prev) => ({ ...prev, [hazardId]: value }));
      refreshLabelCount();
    } catch {
      /* keep the previous state; the button stays unmarked */
    }
  }

  async function submitMissed() {
    if (!missedItem) return;
    const ts = missedTs.trim() === "" ? null : Number(missedTs);
    try {
      await api.postMissed(id, {
        item_id: missedItem,
        room: missedRoom,
        timestamp_s: ts !== null && Number.isFinite(ts) ? ts : null,
      });
      setMissedSaved(true);
      setMissedTs("");
      refreshLabelCount();
    } catch {
      setMissedSaved(false);
    }
  }

  const byId = useMemo(
    () => new Map((report?.hazards ?? []).map((h) => [h.id, h])),
    [report],
  );
  if (error) return <main><p role="alert">{error}</p></main>;
  if (!report) return <main><p>Loading the report...</p></main>;

  const confirmed = report.hazards
    .filter((h) => h.verification === "confirmed")
    .sort((a, b) => a.pack_id.localeCompare(b.pack_id) || (a.rank ?? 99) - (b.rank ?? 99));
  const needsHuman = report.hazards.filter((h) => h.verification === "needs_human");
  const vizByHazard = new Map(report.visualizations.map((v) => [v.hazard_id, v]));

  const cannotByReason = new Map<string, typeof report.cannot_assess>();
  for (const entry of report.cannot_assess) {
    const list = cannotByReason.get(entry.reason) ?? [];
    list.push(entry);
    cannotByReason.set(entry.reason, list);
  }

  const rejected = report.hazards.filter((h) => h.verification === "rejected");
  const reviewControls = (hazardId: string) => {
    const current = marks[hazardId];
    return (
      <div className="mt-3 flex flex-wrap items-center gap-2 border-t border-border pt-3">
        <span className="text-[14px] font-medium">Was this right?</span>
        <Button
          variant={current === "right" ? "primary" : "secondary"}
          icon={ThumbsUp}
          aria-pressed={current === "right"}
          onClick={() => void mark(hazardId, "right")}
        >
          Right
        </Button>
        <Button
          variant={current === "wrong" ? "primary" : "secondary"}
          icon={ThumbsDown}
          aria-pressed={current === "wrong"}
          onClick={() => void mark(hazardId, "wrong")}
        >
          Wrong
        </Button>
        {current && <span className="text-[14px] text-text-2">Marked {current}</span>}
      </div>
    );
  };

  const reportDate = new Date(report.generated_at).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
  return (
    <main>
      <ResultBanner recorded={report.recorded} />
      <p className="px-1 text-[13px] font-semibold text-accent">Verification report</p>
      <h1 className="mt-0.5 px-1 text-[26px] font-extrabold leading-[32px]">
        Home check-up report
      </h1>
      <p className="mt-1 px-1 text-[14px] text-text-3">
        {reportDate} · {plural(report.pack_ids.length, "checklist")}
        {kfById.size > 0 ? ` · ${plural(kfById.size, "frame")} checked` : ""}
      </p>
      <div className="mt-2.5 flex flex-wrap gap-1.5 px-1">
        {report.pack_ids.map((pid) => (
          <PackChip key={pid} packId={pid} />
        ))}
      </div>

      <div className="mt-4 grid grid-cols-4 gap-2" role="list" aria-label="Results at a glance">
        <BigStat n={confirmed.length} label="Problems" color="var(--bad)" bg="var(--bad-bg)" />
        <BigStat n={needsHuman.length} label="Need a look" color="var(--warn)" bg="var(--warn-bg)" />
        <BigStat n={report.cannot_assess.length} label="Can't tell" color="var(--unk)" bg="var(--unk-bg)" dashed />
        <BigStat n={rejected.length} label="No problem" color="var(--ok)" bg="var(--ok-bg)" />
      </div>

      <section
        aria-label="Summary"
        className="mt-3 rounded-card bg-surface p-4 shadow-card"
      >
        <p className="text-[15px] leading-[22px]">{report.summary}</p>
        <div className="mt-3">
          <TallyBar
            counts={{
              bad: confirmed.length,
              warn: needsHuman.length,
              unk: report.cannot_assess.length,
              ok: rejected.length,
            }}
            labels={[
              ["problem", "problems"],
              ["need a look", "need a look"],
              ["can't tell", "can't tell"],
              ["no problem", "no problem"],
            ]}
          />
        </div>
        <p className="mt-3 flex items-center gap-1.5 text-[14px] font-medium text-text-2">
          <Tag size={14} strokeWidth={1.75} aria-hidden />
          Your reviews: {plural(labelCount, "finding")} labeled
        </p>
      </section>

      <section aria-label="Fix these first" className="mt-3 rounded-card bg-surface p-4 shadow-card">
        <h2 className="text-[19px] font-bold leading-[24px]">{report.fix_first.length === 1 ? "Fix this one first" : `Fix these ${report.fix_first.length} first`}</h2>
        <ol className="mt-2 list-decimal pl-6">
          {report.fix_first.map((hid) => (
            <li key={hid}>{byId.get(hid)?.title ?? hid}</li>
          ))}
        </ol>
        <div className="mt-3 flex flex-wrap gap-2">
          <Link to={`/checkup/${id}/fixes`} className={linkBtnPrimary}>
            Open the fix tracker
          </Link>
          <Link to={`/checkup/${id}/recheck`} className={linkBtnSecondary}>
            Re-check this home
          </Link>
        </div>
      </section>

      <section aria-label="Hazards">
        {confirmed.map((h, i) => (
          <div key={h.id}>
            {(report.pack_ids.length > 1 &&
              (i === 0 || confirmed[i - 1].pack_id !== h.pack_id)) && (
              <h3 className="mt-7 px-1 text-[19px] font-bold leading-[24px]">
                Checklist: {packTitles[h.pack_id] ?? h.pack_id}
              </h3>
            )}
            <HazardCard
              hazard={h}
              packTitles={packTitles}
              footer={reviewControls(h.id)}
              flash={justRefilmed && h.origin === "follow_up"}
              frameUrl={
                h.evidence?.keyframe_ids?.[0]
                  ? api.frameUrl(id, h.evidence.keyframe_ids[0])
                  : undefined
              }
              blurry={Boolean(
                h.evidence?.keyframe_ids?.[0] &&
                  kfById.get(h.evidence.keyframe_ids[0])?.low_sharpness,
              )}
            />
            {vizByHazard.has(h.id) && (
              <BeforeAfter
                title={h.title}
                beforeUrl={api.imageUrl(id, `before-${h.id}.png`)}
                afterUrl={api.imageUrl(id, vizByHazard.get(h.id)?.image_path ?? "")}
              />
            )}
          </div>
        ))}
      </section>

      {report.routine_insights.length > 0 && (
        <section aria-label="Routine insights" className="mt-8">
          <h2 className="text-[17px] font-semibold leading-[24px]">From the routine clip</h2>
          {report.routine_insights.map((insight) => (
            <p key={insight.id} className="mt-2 rounded-tile bg-surface-2 p-3 text-[15px]">{insight.summary}</p>
          ))}
        </section>
      )}

      <section aria-label="Fix plan" className="mt-8">
        <h2 className="text-[17px] font-semibold leading-[24px]">Fix plan</h2>
        {report.fixes.map((card) => (
          <article key={card.id} className="mt-3 rounded-card bg-surface shadow-card p-4">
            <h3 className="text-[16px] font-semibold leading-[22px]">{card.chosen.title}</h3>
            <p className="text-[14px] text-text-2">
              {card.chosen.difficulty} - cost estimate: {card.chosen.cost_estimate}
            </p>
            <ol className="mt-2 list-decimal pl-6">
              {card.plain_language_steps.map((s) => <li key={s}>{s}</li>)}
            </ol>
            {card.alternatives.length > 0 && (
              <p className="mt-2 text-[14px] text-text-2">Also possible: {card.alternatives.map((a) => a.title).join("; ")}</p>
            )}
          </article>
        ))}
      </section>

      {needsHuman.length > 0 && (
        <section aria-label="Needs a human look" className="mt-8">
          <h2 className="text-[17px] font-semibold leading-[24px]">Needs a human look</h2>
          {needsHuman.map((h) => (
            <HazardCard
              key={h.id}
              hazard={h}
              packTitles={packTitles}
              footer={reviewControls(h.id)}
              flash={justRefilmed && h.origin === "follow_up"}
              frameUrl={
                h.evidence?.keyframe_ids?.[0]
                  ? api.frameUrl(id, h.evidence.keyframe_ids[0])
                  : undefined
              }
              blurry={Boolean(
                h.evidence?.keyframe_ids?.[0] &&
                  kfById.get(h.evidence.keyframe_ids[0])?.low_sharpness,
              )}
            />
          ))}
        </section>
      )}

      {rejected.length > 0 && (
        <section aria-label="Checked, no problem" className="mt-8">
          <details className="rounded-card bg-surface shadow-card">
            <summary className="flex min-h-[44px] cursor-pointer items-center px-4 text-[15px] font-semibold">
              Show {plural(rejected.length, "checked item")}
            </summary>
            <div className="border-t border-border px-4 py-2">
              {rejected.map((h) => (
                <div key={h.id} className="flex flex-wrap items-center gap-2 py-2">
                  <span className="flex-1 text-[15px]">{h.title}</span>
                  <VerdictChip kind="rejected" />
                  <span className="w-full text-[14px] text-text-2">{h.verification_reason}</span>
                </div>
              ))}
            </div>
          </details>
        </section>
      )}

      <div className="mt-8">
        <RefilmCard
          checkupId={id}
          instructions={report.refilm_instructions ?? []}
          onMerged={(merged) => {
            setReport(merged);
            setJustRefilmed(true);
          }}
        />
      </div>

      {report.cannot_assess.length > 0 && (
        <section aria-label="Couldn't check" className="mt-8">
          <h2 className="text-[17px] font-semibold leading-[24px]">Couldn&rsquo;t check</h2>
          {/* Can't-tell cards: the closest frame we have of the room,
              why it couldn't be settled, and the re-film instruction. */}
          {(report.refilm_instructions ?? []).map((ins) => {
            const roomFrames = [...kfById.values()].filter((k) => k.room_guess === ins.room);
            const closest = roomFrames.sort((a, b) => b.sharpness - a.sharpness)[0];
            const why = report.cannot_assess.find((c) => c.area === ins.room);
            const title = packItems.find((p) => p.id === ins.item_id)?.title ?? ins.item_id;
            return (
              <article key={ins.item_id} className="mt-3 overflow-hidden rounded-card border border-dashed border-border-strong bg-surface">
                <div className="p-4 pb-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <VerdictChip kind="cannot" />
                    <span className="text-[13px] capitalize text-text-3">{ins.room}</span>
                  </div>
                  <h3 className="mt-2 text-[16px] font-semibold leading-[22px]">{title}</h3>
                </div>
                {closest && (
                  <div className="mt-3">
                    <p className="px-4 pb-2 text-[13px] text-text-3">Closest frame we have</p>
                    <EvidenceFrame
                      src={api.frameUrl(id, closest.id)}
                      alt={`Closest frame of the ${ins.room}`}
                      t={closest.t}
                      blurry={Boolean(closest.low_sharpness)}
                      dimmed
                    />
                  </div>
                )}
                <div className="p-4">
                  {why && (
                    <p className="text-[14px] leading-[20px] text-text-2">
                      {REASON_LABELS[why.reason] ?? why.reason} — {why.detail}
                    </p>
                  )}
                  <div className="mt-3 flex items-start gap-2 rounded-tile bg-surface-2 p-3">
                    <Camera size={18} strokeWidth={1.75} className="mt-0.5 shrink-0 text-accent" aria-hidden />
                    <p className="text-[15px] leading-[22px]">
                      <strong>Re-film:</strong> {ins.instruction}
                    </p>
                  </div>
                </div>
              </article>
            );
          })}
          {[...cannotByReason.entries()].map(([reason, entries]) => (
            <div key={reason} className="mt-3">
              <h3 className="text-[15px] font-semibold">{REASON_LABELS[reason] ?? reason}</h3>
              {entries.map((c) => (
                <p key={`${c.area}-${c.detail}`} className="mt-1 text-[15px] text-text-2">
                  {en.cannot_tell.replace("<reason>", `${c.title ?? c.area}: ${c.detail}`)}
                </p>
              ))}
            </div>
          ))}
        </section>
      )}

      <section aria-label="Something it missed" className="mt-3 rounded-card bg-surface p-4 shadow-card">
        <h2 className="text-[17px] font-semibold leading-[24px]">Something it missed?</h2>
        <p className="mt-1 text-[14px] leading-[20px] text-text-2">
          Tell us what the check should have caught. Your notes become
          labels that make the next check better.
        </p>
        <label className="mt-3 block text-[14px]">
          What was missed
          <select
            value={missedItem}
            onChange={(e) => setMissedItem(e.target.value)}
            className="mt-1 block w-full rounded-btn border border-border-strong bg-surface p-3 text-[15px]"
          >
            {packItems.map((item) => (
              <option key={item.id} value={item.id}>{item.title}</option>
            ))}
          </select>
        </label>
        <label className="mt-3 block text-[14px]">
          Room
          <select
            value={missedRoom}
            onChange={(e) => setMissedRoom(e.target.value)}
            className="mt-1 block w-full rounded-btn border border-border-strong bg-surface p-3 text-[15px]"
          >
            {ROOMS.map((room) => (
              <option key={room} value={room}>{room}</option>
            ))}
          </select>
        </label>
        <label className="mt-3 block text-[14px]">
          When in the video (seconds, optional)
          <input
            type="number"
            min={0}
            inputMode="decimal"
            value={missedTs}
            onChange={(e) => setMissedTs(e.target.value)}
            className="mt-1 block w-full rounded-btn border border-border-strong bg-surface p-3 text-[15px]"
            placeholder="e.g. 42"
          />
        </label>
        <div className="mt-4">
          <Button variant="primary" fullWidth disabled={!missedItem} onClick={() => void submitMissed()}>
            Save the missed item
          </Button>
        </div>
        {missedSaved && (
          <p className="mt-2 text-[14px] font-medium text-ok">Saved — thank you.</p>
        )}
      </section>

      <div className="mt-8 flex flex-wrap gap-2">
        {shareUrl && (
          <a href={shareUrl} target="_blank" rel="noreferrer" className={linkBtnPrimary}>
            Share on WhatsApp
          </a>
        )}
        <Button variant="secondary" onClick={() => window.print()}>
          Print the report
        </Button>
        {/* Dev-only: results are cached per video, so a normal
            re-scan returns the stored report. ?dev=1 on this page's
            URL reveals a forced fresh analysis. */}
        {new URLSearchParams(window.location.search).get("dev") === "1" &&
          (() => {
            const kfId = report.hazards.find((h) => h.evidence?.keyframe_ids?.length)
              ?.evidence.keyframe_ids[0];
            const captureId = kfId ? kfId.split("-kf-")[0] : null;
            if (!captureId) return null;
            return (
              <Button
                variant="ghost"
                className="border border-dashed border-border-strong"
                onClick={() => {
                  void api
                    .scan(id, undefined, captureId, true)
                    .then((r) => setReport(r.report))
                    .catch(() => setError("Re-analyze failed - is the backend in live mode?"));
                }}
              >
                Re-analyze (dev)
              </Button>
            );
          })()}
      </div>
      <p className="mt-4 text-[13px] text-text-3">{report.disclaimer}</p>
    </main>
  );
}

function BigStat({
  n,
  label,
  color,
  bg,
  dashed,
}: {
  n: number;
  label: string;
  color: string;
  bg: string;
  dashed?: boolean;
}) {
  return (
    <div
      role="listitem"
      className={`flex flex-col items-start rounded-tile px-3 py-2.5 ${dashed ? "border border-dashed border-border-strong" : ""}`}
      style={{ backgroundColor: bg }}
    >
      <span className="font-mono text-[26px] font-extrabold leading-[30px]" style={{ color }}>
        {n}
      </span>
      <span className="mt-0.5 text-[12px] font-semibold leading-[15px] text-text-2">{label}</span>
    </div>
  );
}
