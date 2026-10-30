"""Two-way check + propose stability + edits experiment (2026-10-30).

Unit tests, no live calls: sweep planning under its SAM budget, sweep
hits judged into hazards, verdict-strength merging, temperature 0 in
propose payloads, edit-region context expansion, and the edit
instruction planner wiring in visualize.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from secondshift.checklists.loader import load_all_packs  # noqa: E402
from secondshift.domain.checkup import Keyframe  # noqa: E402
from secondshift.domain.enums import Verification  # noqa: E402
from secondshift.domain.hazards import Evidence, Hazard, Mask  # noqa: E402
from secondshift.pipeline import sweep as sweep_mod  # noqa: E402
from secondshift.pipeline.visualize import _expand_context  # noqa: E402
from secondshift.providers.base import ImageRef, JudgeResponse  # noqa: E402


def _kf(idx: int, room: str, t: float, sharpness: float = 0.5) -> Keyframe:
    return Keyframe(
        id=f"kf-{idx}",
        capture_id="cap",
        t=t,
        image_path=f"/tmp/kf-{idx}.jpg",
        sharpness=sharpness,
        brightness=0.5,
        usable=True,
        room_guess=room,
    )


def test_best_frames_picks_sharpest_spread_per_room() -> None:
    frames = [
        _kf(1, "living", 0.0, 0.1),
        _kf(2, "living", 0.5, 0.9),  # sharpest but close to kf-3
        _kf(3, "living", 1.0, 0.8),
        _kf(4, "living", 5.0, 0.7),
        _kf(5, "living", 9.0, 0.6),
        _kf(6, "kitchen", 2.0, 0.5),
    ]
    by_room = sweep_mod.best_frames_by_room(frames, per_room=3)
    assert len(by_room["living"]) == 3
    ts = [f.t for f in by_room["living"]]
    assert ts == sorted(ts)
    assert 0.0 not in ts  # the blurriest frame is never a "best" frame
    assert len(by_room["kitchen"]) == 1


def test_plan_sweep_budget_covered_and_presence_only() -> None:
    packs_by_id = load_all_packs()
    packs = [packs_by_id[p] for p in ["falls_older_adults", "fire_safety", "pet_safety"]]
    frames = [_kf(i, room, float(i * 3), 0.5) for i, room in enumerate(["living", "kitchen", "bedroom"] * 2)]
    by_room = sweep_mod.best_frames_by_room(frames)
    plan = sweep_mod.plan_sweep(packs, by_room, covered=set(), budget=10)
    # the budget is a hard cap in prompt-level SAM calls (Pass 3 P1)
    prompt_cost = sum(
        len(c.item.sam_prompts) * (2 if c.item.sweep_anchor_prompts else 1)
        for c in plan if c.tile is None
    )
    assert 0 < prompt_cost <= 10
    # covered (item, room) pairs are never planned
    covered = {(plan[0].item.id, plan[0].frame.room_guess or "")}
    plan2 = sweep_mod.plan_sweep(packs, by_room, covered=covered, budget=100)
    assert all((c.item.id, c.frame.room_guess or "") not in covered for c in plan2)
    # absence/measurement/interaction items are never swept
    from secondshift.domain.enums import ItemKind

    assert all(c.item.kind is ItemKind.PRESENCE for c in plan2)


class _StubSegmenter:
    def __init__(self, hit_prompts: set[str]) -> None:
        self.hit_prompts = hit_prompts
        self.calls = 0

    def segment(self, image: ImageRef, prompts: list[str]) -> list[Mask]:
        self.calls += 1
        if any(p in self.hit_prompts for p in prompts):
            return [
                Mask(
                    keyframe_id=image.keyframe_id or "",
                    bbox=(0.4, 0.4, 0.6, 0.6),
                    score=0.9,
                    prompt=prompts[0],
                )
            ]
        return []


class _StubJudge:
    def __init__(self, verdict: str = "confirmed") -> None:
        self.verdict = verdict

    def judge(self, req) -> JudgeResponse:  # type: ignore[no-untyped-def]
        return JudgeResponse(verification=self.verdict, reason="stub judge saw it")


def test_sweep_hit_becomes_a_judged_hazard() -> None:
    packs_by_id = load_all_packs()
    packs = [packs_by_id["pet_safety"]]
    plant = next(i for i in packs[0].items if i.id == "PET-TOXIC-PLANT")
    frames = [_kf(1, "living", 3.0, 0.9), _kf(2, "living", 8.0, 0.8)]
    hazards = sweep_mod.sweep_presence(
        _StubSegmenter(set(plant.sam_prompts)),
        _StubJudge(),
        packs,
        frames,
        ["living"],
        covered=set(),
        checkup_id="chk",
        start_idx=7,
    )
    found = [h for h in hazards if h.item_id == "PET-TOXIC-PLANT"]
    assert len(found) == 1
    assert found[0].verification is Verification.CONFIRMED
    assert found[0].evidence.timestamps == [3.0]
    assert found[0].id.startswith("hz-007-")


def _hazard(item: str, room: str, verdict: Verification) -> Hazard:
    return Hazard(
        id=f"hz-000-{item.lower()}",
        checkup_id="chk",
        pack_id="falls_older_adults",
        item_id=item,
        kind="presence",  # type: ignore[arg-type]
        room=room,
        title=item,
        description="d",
        why_it_matters="w",
        severity=2,  # type: ignore[arg-type]
        verification=verdict,
        verification_reason="r",
        evidence=Evidence(keyframe_ids=["k"], timestamps=[1.0]),
        risk_score=0.0,
    )


def test_merge_sweep_replaces_weaker_verdicts_only() -> None:
    proposed = [
        _hazard("FALL-FLOOR-CORD", "living", Verification.REJECTED),
        _hazard("PET-CORDS-CHEWABLE", "living", Verification.CONFIRMED),
    ]
    swept = [
        _hazard("FALL-FLOOR-CORD", "living", Verification.CONFIRMED),
        _hazard("PET-CORDS-CHEWABLE", "living", Verification.REJECTED),
        _hazard("FALL-FLOOR-RUG", "kitchen", Verification.CONFIRMED),
    ]
    merged = sweep_mod.merge_sweep_hazards(proposed, swept)
    by_key = {(h.item_id, h.room): h.verification for h in merged}
    assert by_key[("FALL-FLOOR-CORD", "living")] is Verification.CONFIRMED  # upgraded
    assert by_key[("PET-CORDS-CHEWABLE", "living")] is Verification.CONFIRMED  # not downgraded
    assert by_key[("FALL-FLOOR-RUG", "kitchen")] is Verification.CONFIRMED  # new finding added
    assert len(merged) == 3  # no duplicates


def test_propose_payload_uses_temperature_zero() -> None:
    from secondshift.providers.meta.text_vision import build_propose_payload

    payload = build_propose_payload("prompt", [], "fast")
    assert payload["temperature"] == 0


def test_expand_context_grows_small_regions() -> None:
    region = _expand_context((900, 500, 1000, 560), 1920, 1080)
    w = region[2] - region[0]
    h = region[3] - region[1]
    assert w >= int(0.55 * 1920)
    assert h >= int(0.80 * 1080)
    assert 0 <= region[0] and region[2] <= 1920
    assert 0 <= region[1] and region[3] <= 1080


def test_visualize_uses_planned_instruction(tmp_path) -> None:  # type: ignore[no-untyped-def]
    from PIL import Image
    from secondshift.domain.hazards import FixCard, FixOption
    from secondshift.pipeline import visualize as viz_mod

    frame = tmp_path / "frame.jpg"
    Image.new("RGB", (640, 480), (120, 120, 120)).save(frame)
    hazard = _hazard("FALL-BED-LIGHT-REACH", "bedroom", Verification.CONFIRMED)
    hazard.evidence = Evidence(
        keyframe_ids=["kf-1"],
        timestamps=[46.0],
        masks=[Mask(keyframe_id="kf-1", bbox=(0.3, 0.3, 0.7, 0.6), score=0.9, prompt="bed")],
    )
    hazard.kind = "absence"  # type: ignore[assignment]
    card = FixCard(
        id="fix-hz-000",
        hazard_id=hazard.id,
        chosen=FixOption(
            id="fix-1",
            title="Add a lamp",
            how="Buy a lamp and put it by the bed.",
            cost_estimate="$",
            difficulty="easy",
            visualization_prompt="Add a bedside lamp on the nightstand next to the bed.",
        ),
        alternatives=[],
        plain_language_steps=["Buy a lamp."],
    )

    class _Editor:
        def edit(self, image: ImageRef, mask_png: bytes, prompt: str) -> bytes:
            import io

            buf = io.BytesIO()
            Image.new("RGB", (640, 480), (120, 120, 120)).save(buf, format="PNG")
            return buf.getvalue()

    class _Vision:
        def plan_edit(self, image: ImageRef, instruction: str) -> str:
            return "Place a small lamp on the existing glass side table to the right of the bed."

    viz, _ = viz_mod.render_visualizations(
        [hazard],
        [card],
        str(tmp_path / "viz"),
        keyframes={"kf-1": str(frame)},
        image_editor=_Editor(),
        segmenter=None,
        vision=_Vision(),
    )
    assert len(viz) == 1
    assert "glass side table" in viz[0].prompt_used
    # and without a planner the pack instruction survives verbatim
    viz2, _ = viz_mod.render_visualizations(
        [hazard],
        [card],
        str(tmp_path / "viz2"),
        keyframes={"kf-1": str(frame)},
        image_editor=_Editor(),
        segmenter=None,
        vision=None,
    )
    assert "nightstand next to the bed" in viz2[0].prompt_used


# --- Pass 3 P1: tiles, proximity, cross-pack tags, room smoothing ---


def test_thin_items_plan_tiles_within_thin_budget(tmp_path) -> None:  # type: ignore[no-untyped-def]
    from PIL import Image

    frame_path = tmp_path / "frame.jpg"
    Image.new("RGB", (640, 480), (90, 90, 90)).save(frame_path)
    packs_by_id = load_all_packs()
    packs = [packs_by_id["falls_older_adults"], packs_by_id["pet_safety"]]
    frames = [
        Keyframe(
            id="kf-1", capture_id="cap", t=1.0, image_path=str(frame_path),
            sharpness=0.9, brightness=0.5, usable=True, room_guess="living",
        )
    ]
    by_room = sweep_mod.best_frames_by_room(frames)
    plan = sweep_mod.plan_sweep(packs, by_room, covered=set(), thin_budget=40)
    tile_calls = [c for c in plan if c.tile is not None]
    thin_items = {c.item.id for c in tile_calls}
    assert "FALL-FLOOR-CORD" in thin_items  # the living-room cord gets tiles
    spent = sum(len(c.item.sam_prompts) for c in tile_calls)
    assert spent <= 40
    # 5 tiles per (thin item, room): 2x2 + floor band
    cord_tiles = [c for c in tile_calls if c.item.id == "FALL-FLOOR-CORD"]
    assert len({c.tile for c in cord_tiles}) == len(sweep_mod.TILES)


def test_tile_mask_remaps_to_full_frame() -> None:
    mask = Mask(keyframe_id="kf-1", bbox=(0.5, 0.5, 1.0, 1.0), score=0.9, prompt="cord")
    remapped = sweep_mod._remap_mask(mask, (0.5, 0.0, 1.0, 0.5))  # top-right tile
    assert remapped.bbox == (0.75, 0.25, 1.0, 0.5)


def test_proximity_near_and_far() -> None:
    towel = Mask(keyframe_id="k", bbox=(0.40, 0.40, 0.50, 0.60), score=0.9, prompt="dish towel")
    stove = Mask(keyframe_id="k", bbox=(0.45, 0.30, 0.75, 0.55), score=0.9, prompt="stove")
    far_stove = Mask(keyframe_id="k", bbox=(0.85, 0.30, 0.99, 0.55), score=0.9, prompt="stove")
    assert sweep_mod._near(towel, stove) is True  # overlapping
    assert sweep_mod._near(towel, far_stove) is False  # 0.35 away > 0.10


def test_cross_pack_tags_cord_gets_both_packs() -> None:
    from secondshift.pipeline.scan import attach_cross_pack_tags

    packs_by_id = load_all_packs()
    packs = [packs_by_id["falls_older_adults"], packs_by_id["pet_safety"]]
    hazard = _hazard("PET-CORDS-CHEWABLE", "living", Verification.CONFIRMED)
    hazard.pack_id = "pet_safety"
    hazard.pack_tags = ["pet_safety"]
    out = attach_cross_pack_tags([hazard], packs)
    assert "falls_older_adults" in out[0].pack_tags  # same dedupe_key: cord_reroute
    rejected = _hazard("FALL-FLOOR-CORD", "living", Verification.REJECTED)
    rejected.pack_id = "falls_older_adults"
    rejected.pack_tags = ["falls_older_adults"]
    out2 = attach_cross_pack_tags([rejected], packs)
    assert out2[0].pack_tags == ["falls_older_adults"]  # rejected earns nothing


def test_room_smoothing_and_unlabeled_area() -> None:
    from secondshift.pipeline.propose import _smooth_room_labels

    def kf(idx: int, t: float, room: str | None, conf: float | None) -> Keyframe:
        return Keyframe(
            id=f"k{idx}", capture_id="c", t=t, image_path="/tmp/x.jpg",
            sharpness=0.5, brightness=0.5, usable=True,
            room_guess=room, room_confidence=conf,
        )

    frames = [
        kf(1, 0.0, "living", 0.9),
        kf(2, 2.0, None, None),        # adopts living (within 3s)
        kf(3, 30.0, "bedroom", 0.4),   # weak, no confident neighbour -> unlabeled area
        kf(4, 60.0, None, None),       # nothing nearby -> unlabeled area
    ]
    _smooth_room_labels(frames)
    assert [f.room_guess for f in frames] == [
        "living", "living", "unlabeled area", "unlabeled area",
    ]


def test_car_seat_tightness_always_cannot_assess() -> None:
    """SEAT-TIGHTNESS can never be verified by a camera: a scan with
    the car seat pack always carries its exact wording as a
    cannot-assess entry and never as a hazard."""
    from secondshift.config import Settings
    from secondshift.domain.checkup import Checkup, Consent
    from secondshift.pipeline.scan import ScanInput, run_scan
    from secondshift.providers.registry import build_providers

    packs_by_id = load_all_packs()
    from datetime import UTC, datetime

    checkup = Checkup(
        created_at=datetime.now(UTC),
        id="chk-seat",
        home_label="Car",
        resident_label="driver",
        pack_ids=["car_seat_check"],
        consent=Consent(resident_informed=True, no_private_moments=True),
    )
    keyframes = [
        Keyframe(
            id="kf-1", capture_id="cap", t=0.0, image_path="",
            sharpness=0.5, brightness=0.5, usable=True, room_guess=None,
        )
    ]
    out = run_scan(
        build_providers(Settings()),
        ScanInput(
            checkup=checkup,
            packs=[packs_by_id["car_seat_check"]],
            keyframes=keyframes,
        ),
    )
    tight = [c for c in out.cannot_assess if c.area == "SEAT-TIGHTNESS"]
    assert len(tight) == 1
    assert "1-inch shake test" in tight[0].detail
    assert all(h.item_id != "SEAT-TIGHTNESS" for h in out.hazards)
