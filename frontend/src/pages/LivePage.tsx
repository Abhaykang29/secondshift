import { Link } from "react-router-dom";
import WatchLive from "./WatchLive";

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
        <h1 className="text-2xl font-semibold">Live Check</h1>
        <p className="mt-1 opacity-80">
          One spot, one plain-English rule. The answer is always one of:
          watching, pending, ALERT, or can&rsquo;t see. No video is saved.
        </p>
        <div className="mt-3 flex flex-wrap gap-3">
          <Link
            to="/camera"
            className="rounded bg-[#1f3d2b] px-4 py-2 text-white"
          >
            Open the phone camera
          </Link>
          <Link to="/watch/setup" className="rounded border bg-white px-4 py-2">
            Set up a spot
          </Link>
          <Link to="/rules" className="rounded border bg-white px-4 py-2">
            Test a rule sentence
          </Link>
        </div>
      </div>
      <WatchLive />
    </div>
  );
}
