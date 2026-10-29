"""Meta text/vision adapter (Muse Spark 1.3 / Muse Wonder) - Phase 7 plug-in.

Written against the best-known shape (spec section 12): an
OpenAI-compatible chat endpoint with image parts and JSON-in-content
structured output. EVERY unverified detail is marked TODO(API); the
normalizers are pure functions unit-tested on sample payloads, so when
the key arrives, only surprises in the real payloads need fixing here -
nothing outside providers/meta/ changes.
Depends on: httpx, providers.base, providers.cost.
"""

import base64
import json
import uuid
from pathlib import Path
from typing import Any, Literal, TypeVar

from pydantic import BaseModel

from secondshift.domain.rules import RuleSpec
from secondshift.providers.base import (
    ImageRef,
    JudgeRequest,
    JudgeResponse,
    ProposeRequest,
    ProposeResponse,
)

SchemaT = TypeVar("SchemaT", bound=BaseModel)

# VERIFIED live 2026-10-28: POST /v1/chat/completions accepts OpenAI-style
# messages with image_url data-URI parts; usage block reports token counts.
# Measured image cost: ~1,200 prompt tokens for a 1280x720 keyframe.
BASE_URL = "https://api.meta.ai/v1"
CHAT_PATH = "/chat/completions"
MODEL_BY_ROLE = {"fast": "muse-spark-1.3", "deep": "muse-wonder-1.0"}


def image_part(image: ImageRef) -> dict[str, Any]:
    """Encode one image as a chat content part (data URI).

    VERIFIED live 2026-10-28: image_url parts with base64 data URIs are
    accepted by /v1/chat/completions.
    """
    data = Path(image.path).read_bytes()
    encoded = base64.b64encode(data).decode()
    return {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encoded}"}}


PRIMITIVES_TABLE = """object_present: needs target (noun phrase), optional area_hint - check-up + watch
object_absent: needs target + anchor (the visible thing it belongs to) - check-up + watch
object_state: needs target + target_state (open/closed/on/off...) - check-up + watch
state_for_duration: needs target + target_state + duration_min - watch only
zone_empty_for_duration: needs area_hint + duration_min - watch only
event_by_deadline: needs target + target_state + deadline_local (+ schedule) - watch only
camera_health: no target - watch only"""

COMPILER_VERSION_SPARK = "rule_compiler@v2:spark:muse-spark-1.3"


def build_chat_payload(
    prompt: str, images: list[ImageRef], model_role: Literal["fast", "deep"]
) -> dict[str, Any]:
    """Build the chat request body (verified shape, 2026-10-28).

    JSON output is requested in the prompt text; the API returned clean
    JSON in probes. response_format is not sent.
    """
    content: list[dict[str, Any]] = [{"type": "text", "text": prompt}]
    content.extend(image_part(image) for image in images)
    return {
        "model": MODEL_BY_ROLE[model_role],
        "messages": [{"role": "user", "content": content}],
        # TODO(API): some deployments want {"response_format": {"type": "json_object"}}
    }


def normalize_chat_content(payload: dict[str, Any]) -> str:
    """Extract the assistant text from a chat response payload.

    Best-known shape: choices[0].message.content (string, or a list of
    text parts). Raises ValueError on anything else - loudly, so the
    runbook step "fix the adapters" has a precise failure to fix.
    """
    choices = payload.get("choices") or []
    if not choices:
        raise ValueError(f"No choices in chat response: keys={list(payload)}")
    message = choices[0].get("message", {})
    content = message.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        texts = [
            part.get("text", "")
            for part in content
            if isinstance(part, dict) and part.get("type") == "text"
        ]
        if texts:
            return "".join(texts)
    raise ValueError(f"Unrecognized chat content shape: {type(content)}")


def extract_json(text: str) -> dict[str, Any]:
    """Parse the JSON object out of model text (tolerates code fences)."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        cleaned = cleaned.removeprefix("json").strip()
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("No JSON object in model output")
    parsed: dict[str, Any] = json.loads(cleaned[start : end + 1])
    return parsed


def _coerce_cannot_assess(raw: Any) -> dict[str, Any]:
    """CannotAssess coercion to the real schema {area, reason, detail}.

    Live behavior: the model sometimes returns bare item_id strings in
    cannot_assess. Map them honestly: area = the item named, reason =
    not_filmed (it could not be assessed from the footage), detail says
    the listing came from the model without elaboration.
    """
    if isinstance(raw, str):
        return {
            "area": raw,
            "reason": "not_filmed",
            "detail": "The model listed this as not assessable from the footage.",
        }
    out = dict(raw)
    out.setdefault("area", str(out.get("item_id", "unknown area")))
    if out.get("reason") not in (
        "not_filmed",
        "too_dark",
        "too_blurry",
        "occluded",
        "needs_measurement",
        "not_visible_by_design",
    ):
        out["reason"] = "not_filmed"
    out.setdefault("detail", "The model listed this as not assessable from the footage.")
    return out


def _coerce_proposal(raw: dict[str, Any]) -> dict[str, Any]:
    """Fill any fields the model omitted with honest neutral defaults.

    Live behavior (2026-10-28): Spark sometimes returns a proposal with
    only item_id + description. Dropping it would lose a real finding;
    inventing detail would be worse. Defaults: sam_prompts falls back to
    the description (SAM prompts on visible objects), confidence to a
    neutral 0.5, why_risky to the description text.
    """
    out = dict(raw)
    description = str(out.get("description", ""))
    out.setdefault("room", "unknown")
    out.setdefault("evidence_timestamps", [])
    if not out.get("sam_prompts"):
        out["sam_prompts"] = [description] if description else [str(out.get("item_id", "object"))]
    if out.get("confidence") is None:
        out["confidence"] = 0.5
    if not out.get("why_risky"):
        out["why_risky"] = description
    return out


class MetaVisionReasoner:
    """Real Muse Spark/Wonder client (Phase 7 plug-in)."""

    def __init__(self, api_key: str | None) -> None:
        self.api_key = api_key

    def _post_chat(self, payload: dict[str, Any]) -> dict[str, Any]:
        from secondshift.providers.meta.transport import post_json

        return post_json(CHAT_PATH, payload, explicit_key=self.api_key)

    def complete_json(
        self,
        prompt: str,
        images: list[ImageRef],
        schema: type[SchemaT],
        model_role: Literal["fast", "deep"],
    ) -> SchemaT:
        """One structured call: build, post, normalize, validate."""
        payload = build_chat_payload(
            prompt + f"\n\nRespond with JSON matching this schema: {schema.model_json_schema()}",
            images,
            model_role,
        )
        data = self._post_chat(payload)
        return schema.model_validate(extract_json(normalize_chat_content(data)))

    def propose_hazards(self, req: ProposeRequest) -> ProposeResponse:
        """Propose via the propose prompt; parse the JSON into dataclasses."""
        from secondshift.domain.hazards import HazardProposal as _HP
        from secondshift.providers.prompts import load_prompt

        prompt = load_prompt(
            "propose_hazards",
            checklist_items_yaml=req.pack_items_yaml,
            narration_facts=req.narration_facts,
            measurements=req.measurements,
            previous_findings_summary=req.previous_findings_summary,
            n_images=len(req.keyframes),
            json_schema=__import__("json").dumps(
                {
                    "type": "object",
                    "properties": {
                        "proposals": {"type": "array", "items": _HP.model_json_schema()},
                        "rooms_seen": {"type": "array", "items": {"type": "string"}},
                        "cannot_assess": {"type": "array", "items": {"type": "object"}},
                    },
                    "required": ["proposals", "rooms_seen", "cannot_assess"],
                }
            ),
        )
        images = [ImageRef(path=k.image_path, keyframe_id=k.id) for k in req.keyframes]
        data = self._post_chat(build_chat_payload(prompt, images, "fast"))
        parsed = extract_json(normalize_chat_content(data))
        from secondshift.domain.hazards import CannotAssess, HazardProposal

        return ProposeResponse(
            proposals=[
                HazardProposal.model_validate(_coerce_proposal(p))
                for p in parsed.get("proposals", [])
            ],
            rooms_seen=[str(r) for r in parsed.get("rooms_seen", [])],
            cannot_assess=[
                CannotAssess.model_validate(_coerce_cannot_assess(c))
                for c in parsed.get("cannot_assess", [])
            ],
        )

    def judge(self, req: JudgeRequest) -> JudgeResponse:
        """Judge one contested claim with Spark (pass 2: spec says the
        judge is the fast role; Wonder is reserved for the deep routine
        pass). Prompt text lives in prompts/verify_judge.md."""
        from secondshift.providers.prompts import load_prompt

        prompt = load_prompt("verify_judge", claim=req.claim, sam_summary=req.context)
        data = self._post_chat(build_chat_payload(prompt, req.images, "fast"))
        parsed = extract_json(normalize_chat_content(data))
        return JudgeResponse(
            verification=str(parsed.get("verification", "needs_human")),
            reason=str(parsed.get("reason", "")),
        )

    def compile_rule(self, text: str, mode_hint: str, precheck_flags: list[str]) -> RuleSpec:
        """Layer 2 of the rule compiler: Spark + prompts/rule_compiler.md.

        Pass 2 Phase D. The deterministic precheck (Layer 1) has already
        run; this call only compiles or honestly refuses/clarifies.
        compiler_version records the prompt version and the model ID.
        """
        from secondshift.providers.prompts import load_prompt

        prompt = load_prompt(
            "rule_compiler",
            primitives_table=PRIMITIVES_TABLE,
            text=text,
            mode_hint=mode_hint,
            precheck_flags=", ".join(precheck_flags) or "none",
            json_schema=RuleSpec.model_json_schema(),
        )
        data = self._post_chat(build_chat_payload(prompt, [], "fast"))
        parsed = extract_json(normalize_chat_content(data))
        parsed.setdefault("id", uuid.uuid4().hex)
        parsed.setdefault("original_text", text)
        parsed["compiler_version"] = COMPILER_VERSION_SPARK
        return RuleSpec.model_validate(parsed)
