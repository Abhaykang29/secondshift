"""Rules router: compile, list, and attach rules to a checkup.

Compilation is the two-layer compiler (precheck + mock LLM layer); specs
are stored so re-checks can evaluate a checkup's rules (spec 9.11 step 4).
Depends on: rules.compiler, storage.
"""

from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from secondshift.rules.compiler import compile_rule

router = APIRouter(prefix="/rules", tags=["rules"])


class CompileRequest(BaseModel):
    """A sentence to compile."""

    text: str
    mode_hint: str = "checkup"
    checkup_id: str | None = None


@router.post("/compile")
def compile_endpoint(body: CompileRequest, request: Request) -> dict[str, Any]:
    """Compile a sentence, store the spec, and return it."""
    spec = compile_rule(body.text, body.mode_hint, request.app.state.providers.vision)
    payload = spec.model_dump(mode="json")
    payload["checkup_id"] = body.checkup_id
    request.app.state.store.put("rule", spec.id, payload)
    return payload


@router.get("")
def list_rules(request: Request) -> dict[str, Any]:
    """List all saved rules."""
    return {"rules": request.app.state.store.list("rule")}


@router.get("/{rule_id}")
def get_rule(rule_id: str, request: Request) -> dict[str, Any]:
    """Fetch one saved rule."""
    found: dict[str, Any] | None = request.app.state.store.get("rule", rule_id)
    if found is None:
        raise HTTPException(status_code=404, detail=f"Unknown rule {rule_id}")
    return found
