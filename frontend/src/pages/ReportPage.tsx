import { useCallback, useEffect, useMemo, useState } from "react";
import { plural } from "../plural";
import { Link, useParams } from "react-router-dom";
import { api } from "../api/client";
import type { PackItemSummary } from "../api/extra";
import type { Keyframe, Report } from "../api/types";
import BeforeAfter from "../components/BeforeAfter";
import HazardCard from "../components/HazardCard";
import ResultBanner from "../components/ResultBanner";
import RefilmCard from "../components/RefilmCard";
import en from "../i18n/en.json";

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
  if (error) return <main className="p-4"><p role="alert">{error}</p></main>;
  if (!report) return <main className="p-4"><p>Loading the report...</p></main>;

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

  const reviewControls = (hazardId: string) => {
    const current = marks[hazardId];
    return (
      <div className="mt-3 flex items-center gap-2 border-t pt-3">
        <span className="text-sm font-medium">Was this right?</span>
        <button
          type="button"
          aria-pressed={current === "right"}
          onClick={() => void mark(hazardId, "right")}
          className={`rounded border px-3 ${
            current === "right" ? "bg-[#1f3d2b] font-semibold text-white" : "bg-white"
          }`}
        >
          👍 Right
        </button>
        <button
          type="button"
          aria-pressed={current === "wrong"}
          onClick={() => void mark(hazardId, "wrong")}
          className={`rounded border px-3 ${
            current === "wrong" ? "bg-red-700 font-semibold text-white" : "bg-white"
          }`}
        >
          👎 Wrong
        </button>
        {current && <span className="text-sm opacity-75">Marked {current}</span>}
      </div>
    );
  };

  return (
    <main className="p-4">
      <ResultBanner recorded={report.recorded} />
      <h1 className="text-3xl font-semibold">Home check-up report</h1>
      <p className="mt-3 text-lg">{report.summary}</p>

      <section
        aria-label="Summary"
        className="mt-4 flex flex-wrap gap-x-4 gap-y-1 rounded bg-[#1f3d2b] p-4 text-white"
      >
        <span><strong>{plural(confirmed.length, "thing")} to fix</strong></span>
        <span><strong>{needsHuman.length}</strong> {needsHuman.length === 1 ? "needs" : "need"} a human look</span>
        <span><strong>{report.cannot_assess.length}</strong> couldn&rsquo;t check</span>
      </section>
      <p className="mt-2 text-sm font-medium">
        🏷️ Your reviews: {plural(labelCount, "finding")} labeled
      </p>

      <section aria-label="Fix these first" className="mt-6 rounded bg-amber-50 p-4">
        <h2 className="text-xl font-semibold">{report.fix_first.length === 1 ? "Fix this one first" : `Fix these ${report.fix_first.length} first`}</h2>
        <ol className="mt-2 list-decimal pl-6">
          {report.fix_first.map((hid) => (
            <li key={hid}>{byId.get(hid)?.title ?? hid}</li>
          ))}
        </ol>
        <div className="mt-3 flex flex-wrap gap-3">
          <Link to={`/checkup/${id}/fixes`} className="rounded bg-[#1f3d2b] px-4 py-2 text-white">
            Open the fix tracker
          </Link>
          <Link to={`/checkup/${id}/recheck`} className="rounded border bg-white px-4 py-2">
            Re-check this home
          </Link>
        </div>
      </section>

      <section aria-label="Hazards">
        {confirmed.map((h, i) => (
          <div key={h.id}>
            {(report.pack_ids.length > 1 &&
              (i === 0 || confirmed[i - 1].pack_id !== h.pack_id)) && (
              <h3 className="mt-5 text-lg font-semibold">
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
          <h2 className="text-xl font-semibold">From the routine clip</h2>
          {report.routine_insights.map((insight) => (
            <p key={insight.id} className="mt-2 rounded bg-blue-50 p-3">{insight.summary}</p>
          ))}
        </section>
      )}

      <section aria-label="Fix plan" className="mt-8">
        <h2 className="text-xl font-semibold">Fix plan</h2>
        {report.fixes.map((card) => (
          <article key={card.id} className="mt-3 rounded border bg-white p-4">
            <h3 className="font-medium">{card.chosen.title}</h3>
            <p className="text-sm opacity-80">
              {card.chosen.difficulty} - cost estimate: {card.chosen.cost_estimate}
            </p>
            <ol className="mt-2 list-decimal pl-6">
              {card.plain_language_steps.map((s) => <li key={s}>{s}</li>)}
            </ol>
            {card.alternatives.length > 0 && (
              <p className="mt-2 text-sm">Also possible: {card.alternatives.map((a) => a.title).join("; ")}</p>
            )}
          </article>
        ))}
      </section>

      {needsHuman.length > 0 && (
        <section aria-label="Needs a human look" className="mt-8">
          <h2 className="text-xl font-semibold">Needs a human look</h2>
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

      <RefilmCard
        checkupId={id}
        instructions={report.refilm_instructions ?? []}
        onMerged={(merged) => {
          setReport(merged);
          setJustRefilmed(true);
        }}
      />

      {report.cannot_assess.length > 0 && (
        <section aria-label="Couldn't check" className="mt-8">
          <h2 className="text-xl font-semibold">Couldn&rsquo;t check</h2>
          {/* Can't-tell cards: the closest frame we have of the room,
              why it couldn't be settled, and the re-film instruction. */}
          {(report.refilm_instructions ?? []).map((ins) => {
            const roomFrames = [...kfById.values()].filter((k) => k.room_guess === ins.room);
            const closest = roomFrames.sort((a, b) => b.sharpness - a.sharpness)[0];
            const why = report.cannot_assess.find((c) => c.area === ins.room);
            const title = packItems.find((p) => p.id === ins.item_id)?.title ?? ins.item_id;
            return (
              <article key={ins.item_id} className="mt-3 rounded border-2 border-dashed bg-white p-4">
                <div className="flex items-start justify-between gap-2">
                  <h3 className="text-lg font-medium">{title}</h3>
                  <span className="shrink-0 rounded bg-neutral-200 px-2 py-1 text-sm">Can&rsquo;t tell</span>
                </div>
                <p className="text-sm uppercase tracking-wide opacity-70">{ins.room}</p>
                {closest && (
                  <div className="relative mt-2">
                    <img
                      src={api.frameUrl(id, closest.id)}
                      alt={`Closest frame of the ${ins.room}`}
                      className="mx-auto block max-h-[420px] w-auto max-w-full rounded"
                    />
                    <span className="absolute left-2 top-2 rounded bg-black/55 px-2 py-0.5 text-sm text-white">
                      Closest frame we have
                    </span>
                    {closest.low_sharpness && (
                      <span className="absolute right-2 top-2 rounded bg-black/55 px-2 py-0.5 text-sm text-white">
                        blurry frame
                      </span>
                    )}
                  </div>
                )}
                {why && (
                  <p className="mt-2 text-sm opacity-80">
                    {REASON_LABELS[why.reason] ?? why.reason} — {why.detail}
                  </p>
                )}
                <p className="mt-2">
                  <strong>Re-film:</strong> {ins.instruction}
                </p>
              </article>
            );
          })}
          {[...cannotByReason.entries()].map(([reason, entries]) => (
            <div key={reason} className="mt-3">
              <h3 className="font-medium">{REASON_LABELS[reason] ?? reason}</h3>
              {entries.map((c) => (
                <p key={`${c.area}-${c.detail}`} className="mt-1">
                  {en.cannot_tell.replace("<reason>", `${c.area}: ${c.detail}`)}
                </p>
              ))}
            </div>
          ))}
        </section>
      )}

      <section aria-label="Something it missed" className="mt-8 rounded border bg-white p-4">
        <h2 className="text-xl font-semibold">Something it missed?</h2>
        <p className="mt-1 text-sm opacity-80">
          Tell us what the check should have caught. Your notes become
          labels that make the next check better.
        </p>
        <label className="mt-3 block">
          What was missed
          <select
            value={missedItem}
            onChange={(e) => setMissedItem(e.target.value)}
            className="mt-1 block w-full rounded border p-3"
          >
            {packItems.map((item) => (
              <option key={item.id} value={item.id}>{item.title}</option>
            ))}
          </select>
        </label>
        <label className="mt-3 block">
          Room
          <select
            value={missedRoom}
            onChange={(e) => setMissedRoom(e.target.value)}
            className="mt-1 block w-full rounded border p-3"
          >
            {ROOMS.map((room) => (
              <option key={room} value={room}>{room}</option>
            ))}
          </select>
        </label>
        <label className="mt-3 block">
          When in the video (seconds, optional)
          <input
            type="number"
            min={0}
            inputMode="decimal"
            value={missedTs}
            onChange={(e) => setMissedTs(e.target.value)}
            className="mt-1 block w-full rounded border p-3"
            placeholder="e.g. 42"
          />
        </label>
        <button
          type="button"
          disabled={!missedItem}
          onClick={() => void submitMissed()}
          className="mt-4 w-full rounded bg-[#1f3d2b] px-4 py-3 text-white disabled:opacity-40"
        >
          Save the missed item
        </button>
        {missedSaved && (
          <p className="mt-2 text-sm font-medium text-[#1f3d2b]">Saved — thank you.</p>
        )}
      </section>

      <div className="mt-8 flex gap-3">
        {shareUrl && (
          <a href={shareUrl} target="_blank" rel="noreferrer" className="rounded bg-green-700 px-4 py-3 text-white">
            Share on WhatsApp
          </a>
        )}
        <button type="button" onClick={() => window.print()} className="rounded border bg-white px-4 py-3">
          Print the report
        </button>
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
              <button
                type="button"
                className="rounded border border-dashed bg-white px-4 py-3"
                onClick={() => {
                  void api
                    .scan(id, undefined, captureId, true)
                    .then((r) => setReport(r.report))
                    .catch(() => setError("Re-analyze failed - is the backend in live mode?"));
                }}
              >
                Re-analyze (dev)
              </button>
            );
          })()}
      </div>
      <p className="mt-4 text-sm opacity-80">{report.disclaimer}</p>
    </main>
  );
}
