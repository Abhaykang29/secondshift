import { Link } from "react-router-dom";
import { Camera, MapPin, PencilLine } from "lucide-react";
import WatchLive from "./WatchLive";

const LINK_BASE =
  "inline-flex min-h-[44px] items-center justify-center gap-2 rounded-btn px-4 text-[15px] font-semibold transition-all duration-[120ms] active:scale-[0.98]";
const LINK_PRIMARY = "bg-accent text-text-inverse hover:bg-accent-hover";
const LINK_SECONDARY =
  "border border-border-strong bg-surface text-text hover:bg-surface-2";

/**
 * Live tab (Pass 3 spec 4.4): Live Check. Point the phone at one spot,
 * attach a plain-English rule, get instant status. This page hosts the
 * existing watch flow (WatchLive: rule text, room claim + consent,
 * live start/stop over the /camera stream, SSE event list) and links
 * to spot setup and the phone camera source.
 */
export default function LivePage() {
  return (
    <div>
      <div className="p-4 pb-0">
        <h1 className="text-[24px] font-[650] leading-[30px] tracking-[-0.01em]">
          Live Check
        </h1>
        <p className="mt-1 text-[15px] leading-[22px] text-text-2">
          One spot, one plain-English rule. The answer is always one of:
          watching, pending, ALERT, or can&rsquo;t see. No video is saved.
        </p>
        <div className="mt-3 flex flex-wrap gap-3">
          <Link to="/camera" className={`${LINK_BASE} ${LINK_PRIMARY}`}>
            <Camera size={20} strokeWidth={1.75} aria-hidden />
            Open the phone camera
          </Link>
          <Link to="/watch/setup" className={`${LINK_BASE} ${LINK_SECONDARY}`}>
            <MapPin size={20} strokeWidth={1.75} aria-hidden />
            Set up a spot
          </Link>
          <Link to="/rules" className={`${LINK_BASE} ${LINK_SECONDARY}`}>
            <PencilLine size={20} strokeWidth={1.75} aria-hidden />
            Test a rule sentence
          </Link>
        </div>
      </div>
      <WatchLive />
    </div>
  );
}
