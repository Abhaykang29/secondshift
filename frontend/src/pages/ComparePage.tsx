import { useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "../api/client";
import type { Hazard, Keyframe, Report } from "../api/types";
import ResultBanner from "../components/ResultBanner";
import Card from "../components/ui/Card";
import EvidenceFrame from "../components/ui/EvidenceFrame";
import TallyBar from "../components/ui/TallyBar";
import VerdictChip from "../components/ui/VerdictChip";

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
      <main className="mx-auto max-w-2xl p-4">
        <h1 className="text-[24px] font-[650] leading-[30px] tracking-[-0.01em]">
          Re-check comparison
        </h1>
        <p role="alert" className="mt-3 text-bad">{error}</p>
      </main>
    );
  }
  if (!before || !after) {
    return (
      <main className="mx-auto max-w-2xl p-4">
        <p className="text-text-2">Loading both reports\u2026</p>
      </main>
    );
  }

  const tally = {
    bad: rows.filter((r) => r.status === "still" || r.status === "new").length,
    warn: 0,
    unk: rows.filter((r) => r.status === "not_filmed").length,
    ok: rows.filter((r) => r.status === "fixed").length,
  };

  const frame = (checkupId: string, s: Side, label: "Before" | "After") => {
    const t = s.hazard?.evidence?.timestamps?.[0];
    const caption =
      `${label.toUpperCase()}${t !== undefined ? ` \u00B7 t=${t}s` : ""}` +
      (s.closest ? " \u00B7 closest frame" : "");
    return (
      <figure className="min-w-0">
        <figcaption className="mb-1 text-[11px] font-semibold uppercase tracking-[0.06em] text-text-3">
          {caption}
        </figcaption>
        {s.frameId ? (
          <EvidenceFrame
            src={api.frameUrl(checkupId, s.frameId)}
            alt={`${label} frame`}
            mask={!s.closest ? (s.hazard?.evidence?.masks?.[0] ?? null) : null}
          />
        ) : (
          <div className="flex aspect-video items-center justify-center rounded-card bg-surface-3 text-[14px] text-text-3">
            No frame
          </div>
        )}
        <p className="mt-1 text-[13px] leading-[18px] text-text-3">
          {s.hazard
            ? `${s.hazard.verification === "confirmed" ? "Confirmed" : "Needs a human"} \u00B7 ${
                s.hazard.evidence?.timestamps?.[0] !== undefined
                  ? `at ${s.hazard.evidence.timestamps[0]}s`
                  : "no timestamp"
              }`
            : "Not found in this scan"}
        </p>
      </figure>
    );
  };

  return (
    <main className="mx-auto max-w-3xl p-4">
      <ResultBanner
        recorded={before.recorded && after.recorded ? before.recorded : null}
      />
      <h1 className="text-[24px] font-[650] leading-[30px] tracking-[-0.01em]">
        Re-check: before and after
      </h1>
      <p className="mt-1 text-[14px] leading-[20px] text-text-2">
        The same checklist, two scans. Each item shows its before and after
        evidence frames side by side.
      </p>
      {rows.length > 0 && (
        <div className="mt-4">
          <TallyBar compact counts={tally} labels={[["problem", "problems"], ["needs a look", "needs a look"], ["not filmed", "not filmed"], ["fixed", "fixed"]]} />
        </div>
      )}
      {rows.length === 0 && (
        <p className="mt-4 text-text-2">
          Nothing was found in either scan, so there is nothing to compare.
        </p>
      )}
      {rows.map((row) => (
        <Card key={row.key} className="mt-3">
          <div className="flex items-start justify-between gap-2">
            <h2 className="text-[16px] font-semibold leading-[22px]">{row.title}</h2>
            <VerdictChip kind={row.status} />
          </div>
          <p className="mt-0.5 text-[11px] font-semibold uppercase tracking-[0.06em] text-text-3">
            {row.room}
          </p>
          <div className="mt-3 grid grid-cols-1 gap-2 min-[360px]:grid-cols-2">
            {frame(row.beforeCheckup, row.beforeSide, "Before")}
            {frame(row.afterCheckup, row.afterSide, "After")}
          </div>
        </Card>
      ))}
    </main>
  );
}
