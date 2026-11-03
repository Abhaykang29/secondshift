"""Inbox triage (2026-11-03): classify unnamed inbox videos with
Muse Spark (reasoning_effort "low") so the existing pipeline runs
the right check on each one. This is a triage step only - it does
not change the scan pipeline.

Per video: sample ~8 evenly spaced keyframes, blur people with the
pipeline's own blur (privacy/blur.py), and ask Spark to choose ONLY
from the existing packs and the two saved custom checklists
(ROBOT_TABLE, LEAVING_HOME), plus an action: scan | live_check.
A second call compares keyframes across videos to detect
before/after pairs (same space; the clip with more problems visible
is "before"); paired videos become action "before_after_pair".
Fixed-camera clips of a stove, tap or door map to live_check with
the matching pre-written rule. Spark never writes checklist items.

Decisions are saved to data/inbox/triage.json (one-line reason per
video) and printed. Requires the live Meta provider - a mock run
would be a fake decision, so the script refuses PROVIDER != meta.

Usage:
  PROVIDER=meta CACHE_MODE=record CACHE_DIR=fixtures/recordings \
  SECONDSHIFT_PHASE_TAG=triage .venv/bin/python scripts/triage_inbox.py \
      data/inbox/<video> [more videos...]
"""

import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import cv2

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from secondshift.checklists.loader import load_all_packs  # noqa: E402
from secondshift.config import Settings  # noqa: E402
from secondshift.inbox_map import (  # noqa: E402
    DOOR_RULE,
    KITCHEN_OFF_CHECKLIST_LINES,
    STOVE_RULE,
    TABLE_CHECKLIST_LINES,
    TAP_RULE,
)
from secondshift.privacy.blur import blur_keyframes  # noqa: E402
from secondshift.providers.base import ImageRef  # noqa: E402
from secondshift.providers.meta.text_vision import (  # noqa: E402
    MODEL_BY_ROLE,
    extract_json,
    image_part,
    normalize_chat_content,
)
from secondshift.providers.registry import build_providers  # noqa: E402

KEYFRAMES_PER_VIDEO = 8
MAX_IMAGE_DIM = 1024

CHECKLISTS: dict[str, list[str]] = {
    "ROBOT_TABLE": TABLE_CHECKLIST_LINES,
    "LEAVING_HOME": KITCHEN_OFF_CHECKLIST_LINES,
}
LIVE_RULES: dict[str, str] = {"stove": STOVE_RULE, "tap": TAP_RULE, "door": DOOR_RULE}

PACK_BLURBS: dict[str, str] = {
    "falls_older_adults": "fall hazards for older adults (cords, rugs, lighting, rails, bathroom)",
    "babyproofing": "baby/toddler safety (small objects, outlets, gates, cords)",
    "fire_safety": "fire hazards (stove, heaters, candles, alarms, extinguisher)",
    "earthquake_ready": "tall furniture anchoring, heavy objects, latches",
    "pet_safety": "pet hazards (toxic plants/food, cords, small objects)",
    "home_from_hospital": "recovery-at-home safety after a hospital discharge",
    "home_safety_inspection": "general home safety walkthrough (not a property valuation)",
    "workplace_safety": "workplace walkways, exits, extinguishers (OSHA-style)",
    "car_seat_check": "child car seat screening inside a vehicle",
    "mosquito_breeding": "standing water and mosquito breeding spots",
}


def sample_keyframes(video: Path, out_dir: Path) -> tuple[float, list[tuple[float, Path]]]:
    """Extract ~8 evenly spaced frames; returns (duration_s, [(t, path)])."""
    cap = cv2.VideoCapture(str(video))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    frames_total = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0
    duration = frames_total / fps if fps else 0.0
    out_dir.mkdir(parents=True, exist_ok=True)
    samples: list[tuple[float, Path]] = []
    for i in range(KEYFRAMES_PER_VIDEO):
        t = duration * (i + 0.5) / KEYFRAMES_PER_VIDEO
        cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
        ok, frame = cap.read()
        if not ok:
            continue
        height, width = frame.shape[:2]
        scale = min(1.0, MAX_IMAGE_DIM / max(height, width))
        if scale < 1.0:
            frame = cv2.resize(
                frame, (round(width * scale), round(height * scale)),
                interpolation=cv2.INTER_AREA,
            )
        path = out_dir / f"kf-{i:02d}.jpg"
        cv2.imwrite(str(path), frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
        samples.append((t, path))
    cap.release()
    return duration, samples


def ask_spark(
    vision: Any, prompt: str, labeled: list[tuple[str, ImageRef]]
) -> dict[str, Any]:
    """One Spark chat call (reasoning low) parsed as a JSON object.

    Images carry explicit text labels (the propose-payload convention)
    so the model can cite timestamps and video names truthfully.
    """
    content: list[dict[str, Any]] = [{"type": "text", "text": prompt}]
    for label, image in labeled:
        content.append({"type": "text", "text": label})
        content.append(image_part(image))
    payload: dict[str, Any] = {
        "model": MODEL_BY_ROLE["fast"],
        "messages": [{"role": "user", "content": content}],
        "reasoning_effort": "low",
    }
    data = vision._post_chat(payload)
    return extract_json(normalize_chat_content(data))


def classify_prompt(pack_ids: list[str]) -> str:
    packs = "\n".join(f"- {pid}: {PACK_BLURBS.get(pid, pid)}" for pid in pack_ids)
    robot = " ".join(CHECKLISTS["ROBOT_TABLE"])
    leaving = " ".join(CHECKLISTS["LEAVING_HOME"])
    return f"""You are triaging one unnamed home video for the SecondShift safety-check pipeline. The attached frames are evenly spaced samples from the video, in order, labeled with timestamps. People are blurred for privacy.

Choose exactly one action:
- "scan": a walkthrough or moving-camera clip that a safety checklist should scan.
- "live_check": ONLY if the camera is fixed (the framing barely changes across the frames) AND the view is a long static watch on a stove, a kitchen tap, or a door.

For "scan", choose the target: either "pack_ids" (1 to 3 of the packs below) or "checklist" (one of the two saved checklists) - never both, and NEVER invent new checklist items or packs.
PACKS:
{packs}
CHECKLISTS:
- ROBOT_TABLE: "{robot}" - use when the clip is mainly about a table or dining area's state.
- LEAVING_HOME: "{leaving}" - use when the clip is mainly a kitchen/room check of things left on or open.

For "live_check", set "live_target" to "stove", "tap" or "door" (fixed rules are pre-written for these; do not write a rule).

Also report: "camera": "fixed" or "handheld"; "space": a short description of the space shown; "problems_visible": how many distinct problems or concerns you can see for the chosen target (0 if none); "reason": ONE line explaining the decision.

Respond with a JSON object only:
{{"action": "scan", "pack_ids": [], "checklist": null, "live_target": null, "camera": "handheld", "space": "", "problems_visible": 0, "reason": ""}}"""



def probe_creation_time(video: Path) -> datetime | None:
    """Recording time from the file's QuickTime metadata, if present.

    Prefers com.apple.quicktime.creationdate (the actual recording
    time) over the generic creation_time tag (often the export time).
    """
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries",
             "format_tags=creation_time,com.apple.quicktime.creationdate",
             "-of", "json", str(video)],
            capture_output=True, text=True, check=True,
        )
        tags = json.loads(out.stdout).get("format", {}).get("tags", {})
    except Exception:
        return None
    raw = tags.get("com.apple.quicktime.creationdate") or tags.get("creation_time")
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None


def order_pair(
    spark_before: str,
    spark_after: str,
    created: dict[str, datetime | None],
) -> tuple[str, str, str]:
    """Order a before/after pair: recording time wins when both
    clips carry it; Spark's more-problems call is only the fallback."""
    a, b = created.get(spark_before), created.get(spark_after)
    if a is not None and b is not None and a != b:
        before, after = (spark_before, spark_after) if a < b else (spark_after, spark_before)
        return before, after, "recording_time"
    return spark_before, spark_after, "problems_visible"


def pair_prompt(summaries: dict[str, dict[str, Any]]) -> str:
    lines = "\n".join(
        f"- {name}: space={d.get('space')!r}, problems_visible={d.get('problems_visible')}"
        for name, d in summaries.items()
    )
    return f"""The attached frames come from several videos - two frames per video (an early and a middle frame), each labeled with its video name. Per-video triage summaries:
{lines}

Decide which videos, if any, form a before/after pair: two clips of the SAME space where one shows the space with more problems (the "before") and the other shows it improved (the "after"). Only pair videos you are confident show the same space. A video can be in at most one pair.

Respond with a JSON object only:
{{"pairs": [{{"a": "<file>", "b": "<file>", "before": "<file>", "after": "<file>", "reason": "<one line>"}}]}} - an empty pairs list if none."""


def main() -> int:
    args = [Path(a) for a in sys.argv[1:]]
    if not args:
        inbox = ROOT / "data" / "inbox"
        args = sorted(
            p for p in inbox.iterdir()
            if p.suffix.lower() in (".mp4", ".mov") and p.name != "test_1.mp4"
        )
    if not args:
        print("no videos to triage")
        return 1

    settings = Settings.load()
    if settings.provider != "meta":
        print(f"refusing to triage with provider={settings.provider!r} (mock decisions are fake)")
        return 1
    providers = build_providers(settings)
    vision = providers.vision
    if not hasattr(vision, "_post_chat"):
        print("vision provider has no chat transport; triage needs the Meta provider")
        return 1
    pack_ids = sorted(load_all_packs())

    work_root = ROOT / "data" / "triage"
    decisions: dict[str, dict[str, Any]] = {}
    created: dict[str, datetime | None] = {}
    pair_frames: list[ImageRef] = []

    for video in args:
        started = time.time()
        created[video.name] = probe_creation_time(video)
        duration, samples = sample_keyframes(video, work_root / video.stem)
        blur_keyframes([str(p) for _, p in samples], providers.segmenter)
        labeled = [
            (
                f"Image {i + 1} of {len(samples)}: timestamp_seconds={t:g}",
                ImageRef(path=str(p), keyframe_id=f"{video.stem}-{i}", t=t),
            )
            for i, (t, p) in enumerate(samples)
        ]
        raw = ask_spark(vision, classify_prompt(pack_ids), labeled)
        decision: dict[str, Any] = {
            "action": raw.get("action"),
            "pack_ids": [p for p in raw.get("pack_ids") or [] if p in pack_ids][:3],
            "checklist": raw.get("checklist") if raw.get("checklist") in CHECKLISTS else None,
            "live_target": raw.get("live_target") if raw.get("live_target") in LIVE_RULES else None,
            "camera": raw.get("camera"),
            "space": raw.get("space"),
            "problems_visible": raw.get("problems_visible"),
            "reason": raw.get("reason"),
            "duration_s": round(duration, 1),
            "keyframes": len(samples),
            "recorded_at": created[video.name].isoformat() if created[video.name] else None,
        }
        if decision["action"] == "scan" and not decision["pack_ids"] and not decision["checklist"]:
            decision["action"] = "unprocessable"
            decision["reason"] = (decision["reason"] or "") + " [no valid target chosen]"
        if decision["action"] == "live_check":
            if decision["live_target"] is None:
                decision["action"] = "unprocessable"
                decision["reason"] = (decision["reason"] or "") + " [no valid live target]"
            else:
                decision["live_rule"] = LIVE_RULES[str(decision["live_target"])]
        decisions[video.name] = decision
        print(f"{video.name}: {decision['action']} "
              f"packs={decision['pack_ids']} checklist={decision['checklist']} "
              f"live={decision['live_target']} ({time.time() - started:.0f}s)")
        print(f"  reason: {decision['reason']}")
        for idx in (0, len(samples) // 2):
            t, p = samples[idx]
            pair_frames.append(ImageRef(path=str(p), keyframe_id=video.name, t=t))

    if len(args) > 1:
        labeled_pairs = [
            (f"Video {img.keyframe_id}: timestamp_seconds={img.t or 0:g}", img)
            for img in pair_frames
        ]
        raw_pairs = ask_spark(vision, pair_prompt(decisions), labeled_pairs)
        originals = {
            n: (d["pack_ids"], d["checklist"]) for n, d in decisions.items()
        }
        for pair in raw_pairs.get("pairs") or []:
            a, b = pair.get("a"), pair.get("b")
            spark_before, spark_after = pair.get("before"), pair.get("after")
            if a not in decisions or b not in decisions or spark_before not in (a, b) or spark_after not in (a, b):
                continue
            before, after, basis = order_pair(
                str(spark_before), str(spark_after), created
            )
            # the pair runs the (final) "before" clip's target on both
            base_packs, base_checklist = originals[before]
            for name, role in ((before, "before"), (after, "after")):
                d = decisions[name]
                d["action"] = "before_after_pair"
                d["pair_with"] = b if name == a else a
                d["pair_role"] = role
                d["pair_reason"] = pair.get("reason")
                d["pair_order_basis"] = basis
                d["pack_ids"] = base_packs
                d["checklist"] = base_checklist
            note = (
                " [order corrected by recording time]"
                if basis == "recording_time" and before != spark_before
                else ""
            )
            print(f"pair: {before} (before, {basis}) + {after} (after) - {pair.get('reason')}{note}")

    out = {
        "generated_by": "scripts/triage_inbox.py",
        "model": "muse-spark-1.3",
        "reasoning_effort": "low",
        "videos": decisions,
    }
    out_path = ROOT / "data" / "inbox" / "triage.json"
    out_path.write_text(json.dumps(out, indent=2) + "\n")
    print(f"\nwrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
