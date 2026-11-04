import { useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "../api/client";
import type { Hazard, Keyframe, Report } from "../api/types";
import ResultBanner from "../components/ResultBanner";

/**
 * Re-check view (evidence-first, 2026-11-03): two stored reports of
 * the same checklist, item by item, with the before evidence frame
 * and the after evidence frame SIDE BY SIDE and the status change -
 * Found \u2192 Fixed / Still there / New / Not filmed. Everything shown
 * comes from the two stored reports; when an item has no evidence
 * frame on one side, that side shows the room's sharpest frame and
 * labels it as the closest frame, or says no frame exists.
 */

type Status = "fixed" | "still" | "new" | "not_filmed";

const STATUS_LABEL: Record<Status, string> = {
  fixed: "Found \u2192 Fixed",
  still: "Still there",
  new: "New",
  not_filmed: "Not filmed",
};
const STATUS_CLASS: Record<Status, string> = {
  fixed: "bg-green-100",
  still: "bg-red-100",
  new: "bg-amber-100",
  not_filmed: "bg-neutral-200",
};

interface Side {
  hazard?: Hazard;
  frameId?: string;
  closest?: boolean;
}

export default function ComparePage() {
  const { beforeId = "", afterId = "" } = useParams();
  const [before, setBefore] = useState<Report | null>(null);
  const [after, setAfter] = useState<Report | null>(null);
  const [kfMaps, setKfMaps] = useState<{ before: Map<string, Keyframe>; after: Map<string, Keyframe> }>({
    before: new Map(),
    after: new Map(),
  });
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([api.report(beforeId), api.report(afterId)])
      .then(([b, a]) => {
        setBefore(b);
        setAfter(a);
      })
      .catch(() => setError("Both checkups need a finished scan before they can be compared."));
  }, [beforeId, afterId]);

  useEffect(() => {
    if (!before || !after) return;
    const load = async (report: Report) => {
      const kfId = report.hazards.find((h) => h.evidence?.keyframe_ids?.length)?.evidence
        .keyframe_ids[0];
      if (!kfId) return new Map<string, Keyframe>();
      try {
        const r = await api.keyframes(kfId.split("-kf-")[0]);
        return new Map(r.keyframes.map((k) => [k.id, k]));
      } catch {
        return new Map<string, Keyframe>();
      }
    };
    void Promise.all([load(before), load(after)]).then(([b, a]) =>
      setKfMaps({ before: b, after: a }),
    );
  }, [before, after]);

  const rows = useMemo(() => {
    if (!before || !after) return [];
    const key = (h: Hazard) => `${h.item_id}|${h.room}`;
    const found = (r: Report) =>
      new Map(
        r.hazards
          .filter((h) => h.verification === "confirmed" || h.verification === "needs_human")
          .map((h) => [key(h), h]),
      );
    const bFound = found(before);
    const aFound = found(after);
    const side = (report: Report, h: Hazard | undefined, kfs: Map<string, Keyframe>): Side => {
      if (h?.evidence?.keyframe_ids?.[0]) return { hazard: h, frameId: h.evidence.keyframe_ids[0] };
      // No evidence frame: the room's sharpest frame, labelled closest.
      const room = h?.room;
      const roomFrames = [...kfs.values()].filter((k) => !room || k.room_guess === room);
      const sharpest = roomFrames.sort((a, b) => b.sharpness - a.sharpness)[0];
      return { hazard: h, frameId: sharpest?.id, closest: Boolean(sharpest) };
    };
    const keys = new Set([...bFound.keys(), ...aFound.keys()]);
    return [...keys].map((k) => {
      const b = bFound.get(k);
      const a = aFound.get(k);
      const afterNotFilmed =
        !a &&
        after.cannot_assess.some(
          (c) => c.reason === "not_filmed" && b && c.area === b.room,
        );
      const status: Status = b && a ? "still" : b ? (afterNotFilmed ? "not_filmed" : "fixed") : "new";
      const sample = (b ?? a) as Hazard;
      return {
        key: k,
        title: sample.title,
        room: sample.room,
        status,
        beforeSide: side(before, b, kfMaps.before),
        afterSide: side(after, a, kfMaps.after),
        beforeCheckup: beforeId,
        afterCheckup: afterId,
      };
    });
  }, [before, after, kfMaps, beforeId, afterId]);

  if (error) {
    return (
      <main className="mx-auto max-w-2xl p-6">
        <h1 className="text-2xl font-semibold">Re-check comparison</h1>
        <p role="alert" className="mt-3 text-red-700">{error}</p>
      </main>
    );
  }
  if (!before || !after) {
    return (
      <main className="mx-auto max-w-2xl p-6">
        <p>Loading both reports\u2026</p>
      </main>
    );
  }

  const frame = (checkupId: string, s: Side, label: string) => (
    <figure className="min-w-0 flex-1">
      <div className="relative overflow-hidden rounded bg-neutral-700">
        {s.frameId ? (
          <img
            src={api.frameUrl(checkupId, s.frameId)}
            alt={`${label} frame`}
            className="mx-auto block max-h-[300px] w-auto max-w-full"
          />
        ) : (
          <div className="flex aspect-video items-center justify-center text-sm text-white">
            No frame
          </div>
        )}
        <span className="absolute left-2 top-2 rounded bg-black/55 px-2 py-0.5 text-sm text-white">
          {label}
          {s.closest ? " (closest frame)" : ""}
        </span>
        {s.hazard?.evidence?.masks?.[0] && s.frameId && (
          <svg
            className="pointer-events-none absolute inset-0 h-full w-full"
            viewBox="0 0 100 100"
            preserveAspectRatio="none"
            aria-hidden
          >
            <rect
              x={s.hazard.evidence.masks[0].bbox[0] * 100}
              y={s.hazard.evidence.masks[0].bbox[1] * 100}
              width={(s.hazard.evidence.masks[0].bbox[2] - s.hazard.evidence.masks[0].bbox[0]) * 100}
              height={(s.hazard.evidence.masks[0].bbox[3] - s.hazard.evidence.masks[0].bbox[1]) * 100}
              fill="#d33"
              fillOpacity={0.35}
              stroke="#d33"
              strokeWidth={2}
              vectorEffect="non-scaling-stroke"
            />
          </svg>
        )}
      </div>
      <figcaption className="mt-1 text-sm opacity-80">
        {s.hazard
          ? `${s.hazard.verification === "confirmed" ? "Confirmed" : "Needs a human"} \u00B7 ${
              s.hazard.evidence?.timestamps?.[0] !== undefined
                ? `at ${s.hazard.evidence.timestamps[0]}s`
                : "no timestamp"
            }`
          : "Not found in this scan"}
      </figcaption>
    </figure>
  );

  return (
    <main className="mx-auto max-w-3xl p-4">
      <ResultBanner
        recorded={before.recorded && after.recorded ? before.recorded : null}
      />
      <h1 className="text-2xl font-semibold">Re-check: before and after</h1>
      <p className="mt-1 text-sm opacity-80">
        The same checklist, two scans. Each item shows its before and after
        evidence frames side by side.
      </p>
      {rows.length === 0 && (
        <p className="mt-4">Nothing was found in either scan, so there is nothing to compare.</p>
      )}
      {rows.map((row) => (
        <article key={row.key} className="mt-4 rounded border bg-white p-4">
          <div className="flex items-start justify-between gap-2">
            <h2 className="text-lg font-medium">{row.title}</h2>
            <span className={`shrink-0 rounded px-2 py-1 text-sm ${STATUS_CLASS[row.status]}`}>
              {STATUS_LABEL[row.status]}
            </span>
          </div>
          <p className="text-sm uppercase tracking-wide opacity-70">{row.room}</p>
          <div className="mt-3 flex gap-3">
            {frame(row.beforeCheckup, row.beforeSide, "Before")}
            {frame(row.afterCheckup, row.afterSide, "After")}
          </div>
        </article>
      ))}
    </main>
  );
}
