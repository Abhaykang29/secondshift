"""Domain schema tests: the contract in spec section 8 must hold."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError
from secondshift.domain.checkup import Checkup, Consent, Keyframe
from secondshift.domain.enums import ItemKind, Primitive, Severity, Verification
from secondshift.domain.hazards import Evidence, Hazard
from secondshift.domain.rules import Condition, RuleSpec


def test_consent_defaults_match_spec() -> None:
    """Retention defaults to 30 days and raw video is not kept by default."""
    consent = Consent(resident_informed=True, no_private_moments=True)
    assert consent.retention_days == 30
    assert consent.keep_raw_video is False


def test_checkup_requires_consent() -> None:
    """A checkup without consent must not validate."""
    with pytest.raises(ValidationError):
        Checkup(id="c1", created_at=datetime.now(UTC), pack_ids=["falls_older_adults"])  # type: ignore[call-arg]


def test_hazard_round_trip() -> None:
    """A verified hazard serializes and parses back identically."""
    hazard = Hazard(
        id="h1",
        checkup_id="c1",
        pack_id="falls_older_adults",
        item_id="FALL-FLOOR-RUG",
        kind=ItemKind.PRESENCE,
        room="hallway",
        title="Loose rug",
        description="A loose rug in the hallway.",
        why_it_matters="It can catch a foot.",
        severity=Severity.HIGH,
        verification=Verification.CONFIRMED,
        verification_reason="SAM mask 0.91",
        evidence=Evidence(keyframe_ids=["k1"], timestamps=[12.5]),
        risk_score=4.5,
    )
    assert Hazard.model_validate_json(hazard.model_dump_json()) == hazard


def test_keyframe_quality_fields_are_required() -> None:
    """Keyframes without quality metrics must not validate."""
    with pytest.raises(ValidationError):
        Keyframe(id="k1", capture_id="cap1", t=1.0, image_path="x.jpg")  # type: ignore[call-arg]


def test_rule_spec_defaults_match_spec() -> None:
    """Evidence policy defaults: 2 confirmations, min mask score 0.5."""
    spec = RuleSpec(
        id="r1",
        original_text="Tell me if the baby gate is open",
        status="compiled",  # type: ignore[arg-type]
        mode="watch",
        conditions=[
            Condition(primitive=Primitive.OBJECT_STATE, target="baby gate", target_state="open")
        ],
        human_summary="Alert if the baby gate is open",
    )
    assert spec.evidence_policy["min_confirmations"] == 2
    assert spec.evidence_policy["min_mask_score"] == 0.5
    assert spec.notify == ["app"]
