"""After visualizations (spec 9.9, pass 2 Phase F - rewritten).

For the top 3 ranked hazards whose fix has a visualization_prompt:

- BEFORE: the real evidence keyframe (already person-blurred at scan
  time) with the SAM outline drawn on it - an outline only, labeled
  "Found by SAM (box)" while mask strings don't decode (Decision D10).
- AFTER: a real Muse Image EDIT of the keyframe region.

Edit method (Phase F.2): the Image Get-code snippet exposes no mask
parameter we could verify, so we CROP-EDIT-COMPOSITE: crop the edit
region (hazard box dilated 10% for presence hazards; the space beside
the anchor for absence hazards), send the crop to Muse Image with the
fix's visualization_prompt, resize the result back, feather the edge,
and composite it onto the keyframe. The watermark is burned into the
full frame. The exact prompt sent is stored on the Visualization.

Mock editor: returns the crop stamped "MOCK - no edit", so demo mode
never pretends an edit happened. Demo keyframes without files get a
plain labelled canvas with the same stamp - the old coloured-rectangle
"after" renderer is DELETED (review finding 1).
Depends on: PIL, opencv (via privacy.blur), domain.hazards, providers.
"""

import io
import logging
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from secondshift.domain.enums import ItemKind
from secondshift.domain.hazards import FixCard, Hazard, Visualization
from secondshift.providers.base import ImageEditor, ImageRef, Segmenter

logger = logging.getLogger(__name__)

WATERMARK = "Visualization - not a photo"
MOCK_STAMP = "MOCK - no edit"
EDIT_SUFFIX = (
    " Change only what the instruction says; keep the same room, light and "
    "camera angle. Photorealistic. No people, no text."
)


def _region_for(hazard: Hazard, w: int, h: int) -> tuple[int, int, int, int] | None:
    """Pixel crop region for the edit (presence: dilated hazard box;
    absence: a placement region beside/above/below the anchor box).

    Smoke-test fix 1: the old absence region reused the anchor's own
    width AND height next to it. For a thin, wide anchor (the kitchen
    counter strip SAM returned for the extinguisher) that produced a
    thin sliver at the frame edge - the glitch strip in the after
    photo. The placement region now has a sane minimum size (at least
    ~20% of the frame wide and ~26% tall, capped so it stays a local
    edit), is clamped inside the frame, and must not overlap the
    anchor. If no such region fits, there is no honest edit: None.
    """
    if not hazard.evidence.masks:
        return None
    mask = hazard.evidence.masks[0]
    x0, y0, x1, y1 = mask.bbox
    bw, bh = (x1 - x0) * w, (y1 - y0) * h
    if hazard.kind is ItemKind.ABSENCE:
        ax0, ay0, ax1, ay1 = x0 * w, y0 * h, x1 * w, y1 * h
        gap = 0.02 * w
        cx, cy = (ax0 + ax1) / 2.0, (ay0 + ay1) / 2.0
        # Try the full placement size first, then smaller ones: a big
        # anchor (a bed filling the frame) leaves only a modest free
        # area, and a smaller honest region beats no visualization.
        for scale in (1.0, 0.75, 0.55):
            tw = min(max(bw, 0.20 * w), 0.38 * w) * scale
            th = min(max(bh * 2.5, 0.26 * h), 0.42 * h) * scale
            candidates = [
                (ax1 + gap, cy - th / 2.0),  # right of the anchor
                (ax0 - gap - tw, cy - th / 2.0),  # left of the anchor
                (cx - tw / 2.0, ay1 + gap),  # below the anchor
                (cx - tw / 2.0, ay0 - gap - th),  # above the anchor
            ]
            for rx0, ry0 in candidates:
                rx0 = min(max(rx0, 0.0), w - tw)
                ry0 = min(max(ry0, 0.0), h - th)
                rx1, ry1 = rx0 + tw, ry0 + th
                overlap_x = max(0.0, min(rx1, ax1) - max(rx0, ax0))
                overlap_y = max(0.0, min(ry1, ay1) - max(ry0, ay0))
                if overlap_x * overlap_y > 0:
                    continue  # never edit on top of the anchor itself
                return int(rx0), int(ry0), int(rx1), int(ry1)
        return None
    box = (
        x0 * w - 0.10 * bw,
        y0 * h - 0.10 * bh,
        x1 * w + 0.10 * bw,
        y1 * h + 0.10 * bh,
    )
    ix0, iy0 = max(0, int(box[0])), max(0, int(box[1]))
    ix1, iy1 = min(w, int(box[2])), min(h, int(box[3]))
    if ix1 - ix0 < 16 or iy1 - iy0 < 16:
        return None
    return ix0, iy0, ix1, iy1


def _feather_composite(
    base: Image.Image, edited: Image.Image, region: tuple[int, int, int, int]
) -> Image.Image:
    """Paste the edited crop back with a feathered edge."""
    x0, y0, x1, y1 = region
    edited = edited.convert("RGB").resize((x1 - x0, y1 - y0))
    feather = max(4, int(0.08 * min(x1 - x0, y1 - y0)))
    alpha = Image.new("L", edited.size, 255)
    draw = ImageDraw.Draw(alpha)
    for i in range(feather):
        v = int(255 * (i + 1) / feather)
        draw.rectangle([i, i, edited.width - 1 - i, edited.height - 1 - i], outline=v)
    out = base.convert("RGB").copy()
    out.paste(edited, (x0, y0), alpha)
    return out


def _watermark(image: Image.Image, extra: str | None = None) -> Image.Image:
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default()
    label = WATERMARK if extra is None else f"{WATERMARK} - {extra}"
    draw.text((12, image.height - 24), label, fill=(255, 255, 255), font=font)
    return image


def _draw_outline(draw: ImageDraw.ImageDraw, hazard: Hazard, w: int, h: int) -> None:
    """Draw the SAM verification outline (box while masks don't decode)."""
    for mask in hazard.evidence.masks[:1]:
        if mask.polygon:
            pts = [(x * w, y * h) for x, y in mask.polygon]
            draw.line([*pts, pts[0]], fill=(255, 90, 60), width=3)
    draw.text((12, 30), "Found by SAM (box)", fill=(255, 90, 60))


def render_visualizations(
    hazards: list[Hazard],
    fix_cards: list[FixCard],
    out_dir: str,
    keyframes: dict[str, str] | None = None,
    image_editor: ImageEditor | None = None,
    segmenter: Segmenter | None = None,
) -> tuple[list[Visualization], dict[str, str]]:
    """Render before/after images for the top 3 visual fix candidates.

    keyframes maps keyframe id -> image path. Without a real keyframe
    file (demo stubs) the BEFORE/AFTER pair is a plain labelled canvas
    stamped MOCK - honest demo furniture, not a fake edit.
    """
    from secondshift.privacy.blur import blur_persons

    fixes_by_hazard = {c.hazard_id: c for c in fix_cards}
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    visualizations: list[Visualization] = []
    befores: dict[str, str] = {}
    candidates = [
        h
        for h in hazards
        if h.id in fixes_by_hazard and fixes_by_hazard[h.id].chosen.visualization_prompt
    ][:3]
    if len(candidates) > 1:
        # Image edits are the slowest step in the scan; render the
        # (<= 3) candidates in parallel, one recursive call each.
        from concurrent.futures import ThreadPoolExecutor

        def _one(hazard: Hazard) -> tuple[list[Visualization], dict[str, str]]:
            return render_visualizations(
                [hazard],
                [fixes_by_hazard[hazard.id]],
                out_dir,
                keyframes=keyframes,
                image_editor=image_editor,
                segmenter=segmenter,
            )

        with ThreadPoolExecutor(max_workers=len(candidates)) as pool:
            merged_viz: list[Visualization] = []
            merged_befores: dict[str, str] = {}
            for viz_list, before_map in pool.map(_one, candidates):
                merged_viz.extend(viz_list)
                merged_befores.update(before_map)
            return merged_viz, merged_befores
    for hazard in candidates:
        card = fixes_by_hazard[hazard.id]
        prompt = f"{card.chosen.visualization_prompt}{EDIT_SUFFIX}"
        kf_path = (keyframes or {}).get(
            hazard.evidence.keyframe_ids[0] if hazard.evidence.keyframe_ids else ""
        )
        before_path = out / f"before-{hazard.id}.png"
        after_path = out / f"viz-{hazard.id}.png"
        if not kf_path or not Path(kf_path).exists():
            canvas = Image.new("RGB", (640, 360), (70, 75, 85))
            draw = ImageDraw.Draw(canvas)
            draw.text((12, 10), f"Before: {hazard.title}", fill=(255, 255, 255))
            draw.text((12, 30), MOCK_STAMP, fill=(255, 220, 120))
            canvas.save(before_path)
            after = _watermark(canvas.copy(), MOCK_STAMP)
            draw_a = ImageDraw.Draw(after)
            draw_a.text((12, 10), f"After: {card.chosen.title}", fill=(255, 255, 255))
            after.save(after_path)
            visualizations.append(
                Visualization(
                    id=f"viz-{hazard.id}",
                    hazard_id=hazard.id,
                    source_keyframe_id=hazard.evidence.keyframe_ids[0]
                    if hazard.evidence.keyframe_ids
                    else "",
                    image_path=after_path.name,
                    prompt_used=prompt,
                )
            )
            befores[hazard.id] = str(before_path)
            continue

        # Real path: the keyframe was blurred at scan time; re-check
        # cheaply (cached). A failed check keeps the scan-time state -
        # the frame was already blurred before any scan output existed.
        if segmenter is not None:
            blur_persons(kf_path, segmenter)
        base = Image.open(kf_path).convert("RGB")
        draw_b = ImageDraw.Draw(base)
        draw_b.text((12, 10), f"Before: {hazard.title}", fill=(255, 255, 255))
        _draw_outline(draw_b, hazard, base.width, base.height)
        base.save(before_path)
        befores[hazard.id] = str(before_path)

        region = _region_for(hazard, base.width, base.height)
        after_img: Image.Image | None = None
        if region is not None and image_editor is not None:
            crop = base.crop(region)
            crop_path = out / f"crop-{hazard.id}.png"
            crop.save(crop_path)
            try:
                edited_bytes = image_editor.edit(ImageRef(path=str(crop_path)), b"", prompt)
                edited = Image.open(io.BytesIO(edited_bytes)).convert("RGB")
                after_img = _feather_composite(Image.open(kf_path).convert("RGB"), edited, region)
            except Exception:
                logger.warning("image edit failed for %s; no after image", hazard.id)
                after_img = None
            crop_path.unlink(missing_ok=True)
        if after_img is None:
            continue  # no honest after image - better none than a fake
        draw_a = ImageDraw.Draw(after_img)
        draw_a.text((12, 10), f"After: {card.chosen.title}", fill=(255, 255, 255))
        _watermark(after_img)
        after_img.save(after_path)
        visualizations.append(
            Visualization(
                id=f"viz-{hazard.id}",
                hazard_id=hazard.id,
                source_keyframe_id=hazard.evidence.keyframe_ids[0]
                if hazard.evidence.keyframe_ids
                else "",
                image_path=after_path.name,
                prompt_used=prompt,
            )
        )
    return visualizations, befores
