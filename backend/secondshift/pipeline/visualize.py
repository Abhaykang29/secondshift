"""After visualizations (spec section 9.9).

For the top hazards whose chosen fix has a visualization_prompt, render an
"after" picture. The real path calls Muse Image with a mask built from
the SAM mask; the mock path draws a labelled, watermarked visualization
with PIL over the evidence frame (or a room-coloured canvas when the
keyframe is a demo stub). The watermark is burned in, always.
Depends on: PIL, domain.hazards, providers.base.ImageEditor (real path).
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from secondshift.domain.hazards import FixCard, Hazard, Visualization

WATERMARK = "Visualization \u2014 not a photo"
_ROOM_COLOURS = {
    "hallway": (70, 80, 90),
    "bathroom": (65, 85, 85),
    "kitchen": (85, 75, 55),
    "living": (80, 70, 70),
    "stairs": (60, 60, 80),
    "entry": (90, 90, 60),
    "nursery": (90, 75, 85),
    "bedroom": (75, 70, 90),
}


def _base_image(hazard: Hazard, width: int = 640, height: int = 360) -> Image.Image:
    """The base canvas for a visualization.

    Mock path: a room-coloured canvas (demo keyframes carry no file).
    Phase 7 wires the real evidence keyframe image here.
    """
    return Image.new("RGB", (width, height), _ROOM_COLOURS.get(hazard.room, (80, 80, 80)))


def _draw_mask(
    draw: ImageDraw.ImageDraw, hazard: Hazard, w: int, h: int, colour: tuple[int, int, int]
) -> None:
    for mask in hazard.evidence.masks[:1]:
        if mask.polygon:
            pts = [(x * w, y * h) for x, y in mask.polygon]
            draw.polygon(pts, fill=colour)


def render_visualizations(
    hazards: list[Hazard],
    fix_cards: list[FixCard],
    out_dir: str,
) -> tuple[list[Visualization], dict[str, str]]:
    """Render before/after PNGs for the top 3 fixable hazards.

    Returns (visualizations, before_image_paths by hazard id). Files are
    written under out_dir and served by the reports router.
    """
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
    for hazard in candidates:
        card = fixes_by_hazard[hazard.id]
        prompt = f"{card.chosen.visualization_prompt} Keep everything else identical. Photorealistic. No people."
        before = _base_image(hazard)
        draw_b = ImageDraw.Draw(before)
        _draw_mask(draw_b, hazard, before.width, before.height, (200, 60, 40))
        draw_b.text((12, 10), f"Before: {hazard.title}", fill=(255, 255, 255))
        before_path = out / f"before-{hazard.id}.png"
        before.save(before_path)
        befores[hazard.id] = str(before_path)

        after = _base_image(hazard)
        draw_a = ImageDraw.Draw(after, "RGBA")
        _draw_mask(draw_a, hazard, after.width, after.height, (60, 180, 90))
        draw_a.text((12, 10), f"After: {card.chosen.title}", fill=(255, 255, 255))
        font = ImageFont.load_default()
        draw_a.text((12, after.height - 24), WATERMARK, fill=(255, 255, 255), font=font)
        after_path = out / f"viz-{hazard.id}.png"
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
    return visualizations, befores
