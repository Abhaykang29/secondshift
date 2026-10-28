"""Rule compiler tests (Phase 4): Appendix B end to end, precheck flags,
validator, and the re-check diff through the API."""

from pathlib import Path

import yaml
from fastapi.testclient import TestClient
from secondshift.domain.enums import CompileStatus, Mode, Primitive
from secondshift.domain.rules import Condition, RuleSpec
from secondshift.main import create_app
from secondshift.rules.compiler import compile_rule
from secondshift.rules.observability import REFUSAL_FLAGS, precheck
from secondshift.rules.validate import validate_spec

SENTENCES = yaml.safe_load(
    (Path(__file__).parent.parent / "eval" / "rules" / "sentences.yaml").read_text()
)


def test_precheck_flags_are_right_on_appendix_b() -> None:
    """Spec Phase 4 acceptance: >=95% correct precheck flags on Appendix B."""
    correct = 0
    for entry in SENTENCES:
        flags = precheck(entry["text"], entry["mode_hint"])
        if entry["expected_status"] == "refused":
            ok = bool([f for f in flags if f in REFUSAL_FLAGS]) or "too_vague" in flags
        elif entry["expected_status"] == "compiled":
            ok = not [f for f in flags if f in REFUSAL_FLAGS]
        else:
            ok = True  # clarifications are decided by the compiler layer
        correct += int(ok)
    assert correct / len(SENTENCES) >= 0.95, f"{correct}/{len(SENTENCES)}"


def test_compiler_statuses_on_appendix_b() -> None:
    """Every Appendix B sentence compiles to its expected status."""
    wrong = []
    for entry in SENTENCES:
        spec = compile_rule(entry["text"], entry["mode_hint"])
        if spec.status.value != entry["expected_status"]:
            wrong.append((entry["text"], entry["expected_status"], spec.status.value))
    assert not wrong, f"Wrong statuses: {wrong}"


def test_compiler_primitives_on_appendix_b() -> None:
    """Compiled sentences use exactly the expected primitives."""
    wrong = []
    for entry in SENTENCES:
        if entry["expected_status"] != "compiled":
            continue
        spec = compile_rule(entry["text"], entry["mode_hint"])
        got = sorted(c.primitive.value for c in spec.conditions)
        if got != sorted(entry["expected_primitives"]):
            wrong.append((entry["text"], entry["expected_primitives"], got))
    assert not wrong, f"Wrong primitives: {wrong}"


def test_refusals_always_offer_alternatives() -> None:
    """A refusal without observable alternatives is a compiler bug."""
    for entry in SENTENCES:
        if entry["expected_status"] == "refused":
            spec = compile_rule(entry["text"], entry["mode_hint"])
            assert spec.alternatives, entry["text"]
            assert spec.refusal_reason


def test_validator_rejects_watch_primitive_in_checkup_mode() -> None:
    """state_for_duration in a check-up rule must fail validation."""
    spec = RuleSpec(
        id="r",
        original_text="x",
        status=CompileStatus.COMPILED,
        mode=Mode.CHECKUP,
        conditions=[
            Condition(primitive=Primitive.STATE_FOR_DURATION, target="door", duration_min=5.0)
        ],
        human_summary="Alert if the door is open",
    )
    assert validate_spec(spec)


def test_recheck_diff_through_api() -> None:
    """Scan parent, re-check fixed: rug/grab resolved, cord still, bed light new."""
    client = TestClient(create_app())
    cid = client.post(
        "/api/checkups",
        json={
            "pack_ids": ["falls_older_adults"],
            "resident_label": "Mom",
            "consent": {"resident_informed": True, "no_private_moments": True},
        },
    ).json()["id"]
    client.post(f"/api/checkups/{cid}/scan", json={})
    rule = client.post(
        "/api/rules/compile",
        json={
            "text": "Check that the hallway night light is still there.",
            "mode_hint": "checkup",
            "checkup_id": cid,
        },
    ).json()
    assert rule["status"] == "compiled"
    res = client.post(f"/api/checkups/{cid}/recheck", json={"scenario": "parent_home_fixed"})
    assert res.status_code == 200, res.text
    recheck = res.json()
    by_item = {i["item_id"]: i["status"] for i in recheck["items"]}
    assert by_item["FALL-FLOOR-RUG"] == "resolved"
    assert by_item["FALL-BATH-GRAB-MISSING"] == "resolved"
    assert by_item["FALL-FLOOR-CORD"] == "still_present"
    assert by_item["FALL-BED-LIGHT-REACH"] == "new"
    assert recheck["score_after"] > recheck["score_before"]
    outcomes = {o["rule_id"]: o["outcome"] for o in recheck["rule_outcomes"]}
    assert outcomes[rule["id"]] == "met"  # night light now installed in the fixed scenario
