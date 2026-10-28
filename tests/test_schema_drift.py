"""Schema drift test (spec section 17, rule 9).

Every Pydantic model name in the domain package must appear in the
frontend's hand-maintained types.ts. If a model is added or renamed in
Python without updating the TypeScript contract, this test fails.
"""

import inspect
from pathlib import Path

import secondshift.domain.checkup as checkup_mod
import secondshift.domain.eval as eval_mod
import secondshift.domain.hazards as hazards_mod
import secondshift.domain.rules as rules_mod
import secondshift.domain.watch as watch_mod
from pydantic import BaseModel

TYPES_TS = Path(__file__).parent.parent / "frontend" / "src" / "api" / "types.ts"


def _model_names() -> set[str]:
    names: set[str] = set()
    for module in (checkup_mod, hazards_mod, rules_mod, watch_mod, eval_mod):
        for name, obj in vars(module).items():
            if inspect.isclass(obj) and issubclass(obj, BaseModel) and obj is not BaseModel:
                if obj.__module__ == module.__name__:
                    names.add(name)
    return names


def test_every_domain_model_exists_in_frontend_types() -> None:
    """All domain models are mirrored in frontend/src/api/types.ts."""
    ts = TYPES_TS.read_text()
    missing = sorted(n for n in _model_names() if n not in ts)
    assert not missing, f"Domain models missing from frontend types.ts: {missing}"
