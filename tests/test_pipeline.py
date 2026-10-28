"""Pipeline tests (Phase 2): snapshot of the parent scenario scan, plus
unit tests for routine geometry and the risk-score formula."""

from datetime import UTC, datetime

from secondshift.checklists.loader import load_all_packs
from secondshift.config import Settings
from secondshift.domain.checkup import Checkup, Consent, Keyframe, NarrationFact
from secondshift.pipeline.routine import count_support_contacts, on_path, path_points
from secondshift.pipeline.scan import ScanInput, run_scan
from secondshift.providers.registry import build_providers


def _parent_scan() -> object:
    packs = load_all_packs()
    checkup = Checkup(
        id="c1",
        created_at=datetime.now(UTC),
        pack_ids=["falls_older_adults"],
        resident_label="Mom",
        consent=Consent(resident_informed=True, no_private_moments=True),
    )
    keyframes = [
        Keyframe(
            id=f"k{i}",
            capture_id="cap",
            t=float(i * 5),
            image_path="",
            sharpness=500.0,
            brightness=120.0,
            usable=True,
        )
        for i in range(20)
    ]
    facts = [
        NarrationFact(
            fact="Mom gets up twice a night to use the bathroom",
            t=30.0,
            affects=["night_path", "bathroom"],
        )
    ]
    return run_scan(
        build_providers(Settings()),
        ScanInput(
            checkup=checkup,
            packs=[packs["falls_older_adults"]],
            keyframes=keyframes,
            narration_facts=facts,
            scenario_name="parent_home_demo",
        ),
    )


# Deterministic snapshot of the parent_home_demo scan (item, verification, risk).
EXPECTED_SNAPSHOT = [
    ("FALL-FLOOR-RUG", "confirmed", 5.7),
    ("FALL-BATH-GRAB-MISSING", "confirmed", 4.446),
    ("FALL-BATH-NONSLIP-MISSING", "confirmed", 4.446),
    ("FALL-PATH-NIGHT-LIGHT", "confirmed", 4.446),
    ("FALL-FURNITURE-SUPPORT", "confirmed", 3.978),
    ("FALL-STAIRS-OBJECTS", "confirmed", 3.705),
    ("FALL-FLOOR-CORD", "confirmed", 2.85),
    ("FALL-FLOOR-CLUTTER", "confirmed", 2.47),
    ("FALL-KITCHEN-HIGH-STORAGE", "confirmed", 1.9),
    ("FALL-PET-PATH", "rejected", 0.0),
]


def test_parent_scenario_scan_matches_snapshot() -> None:
    """Phase 2 acceptance snapshot: >=8 hazards, correct states, stable ranking."""
    out = _parent_scan()
    got = [(h.item_id, h.verification.value, h.risk_score) for h in out.hazards]  # type: ignore[attr-defined]
    assert got == EXPECTED_SNAPSHOT
    confirmed = [h for h in out.hazards if h.verification.value == "confirmed"]  # type: ignore[attr-defined]
    assert len(confirmed) >= 8
    assert len(out.routine_insights) >= 1  # type: ignore[attr-defined]
    rug = confirmed[0]
    assert rug.item_id == "FALL-FLOOR-RUG" and rug.on_routine_path is True


def test_scan_is_deterministic() -> None:
    """Two identical scans produce identical rankings."""
    a = [(h.item_id, h.risk_score) for h in _parent_scan().hazards]  # type: ignore[attr-defined]
    b = [(h.item_id, h.risk_score) for h in _parent_scan().hazards]  # type: ignore[attr-defined]
    assert a == b


def test_baby_scenario_scan_confirms_seven() -> None:
    """The baby scenario verifies all 7 hazards including the gate absence."""
    packs = load_all_packs()
    checkup = Checkup(
        id="c2",
        created_at=datetime.now(UTC),
        pack_ids=["babyproofing"],
        consent=Consent(resident_informed=True, no_private_moments=True),
    )
    keyframes = [
        Keyframe(
            id=f"k{i}",
            capture_id="cap",
            t=float(i * 5),
            image_path="",
            sharpness=500.0,
            brightness=120.0,
            usable=True,
        )
        for i in range(12)
    ]
    out = run_scan(
        build_providers(Settings()),
        ScanInput(
            checkup=checkup,
            packs=[packs["babyproofing"]],
            keyframes=keyframes,
            scenario_name="baby_home_demo",
        ),
    )
    confirmed = {h.item_id for h in out.hazards if h.verification.value == "confirmed"}
    assert len(confirmed) == 7
    assert "BABY-STAIRS-NO-GATE" in confirmed


def test_support_contacts_count_sustained_touches_only() -> None:
    """A 2-frame touch is not an event; a 4-frame touch is exactly one."""
    dresser = {"dresser": (0.7, 0.2, 0.95, 0.6)}
    hand_on = (0.72, 0.3, 0.78, 0.4)
    hand_off = (0.1, 0.3, 0.16, 0.4)
    frames = [hand_on, hand_on, hand_off, hand_on, hand_on, hand_on, hand_on, hand_off]
    assert count_support_contacts(frames, dresser, min_frames=3) == {"dresser": 1}
    assert count_support_contacts([hand_on, hand_on], dresser, min_frames=3) == {}


def test_path_obstacle_detection() -> None:
    """A hazard box crossed by the walking path is on the path; a far one is not."""
    person = [(0.1, 0.5, 0.2, 0.9), (0.4, 0.5, 0.5, 0.9), (0.7, 0.5, 0.8, 0.9)]
    path = path_points(person)  # type: ignore[arg-type]
    assert on_path((0.38, 0.8, 0.55, 0.95), path) is True
    assert on_path((0.85, 0.05, 0.95, 0.2), path) is False
