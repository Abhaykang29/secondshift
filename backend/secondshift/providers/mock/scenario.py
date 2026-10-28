"""Mock scenario loading (spec section 11.2).

Why: all mock providers must agree on one deterministic scenario - the
vision mock proposes its hazards, the SAM mock knows which objects are
*not* there (safety objects with safety_found=false, and segment_missing
proposals), and the transcriber mock speaks its narration.
Depends on: PyYAML, stdlib.
"""

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

SCENARIO_DIR = Path(__file__).parents[4] / "fixtures" / "mock_scenarios"


@lru_cache(maxsize=8)
def load_scenario(name: str) -> dict[str, Any]:
    """Load one scenario YAML by name (cached; scenarios are fixtures)."""
    path = SCENARIO_DIR / f"{name}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Unknown mock scenario: {name}")
    data: dict[str, Any] = yaml.safe_load(path.read_text())
    return data


def default_scenario_name() -> str:
    """Scenario from the environment, defaulting to the parent home demo."""
    return os.environ.get("SECONDSHIFT_SCENARIO", "parent_home_demo")


def missing_prompts(scenario: dict[str, Any]) -> set[str]:
    """Prompts SAM must NOT find in this scenario.

    Two honest cases: safety objects a scenario says are absent
    (safety_found=false), and proposals flagged segment_missing - the
    model's false positive that SAM verification exists to reject.
    """
    missing: set[str] = set()
    for proposal in scenario.get("proposals", []):
        if proposal.get("safety_found") is False:
            missing.update(proposal.get("safety_prompts", []))
        if proposal.get("segment_missing"):
            missing.update(proposal.get("sam_prompts", []))
    return missing


def polygon_for(scenario: dict[str, Any], prompt: str) -> list[tuple[float, float]] | None:
    """The scenario polygon for a prompt, if one was authored."""
    for proposal in scenario.get("proposals", []):
        prompts = list(proposal.get("sam_prompts", [])) + list(proposal.get("safety_prompts", []))
        if prompt in prompts:
            poly = proposal.get("mask_polygon") or proposal.get("anchor_polygon")
            if poly:
                return [(float(point[0]), float(point[1])) for point in poly]
    return None
