"""Run the full demo script end to end on mocks, through record/replay.

Phase A records the mock providers' responses into the record/replay
cache. Phase B runs the ENTIRE demo (docs/DEMO_SCRIPT.md beats 2-6) with
replay-only providers - if any response is missing from the cache this
fails loudly, which is exactly the guarantee demo mode needs on stage.

Usage: python scripts/run_demo.py [--cache-dir DIR]
"""

import argparse
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from secondshift.capture.narration import extract_facts  # noqa: E402
from secondshift.checklists.loader import load_all_packs  # noqa: E402
from secondshift.domain.checkup import Checkup, Consent, Keyframe  # noqa: E402
from secondshift.domain.enums import CacheMode  # noqa: E402
from secondshift.pipeline.scan import ScanInput, assemble_report, run_scan  # noqa: E402
from secondshift.providers.cache import RecordReplayCache  # noqa: E402
from secondshift.providers.cost import CostGuard  # noqa: E402
from secondshift.providers.mock.segmentation import MockSegmenter  # noqa: E402
from secondshift.providers.mock.speech import MockTranscriber  # noqa: E402
from secondshift.providers.mock.vision import MockVisionReasoner  # noqa: E402
from secondshift.providers.registry import Providers  # noqa: E402
from secondshift.providers.replay import (  # noqa: E402
    RecordingSegmenter,
    RecordingTranscriber,
    RecordingVision,
    ReplaySegmenter,
    ReplayTranscriber,
    ReplayVision,
)
from secondshift.recheck.diff import diff_scans  # noqa: E402
from secondshift.rules.compiler import compile_rule  # noqa: E402
from secondshift.watch.engine import WatchEngine  # noqa: E402
from secondshift.watch.gate import ModelGate  # noqa: E402
from secondshift.watch.state_machine import StateMachine  # noqa: E402

SCENARIOS = ("parent_home_demo", "baby_home_demo", "parent_home_fixed")


def _keyframes(n: int = 20) -> list[Keyframe]:
    return [
        Keyframe(
            id=f"demo-kf-{i:03d}",
            capture_id="demo",
            t=float(i * 5),
            image_path="",
            sharpness=500.0,
            brightness=120.0,
            usable=True,
        )
        for i in range(n)
    ]


def _checkup(pack: str) -> Checkup:
    return Checkup(
        id=f"demo-{pack}",
        created_at=datetime.now(UTC),
        pack_ids=[pack],
        resident_label="Mom",
        consent=Consent(resident_informed=True, no_private_moments=True),
    )


def _providers(cache: RecordReplayCache, scenario: str, record: bool) -> Providers:
    if record:
        vision: object = RecordingVision(MockVisionReasoner(scenario), cache, scenario)
        segmenter: object = RecordingSegmenter(MockSegmenter(scenario), cache, scenario)
        transcriber: object = RecordingTranscriber(MockTranscriber(scenario), cache, scenario)
    else:
        vision = ReplayVision(cache, scenario)
        segmenter = ReplaySegmenter(cache, scenario)
        transcriber = ReplayTranscriber(cache, scenario)
    from secondshift.providers.mock.image_edit import MockImageEditor

    return Providers(
        vision=vision,
        segmenter=segmenter,  # type: ignore[arg-type]
        image_editor=MockImageEditor(),
        transcriber=transcriber,  # type: ignore[arg-type]
        cache=cache,
        cost=CostGuard(),
    )


def record_phase(cache_dir: Path) -> None:
    """Run mock scans once, recording every provider response."""
    cache = RecordReplayCache(cache_dir, CacheMode.RECORD)
    packs = load_all_packs()
    for scenario in SCENARIOS:
        pack_id = "babyproofing" if scenario.startswith("baby") else "falls_older_adults"
        providers = _providers(cache, scenario, record=True)
        segments = providers.transcriber.transcribe("demo", "en")  # recorded
        _ = segments
        run_scan(
            providers,
            ScanInput(
                checkup=_checkup(pack_id),
                packs=[packs[pack_id]],
                keyframes=_keyframes(),
                scenario_name=scenario,
            ),
        )


def run_demo(cache_dir: Path) -> dict[str, object]:
    """The full demo script, replay-only. Returns a summary dict."""
    cache = RecordReplayCache(cache_dir, CacheMode.REPLAY)
    packs = load_all_packs()
    summary: dict[str, object] = {}

    # Beat 2-3: parent check-up on replay providers.
    providers = _providers(cache, "parent_home_demo", record=False)
    segments = providers.transcriber.transcribe("demo", "en")
    facts = extract_facts(segments)
    parent_out = run_scan(
        providers,
        ScanInput(
            checkup=_checkup("falls_older_adults"),
            packs=[packs["falls_older_adults"]],
            keyframes=_keyframes(),
            narration_facts=facts,
            scenario_name="parent_home_demo",
        ),
    )
    report = assemble_report(_checkup("falls_older_adults"), parent_out, {})
    confirmed = [h for h in report.hazards if h.verification.value == "confirmed"]
    assert len(confirmed) >= 8, f"expected >=8 confirmed, got {len(confirmed)}"
    assert report.hazards[0].item_id == "FALL-FLOOR-RUG"
    summary["parent_confirmed"] = len(confirmed)
    summary["top_hazard"] = report.hazards[0].item_id

    # Beat 4: the honest refusal.
    refused = compile_rule("Warn me before Mom falls.", "checkup")
    assert refused.status.value == "refused" and refused.alternatives
    summary["refusal_alternatives"] = len(refused.alternatives)

    # Beat 5: re-check against the fixed home (also replay).
    fixed_providers = _providers(cache, "parent_home_fixed", record=False)
    fixed_out = run_scan(
        fixed_providers,
        ScanInput(
            checkup=_checkup("falls_older_adults"),
            packs=[packs["falls_older_adults"]],
            keyframes=_keyframes(),
            scenario_name="parent_home_fixed",
        ),
    )
    recheck = diff_scans("demo", "recheck-demo", parent_out.hazards, fixed_out)
    statuses = {i.item_id: i.status.value for i in recheck.items}
    assert statuses.get("FALL-FLOOR-RUG") == "resolved"
    assert recheck.score_after > recheck.score_before
    summary["recheck_score"] = [recheck.score_before, recheck.score_after]

    # Beat 6: watch - the gate rule, one alert.
    spec = compile_rule(
        "Tell me if the baby gate at the top of the stairs is left open for more than 30 seconds.",
        "watch",
    )
    assert spec.status.value == "compiled"
    engine = WatchEngine(StateMachine("demo", spec.id), ModelGate(CostGuard(), min_interval_s=0.0))
    timeline = [(float(t), 10 <= t < 70) for t in range(0, 121, 5)]
    events = engine.run_duration_rule(timeline, 30.0, "baby gate")
    alerts = [e for e in events if e.state_to.value == "alert"]
    assert len(alerts) == 1
    summary["watch_alerts"] = len(alerts)

    # Baby pack on replay.
    baby_providers = _providers(cache, "baby_home_demo", record=False)
    baby_out = run_scan(
        baby_providers,
        ScanInput(
            checkup=_checkup("babyproofing"),
            packs=[packs["babyproofing"]],
            keyframes=_keyframes(12),
            scenario_name="baby_home_demo",
        ),
    )
    baby_confirmed = [h for h in baby_out.hazards if h.verification.value == "confirmed"]
    assert len(baby_confirmed) == 7
    summary["baby_confirmed"] = len(baby_confirmed)
    return summary


def main() -> None:
    """Record, then run the demo on replay; print the proof summary."""
    parser = argparse.ArgumentParser(description="SecondShift demo on record/replay")
    parser.add_argument("--cache-dir", default="fixtures/recordings/demo-cache")
    args = parser.parse_args()
    cache_dir = Path(args.cache_dir)
    record_phase(cache_dir)
    print(f"Recorded mock responses to {cache_dir}")
    summary = run_demo(cache_dir)
    print("DEMO OK (replay-only):")
    for key, value in summary.items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    main()
