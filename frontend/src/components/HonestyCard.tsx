import { useEffect, useState } from "react";
import { api } from "../api/client";
import Banner from "./ui/Banner";
import Card from "./ui/Card";
import StatTile from "./ui/StatTile";

/**
 * Honesty numbers card (final pass, item 2): renders eval/honesty.json
 * via GET /api/eval/honesty - figures computed by
 * scripts/honesty_report.py from stored results, never typed by
 * hand. When the numbers have not been computed, the card renders
 * nothing rather than placeholder figures.
 */
interface HonestyData {
  clips: number;
  items: number;
  answered_items: number;
  abstained_items: number;
  abstain_rate_pct: number | null;
  answered_accuracy_pct: number | null;
  review_labels: { right: number; wrong: number };
  wrong_and_confident: { item_id?: string; room?: string }[];
  clean_room: { clips_found: string[]; false_alarms: number | null };
  refilm: { clips: number; resolved: number };
  ground_truth: {
    clip: string;
    targets: number;
    family_recall?: number;
    strict_recall?: number;
    false_alarms?: string[];
    report_missing?: boolean;
  } | null;
  partner_notes_found: boolean;
  small_sample: boolean;
}

export default function HonestyCard() {
  const [data, setData] = useState<HonestyData | null>(null);
  useEffect(() => {
    api
      .honesty()
      .then((raw) => setData(raw as unknown as HonestyData))
      .catch(() => setData(null));
  }, []);
  if (!data) return null;
  const gt = data.ground_truth;
  const labelTotal = data.review_labels.right + data.review_labels.wrong;
  return (
    <section aria-label="Honesty numbers" className="mt-8">
      <Card title="Our honesty numbers">
        <p className="text-[15px] font-medium">
          Based on {data.clips} clip{data.clips === 1 ? "" : "s"} scored so far.
        </p>
        {data.small_sample && (
          <div className="mt-3">
            <Banner kind="warn">
              Fewer than 10, so treat every number here as a small sample.
            </Banner>
          </div>
        )}
        <div className="mt-3 grid grid-cols-2 gap-3 lg:grid-cols-4">
          <StatTile value={String(data.clips)} label="Clips scored" />
          <StatTile value={String(data.items)} label="Items scored" />
          <StatTile
            value={data.abstain_rate_pct === null ? "No data yet" : `${data.abstain_rate_pct}%`}
            label="Abstain rate"
            muted={data.abstain_rate_pct === null}
          />
          <StatTile
            value={data.answered_accuracy_pct === null ? "No data yet" : `${data.answered_accuracy_pct}%`}
            label="Answered accuracy"
            muted={data.answered_accuracy_pct === null}
          />
        </div>
        <ul className="mt-4 list-disc space-y-1.5 pl-6 text-[15px] leading-[22px]">
          <li>
            Items scored: {data.items} ({data.answered_items} answered, {data.abstained_items}{" "}
            can&rsquo;t tell).
          </li>
          <li>
            Abstain rate:{" "}
            {data.abstain_rate_pct === null ? "no data" : `${data.abstain_rate_pct}%`} of items
            answered &ldquo;can&rsquo;t tell&rdquo;.
          </li>
          <li>
            Answered accuracy:{" "}
            {data.answered_accuracy_pct === null
              ? `no data yet - no Right/Wrong labels recorded (${labelTotal} labels).`
              : `${data.answered_accuracy_pct}% from ${labelTotal} in-app labels.`}
          </li>
          {gt && !gt.report_missing && (
            <li>
              On the one owner-labeled clip ({gt.clip}): found {gt.family_recall} of {gt.targets}{" "}
              listed hazards ({gt.strict_recall} under their exact names);{" "}
              {(gt.false_alarms ?? []).length} reported finding
              {(gt.false_alarms ?? []).length === 1 ? "" : "s"} outside the owner&rsquo;s list
              {(gt.false_alarms ?? []).length > 0 ? `: ${gt.false_alarms?.join(", ")}` : ""}.
            </li>
          )}
          <li>
            Wrong-and-confident: {data.wrong_and_confident.length} confirmed finding
            {data.wrong_and_confident.length === 1 ? "" : "s"} labeled Wrong in the app.
          </li>
          <li>
            Clean-room false alarms:{" "}
            {data.clean_room.false_alarms === null
              ? "not computable - the clean-room clips were never received."
              : `${data.clean_room.false_alarms} on ${data.clean_room.clips_found.length} clean clips.`}
          </li>
          <li>
            Re-film: {data.refilm.resolved} can&rsquo;t-tell items resolved by {data.refilm.clips}{" "}
            follow-up clip{data.refilm.clips === 1 ? "" : "s"} so far.
          </li>
          {!data.partner_notes_found && (
            <li>Partner scoring notes were not received, so no score against them exists.</li>
          )}
        </ul>
        <p className="mt-3 border-t border-border pt-3 text-[12px] leading-[18px] text-text-3">
          Computed from stored results by a script - never typed by hand (eval/HONESTY.md).
        </p>
      </Card>
    </section>
  );
}
