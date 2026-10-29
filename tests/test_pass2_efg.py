"""Pass 2 Phases E/F/G code tests (NOT live verification).

Everything here runs on synthetic frames, stub providers, and the one
real SAM payload saved in tests/fixtures/sam_real/. Live verification
on real footage is tracked in docs/LIVE_VERIFICATION.md.
"""

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from secondshift.domain.hazards import Mask  # noqa: E402


class _PersonSeg:
    """Finds a 'person' box in the left half; hazards nowhere."""

    def segment(self, image, prompts):  # type: ignore[no-untyped-def]
        if "person" in prompts:
            return [Mask(keyframe_id=image.keyframe_id or "k",
                         bbox=(0.05, 0.05, 0.45, 0.95), score=0.9, prompt="person")]
        return []

    def segment_video(self, frames, prompts):  # type: ignore[no-untyped-def]
        return {}


class _BrokenSeg:
    def segment(self, image, prompts):  # type: ignore[no-untyped-def]
        raise RuntimeError("provider down")

    def segment_video(self, frames, prompts):  # type: ignore[no-untyped-def]
        return {}


def test_blur_persons_blurs_the_person_region(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """A person region loses its detail; the rest of the frame stays."""
    import cv2
    from secondshift.privacy.blur import blur_persons

    frame = np.zeros((200, 200, 3), dtype=np.uint8)
    frame[:, :100] = (np.random.RandomState(0).rand(200, 100, 3) * 255).astype(np.uint8)
    frame[:, 100:] = 128
    path = tmp_path / "kf.png"
    cv2.imwrite(str(path), frame)
    assert blur_persons(str(path), _PersonSeg()) == 1
    out = cv2.imread(str(path))
    assert out[:, :90].std() < frame[:, :90].std()  # detail destroyed
    assert out[:, 150:].std() == pytest.approx(frame[:, 150:].std())  # untouched


def test_blur_persons_reports_failure_and_fallback_keeps_only_the_box(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """Provider failure returns -1; blur_all_but keeps only the hazard box."""
    import cv2
    from secondshift.privacy.blur import blur_all_but, blur_persons

    frame = (np.random.RandomState(1).rand(100, 100, 3) * 255).astype(np.uint8)
    path = tmp_path / "kf.png"
    cv2.imwrite(str(path), frame)
    assert blur_persons(str(path), _BrokenSeg()) == -1
    assert blur_all_but(str(path), (0.4, 0.4, 0.6, 0.6))
    out = cv2.imread(str(path))
    assert out[45:55, 45:55].std() == pytest.approx(frame[45:55, 45:55].std(), rel=0.05)
    assert out[0:20, 0:20].std() < frame[0:20, 0:20].std()


def test_sam_mask_string_decoders_round_trip_and_real_payload_resists() -> None:
    """Standard encodings decode; the real SAM string does not (D10)."""
    import json

    from secondshift.providers.meta.mask_decode import (
        extract_mask_strings,
        try_decode_mask,
    )

    payload = json.loads(
        (Path(__file__).parent / "fixtures" / "sam_real" / "probe_rectangle.json").read_text()
    )
    text = payload["output"][0]["content"][0]["text"]
    strings = extract_mask_strings(text)
    assert len(strings) == 1
    mask, method = try_decode_mask(strings[0], 301, 400)
    assert mask is None and method is None  # documented in mask_decode.py


def test_fix_plan_choice_is_validated_against_the_library() -> None:
    """A live fix choice outside the library falls back to library order."""
    from secondshift.checklists.loader import load_all_packs
    from secondshift.domain.enums import ItemKind, Severity, Verification
    from secondshift.domain.hazards import Evidence, Hazard
    from secondshift.pipeline.fixes import build_fix_cards

    packs = [load_all_packs()["falls_older_adults"]]
    hazard = Hazard(
        id="hz1", checkup_id="c1", pack_id="falls_older_adults",
        item_id="FALL-FLOOR-RUG", kind=ItemKind.PRESENCE, room="hallway",
        title="Loose rug", description="Rug on the path", why_it_matters="Trips",
        severity=Severity.HIGH, verification=Verification.CONFIRMED,
        verification_reason="sam", evidence=Evidence(keyframe_ids=["k"], timestamps=[1.0]),
        risk_score=5.0,
    )

    class RogueVision:
        def plan_fix(self, title, desc, fixes, lang):  # type: ignore[no-untyped-def]
            return {"chosen_fix_id": "INVENTED", "plain_language_steps": ["Do it."]}

    cards = build_fix_cards([hazard], packs, vision=RogueVision())
    assert cards[0].chosen.id == packs[0].items[0].fixes[0].id  # library order kept

    class GoodVision:
        def plan_fix(self, title, desc, fixes, lang):  # type: ignore[no-untyped-def]
            return {"chosen_fix_id": fixes[-1]["id"],
                    "plain_language_steps": ["Step one.", "Step two."]}

    cards = build_fix_cards([hazard], packs, vision=GoodVision())
    assert cards[0].chosen.id == packs[0].items[0].fixes[-1].id
    assert cards[0].plain_language_steps == ["Step one.", "Step two."]


def _gate_setup(tmp_path):  # type: ignore[no-untyped-def]
    """A compiled gate rule + stub providers whose SAM/judge read brightness."""
    from secondshift.providers.cost import CostGuard
    from secondshift.providers.mock.vision import MockVisionReasoner
    from secondshift.rules.compiler import compile_rule

    spec = compile_rule(
        "Tell me if the baby gate at the top of the stairs is left open "
        "for more than 30 seconds.",
        "watch",
        MockVisionReasoner(),
    )
    assert spec.status.value == "compiled"

    class Seg:
        def segment(self, image, prompts):  # type: ignore[no-untyped-def]
            import cv2

            frame = cv2.imread(image.path)
            if frame is not None and frame.mean() > 100:
                return [Mask(keyframe_id="k", bbox=(0.2, 0.2, 0.8, 0.8),
                             score=0.9, prompt=prompts[0])]
            return []

        def segment_video(self, frames, prompts):  # type: ignore[no-untyped-def]
            return {}

    class Vision:
        def judge_state(self, target, question, image):  # type: ignore[no-untyped-def]
            import cv2

            frame = cv2.imread(image.path)
            return "open" if frame is not None and frame.mean() > 100 else "closed"

    class P:
        segmenter = Seg()
        vision = Vision()
        cost = CostGuard()

    return spec, P()


def test_live_watch_alerts_once_then_cannot_see_then_recovers(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """Gate open 30s -> exactly one alert; covered -> CANNOT_SEE; back -> watching."""
    from secondshift.watch.live import LiveWatch

    spec, providers = _gate_setup(tmp_path)
    events: list = []
    watch = LiveWatch(spec, "phone-1", providers, str(tmp_path), on_event=events.append)
    noise = (np.random.RandomState(2).rand(120, 160, 3) * 30).astype(np.uint8)
    closed = np.clip(noise.astype(int) + 30, 0, 255).astype(np.uint8)
    open_ = np.clip(noise.astype(int) + 190, 0, 255).astype(np.uint8)
    covered = np.zeros((120, 160, 3), dtype=np.uint8)
    for t in range(0, 10, 5):
        watch.process_frame(closed, now_s=float(t))
    for t in range(10, 60, 5):
        watch.process_frame(open_, now_s=float(t))
    alerts = [e for e in events if e.state_to.value == "alert"]
    assert len(alerts) == 1
    watch.process_frame(covered, now_s=70.0)
    assert any(e.state_to.value == "cannot_see" for e in events)
    watch.process_frame(closed, now_s=80.0)
    states = [e.state_to.value for e in events]
    assert states[-1] == "watching"


def test_live_watch_room_guard_refuses_bathroom_from_either_side(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """Bathroom from the model OR the user claim refuses the watch."""
    from secondshift.watch.live import classify_watch_room

    class VisionBathroom:
        def classify_room(self, image):  # type: ignore[no-untyped-def]
            return {"room_type": "bathroom", "confidence": 0.9}

    class P:
        vision = VisionBathroom()

    _room, allowed, _reason = classify_watch_room("/x.jpg", "hallway", P())
    assert allowed is False


def test_visualize_real_edit_path_and_mock_stamp(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """Phase F: a real editor's crop lands composited + watermarked;
    the mock editor leaves the keyframe essentially untouched."""
    import cv2
    from secondshift.domain.enums import ItemKind, Severity, Verification
    from secondshift.domain.hazards import Evidence, FixCard, FixOption, Hazard
    from secondshift.pipeline.visualize import render_visualizations
    from secondshift.providers.base import ImageRef
    from secondshift.providers.mock.image_edit import MockImageEditor

    frame = (np.random.RandomState(3).rand(240, 320, 3) * 120 + 60).astype(np.uint8)
    kf = tmp_path / "kf1.jpg"
    cv2.imwrite(str(kf), frame)
    hazard = Hazard(
        id="hz1", checkup_id="c1", pack_id="falls_older_adults",
        item_id="FALL-FLOOR-RUG", kind=ItemKind.PRESENCE, room="hallway",
        title="Loose rug", description="d", why_it_matters="w",
        severity=Severity.HIGH, verification=Verification.CONFIRMED,
        verification_reason="sam",
        evidence=Evidence(
            keyframe_ids=["kf1"], timestamps=[1.0],
            masks=[Mask(keyframe_id="kf1", bbox=(0.3, 0.3, 0.7, 0.7),
                        score=0.9, prompt="rug")],
        ),
        risk_score=5.0,
    )
    card = FixCard(
        id="fix-hz1", hazard_id="hz1",
        chosen=FixOption(id="f1", title="Remove the rug", how="Remove it.",
                         difficulty="easy", cost_estimate="free",
                         visualization_prompt="Remove the rug; show bare floor."),
        alternatives=[], plain_language_steps=["Remove it."],
    )

    class RedEditor:
        def edit(self, image: ImageRef, mask_png: bytes, prompt: str) -> bytes:
            import io

            from PIL import Image

            img = Image.open(image.path).convert("RGB")
            red = Image.new("RGB", img.size, (200, 30, 30))
            buf = io.BytesIO()
            red.save(buf, format="PNG")
            return buf.getvalue()

    viz, _ = render_visualizations(
        [hazard], [card], str(tmp_path / "viz"),
        keyframes={"kf1": str(kf)}, image_editor=RedEditor(), segmenter=_PersonSeg(),
    )
    assert len(viz) == 1 and "Remove the rug" in viz[0].prompt_used
    after = cv2.imread(str(tmp_path / "viz" / viz[0].image_path))
    assert after is not None and after[120, 160][2] > 150  # red edit composited

    viz2, _ = render_visualizations(
        [hazard], [card], str(tmp_path / "viz2"),
        keyframes={"kf1": str(kf)}, image_editor=MockImageEditor(), segmenter=_PersonSeg(),
    )
    after2 = cv2.imread(str(tmp_path / "viz2" / viz2[0].image_path))
    center = after2[120, 160].astype(int)
    assert abs(center[2] - int(frame[120, 160][2])) < 40  # no fake edit in the middle
