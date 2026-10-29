"""Person-environment analysis for the routine clip (spec section 9.6).

The geometry is pure and unit-tested: support contacts are hand/furniture
mask overlaps sustained over consecutive frames; the walking path is the
polyline of person-mask bottom-centres, buffered - hazards intersecting
the buffer are on the routine path. Summaries describe the interaction
with the space, never the person's body or health.
Depends on: domain models.
"""

from secondshift.domain.hazards import Evidence, RoutineInsight

Box = tuple[float, float, float, float]  # x0, y0, x1, y1 normalized


def _dilate(box: Box, px: float, width_px: float = 512.0) -> Box:
    d = px / width_px
    return (box[0] - d, box[1] - d, box[2] + d, box[3] + d)


def _overlaps(a: Box, b: Box) -> bool:
    return not (a[2] < b[0] or b[2] < a[0] or a[3] < b[1] or b[3] < a[1])


def count_support_contacts(
    hand_boxes: list[Box | None],
    furniture_boxes: dict[str, Box],
    dilate_px: float = 6.0,
    min_frames: int = 3,
) -> dict[str, int]:
    """Count contact events per furniture object from per-frame boxes.

    A contact event = the (dilated) hand box overlaps the furniture box
    for at least min_frames consecutive frames. Example: a hand resting
    on a dresser for 4 frames = 1 event for "dresser".
    """
    counts: dict[str, int] = {}
    streaks: dict[str, int] = {}
    for hand in hand_boxes:
        for name, box in furniture_boxes.items():
            touching = hand is not None and _overlaps(_dilate(hand, dilate_px), box)
            if touching:
                streaks[name] = streaks.get(name, 0) + 1
                if streaks[name] == min_frames:
                    counts[name] = counts.get(name, 0) + 1
            else:
                streaks[name] = 0
    return counts


def path_points(person_boxes: list[Box | None]) -> list[tuple[float, float]]:
    """The walking path: bottom-centre of the person mask per frame."""
    return [((b[0] + b[2]) / 2, b[3]) for b in person_boxes if b is not None]


def on_path(box: Box, path: list[tuple[float, float]], buffer: float = 0.06) -> bool:
    """Whether a hazard box intersects the buffered walking path."""
    for x, y in path:
        if box[0] - buffer <= x <= box[2] + buffer and box[1] - buffer <= y <= box[3] + buffer:
            return True
    return False


def summarize_contacts(
    checkup_id: str,
    contacts: list[dict[str, object]],
    vision: object | None = None,
) -> list[RoutineInsight]:
    """Turn computed support contacts into plain-language insights.

    Pass 2 E.5: with a live provider, Wonder rewrites the summaries
    from the computed numbers via prompts/routine_insights.md; the
    deterministic text stays as fallback (and for mocks).
    """
    insights: list[RoutineInsight] = []
    wonder_texts: list[str] = []
    if vision is not None and contacts:
        numbers = "; ".join(
            f"{entry.get('object')}: {entry.get('count')} support contacts"
            for entry in contacts
        )
        written = vision.routine_insights(numbers)  # type: ignore[attr-defined]
        if written:
            wonder_texts = [
                str(w.get("summary", "")) for w in written if isinstance(w, dict)
            ]
    for idx, entry in enumerate(contacts):
        obj = str(entry["object"])
        raw_count = entry["count"]
        count = int(raw_count) if isinstance(raw_count, (int, float, str)) else 0
        insights.append(
            RoutineInsight(
                id=f"ri-support-{obj}",
                checkup_id=checkup_id,
                kind="support_contact",
                summary=(
                    wonder_texts[idx]
                    if idx < len(wonder_texts) and wonder_texts[idx]
                    else (
                        f"Touched the {obj} {count} times between the bed and the door - "
                        "a sign that a support (rail or sturdy furniture) is needed along this path."
                    )
                ),
                count=count,
                evidence=Evidence(keyframe_ids=[], timestamps=[]),
            )
        )
    return insights
