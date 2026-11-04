import type { ReactNode } from "react";
import { GitBranch } from "lucide-react";
import type { Hazard } from "../api/types";
import Chip from "./ui/Chip";
import VerdictChip from "./ui/VerdictChip";
import EvidenceFrame from "./ui/EvidenceFrame";
import { PackChip } from "./ui/PackIcon";

const SEVERITY_LABEL: Record<number, string> = { 3: "High", 2: "Medium", 1: "Low" };

/**
 * One hazard card (redesign spec 5.3): the evidence frame with the
 * SAM overlay (normalized coords), verdict + pack + severity chips,
 * the plain-language reason, and the production chain in mono.
 * For absence hazards the anchor outline is drawn and labelled
 * missing. A missing timestamp shows no chip, never 0s.
 */
/** The chain that produced this verdict, from the stored fields:
 * Spark proposed it, SAM's mask (label = mask.prompt) is the proof,
 * and the verdict follows. Absence items invert the SAM step. */
function chainFor(hazard: Hazard): string {
  const mask = hazard.evidence.masks?.[0];
  if (hazard.verification === "confirmed") {
    if (mask) return `Spark proposed \u2192 SAM found \u201C${mask.prompt}\u201D \u2192 Spark confirmed`;
    if (hazard.kind === "absence")
      return "Spark proposed \u2192 SAM searched where it should be \u2192 Spark confirmed it\u2019s missing";
    return "Spark proposed \u2192 Spark confirmed";
  }
  if (hazard.verification === "needs_human") {
    if (mask)
      return `Spark proposed \u2192 SAM found \u201C${mask.prompt}\u201D \u2192 a human should confirm`;
    return "Spark proposed \u2192 SAM couldn\u2019t settle it \u2192 a human should look";
  }
  return "";
}

export default function HazardCard({
  hazard,
  packTitles,
  footer,
  flash,
  frameUrl,
  blurry,
}: {
  hazard: Hazard;
  packTitles?: Record<string, string>;
  footer?: ReactNode;
  flash?: boolean;
  frameUrl?: string;
  blurry?: boolean;
}) {
  const mask = hazard.evidence.masks?.[0];
  const isAbsence = hazard.kind === "absence";
  const evidenceT = hazard.evidence.timestamps?.[0];
  const tags = hazard.pack_tags && hazard.pack_tags.length > 0
    ? hazard.pack_tags
    : [hazard.pack_id];
  const chain = chainFor(hazard);
  return (
    <article
      className={`mt-3 overflow-hidden rounded-card bg-surface shadow-card${flash ? " refilm-flash" : ""}`}
      aria-label={hazard.title}
    >
      <EvidenceFrame
        src={frameUrl}
        alt={`Evidence frame for ${hazard.title}`}
        mask={mask ? { bbox: mask.bbox, polygon: mask.polygon, prompt: mask.prompt } : null}
        absenceAnchor={isAbsence ? hazard.title : null}
        t={evidenceT}
        blurry={blurry}
        topCornersOnly
        maxHeight={460}
      />
      <div className="p-4">
        <div className="flex flex-wrap items-center gap-1.5">
          {hazard.verification === "confirmed" && <VerdictChip kind="confirmed" />}
          {hazard.verification === "needs_human" && <VerdictChip kind="needs_human" />}
          {hazard.verification === "rejected" && <VerdictChip kind="rejected" />}
          {tags.map((tag) =>
            packTitles && packTitles[tag] && packTitles[tag] !== tag ? (
              <Chip key={tag}>{packTitles[tag]}</Chip>
            ) : (
              <PackChip key={tag} packId={tag} />
            ),
          )}
          {SEVERITY_LABEL[hazard.severity] && <Chip>{SEVERITY_LABEL[hazard.severity]}</Chip>}
          {hazard.origin === "follow_up" && <Chip variant="accent">From follow-up clip</Chip>}
        </div>
        <h3 className="mt-2.5 flex items-start gap-2 text-[17px] font-bold leading-[23px]">
          {hazard.rank ? (
            <span className="mt-[1px] inline-flex h-[22px] min-w-[22px] shrink-0 items-center justify-center rounded-full bg-text px-1.5 font-mono text-[12px] font-bold text-surface">
              {hazard.rank}
            </span>
          ) : null}
          <span>{hazard.title}</span>
        </h3>
        <p className="mt-0.5 text-[13px] capitalize text-text-3">
          {hazard.room}
          {hazard.on_routine_path ? " · on the walking path" : ""}
        </p>
        <p className="mt-2 text-[14px] leading-[20px] text-text-2">{hazard.description}</p>
        <p className="mt-1 text-[14px] leading-[20px] text-text-2">
          <em>Why it matters:</em> {hazard.why_it_matters}
        </p>
        <p className="mt-1 text-[14px] leading-[20px] text-text-2">{hazard.verification_reason}</p>
        {chain && (
          <>
                        <p className="mt-3 flex items-start gap-1.5 rounded-btn bg-surface-2 px-3 py-2 text-[13px] font-medium text-text-2">
              <GitBranch size={14} strokeWidth={1.75} className="mt-0.5 shrink-0" aria-hidden />
              <span>{chain}</span>
            </p>
          </>
        )}
        {footer}
      </div>
    </article>
  );
}
