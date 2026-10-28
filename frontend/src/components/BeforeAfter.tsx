import { useState } from "react";

/**
 * Before/after slider for a fix visualization. The "after" image is a
 * watermarked visualization - never presented as a photo.
 */
export default function BeforeAfter({
  beforeUrl, afterUrl, title,
}: { beforeUrl: string; afterUrl: string; title: string }) {
  const [pos, setPos] = useState(50);
  return (
    <figure className="mt-3">
      <div className="relative aspect-video w-full overflow-hidden rounded bg-neutral-700">
        <img src={beforeUrl} alt={`Before: ${title}`} className="absolute inset-0 h-full w-full object-cover" />
        <img
          src={afterUrl}
          alt={`Visualization of the fix: ${title}`}
          className="absolute inset-0 h-full w-full object-cover"
          style={{ clipPath: `inset(0 0 0 ${pos}%)` }}
        />
        <span className="absolute bottom-2 left-2 rounded bg-black/60 px-2 py-1 text-xs text-white">
          Visualization - not a photo
        </span>
      </div>
      <input
        type="range" min={0} max={100} value={pos} aria-label="Before / after slider"
        onChange={(e) => setPos(Number(e.target.value))} className="mt-2 w-full"
      />
    </figure>
  );
}
