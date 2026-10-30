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
    prompt: str,
    images: list[ImageRef],
    model_role: Literal["fast", "deep"],
    reasoning_effort: str | None = None,
) -> dict[str, Any]:
    """Build the chat request body (verified shape, 2026-10-28).

    JSON output is requested in the prompt text; the API returned clean
    JSON in probes. response_format is not sent. reasoning_effort is
    sent only when set (compile + judge use "low" - measured in the
    pass-2 reasoning test, see docs/LIVE_VERIFICATION.md).
    """
    content: list[dict[str, Any]] = [{"type": "text", "text": prompt}]
    content.extend(image_part(image) for image in images)
    payload: dict[str, Any] = {
        "model": MODEL_BY_ROLE[model_role],
        "messages": [{"role": "user", "content": content}],
        # TODO(API): some deployments want {"response_format": {"type": "json_object"}}
    }
    if reasoning_effort:
        payload["reasoning_effort"] = reasoning_effort
    return payload


def build_propose_payload(
    prompt: str,
    keyframes: list[Any],
    model_role: Literal["fast", "deep"],
) -> dict[str, Any]:
    """Build a propose payload with every image explicitly labeled.

    The propose prompt has always told the model that images are
    labeled with their timestamps; the old payload never actually sent
    labels, so the model guessed (and guessed t=0, 1, 2...). Each image
    now carries a text part with its keyframe id and real timestamp in
    seconds, immediately before the image itself.
    """
    content: list[dict[str, Any]] = [{"type": "text", "text": prompt}]
    total = len(keyframes)
    for idx, keyframe in enumerate(keyframes):
        content.append(
            {
                "type": "text",
                "text": (
                    # DECISIONS D11: index + timestamp only - keyframe
                    # ids are random per capture, so including one
                    # changed the cache key without changing anything
                    # the answer depends on, defeating warm re-checks.
                    f"Image {idx + 1} of {total}: "
                    f"timestamp_seconds={keyframe.t:g}"
                ),
            }
        )
        content.append(image_part(ImageRef(path=keyframe.image_path, keyframe_id=keyframe.id)))
    return {
        "model": MODEL_BY_ROLE[model_role],
        # Propose stability (2026-10-30): temperature 0 is accepted by
        # the API (probed live, HTTP 200) and costs nothing extra -
        # preferred over running propose twice and merging.
        "temperature": 0,
        "messages": [{"role": "user", "content": content}],
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
    raw_reason = out.get("reason")
    if raw_reason not in (
        "not_filmed",
        "too_dark",
        "too_blurry",
        "occluded",
        "needs_measurement",
        "not_visible_by_design",
    ):
        # A free-text reason is the model's detail, not a schema reason.
        if isinstance(raw_reason, str) and raw_reason.strip() and "detail" not in out:
            out["detail"] = raw_reason.strip()
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
                        "keyframe_rooms": {"type": "array", "items": {"type": "string"}},
                        "cannot_assess": {"type": "array", "items": {"type": "object"}},
                    },
                    "required": ["proposals", "rooms_seen", "cannot_assess"],
                }
            ),
        )
        data = self._post_chat(build_propose_payload(prompt, req.keyframes, "fast"))
        parsed = extract_json(normalize_chat_content(data))
        from secondshift.domain.hazards import CannotAssess, HazardProposal

        keyframe_rooms = parsed.get("keyframe_rooms") or parsed.get("rooms_by_image_index") or []
        return ProposeResponse(
            proposals=[
                HazardProposal.model_validate(_coerce_proposal(p))
                for p in parsed.get("proposals", [])
            ],
            rooms_seen=[str(r) for r in parsed.get("rooms_seen", [])],
            keyframe_rooms=[str(r) for r in keyframe_rooms],
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
        data = self._post_chat(
            build_chat_payload(prompt, req.images, "fast", reasoning_effort="low")
        )
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
        data = self._post_chat(build_chat_payload(prompt, [], "fast", reasoning_effort="low"))
        parsed = extract_json(normalize_chat_content(data))
        parsed.setdefault("id", uuid.uuid4().hex)
        parsed.setdefault("original_text", text)
        parsed["compiler_version"] = COMPILER_VERSION_SPARK
        return RuleSpec.model_validate(parsed)

    # --- Pass 2 Phase E/G prompt-backed methods. Each returns None on
    # any parse problem so pipelines fall back to deterministic paths.
    def plan_fix(
        self,
        hazard_title: str,
        description: str,
        fixes: list[dict[str, str]],
        language: str,
    ) -> dict[str, Any] | None:
        """Spark picks a fix FROM THE LIBRARY (prompts/fix_plan.md)."""
        import json as _json

        from secondshift.providers.prompts import load_prompt

        prompt = load_prompt(
            "fix_plan",
            hazard=f"{hazard_title}: {description}",
            home_context="",
            fix_library=_json.dumps(fixes),
            language=language,
        )
        try:
            data = self._post_chat(build_chat_payload(prompt, [], "fast"))
            parsed = extract_json(normalize_chat_content(data))
        except Exception:
            return None
        return parsed if isinstance(parsed, dict) else None

    def summarize_report(self, report_json: str, language: str) -> str | None:
        """Spark writes the 2-3 sentence summary (prompts/report_summary.md)."""
        from secondshift.providers.prompts import load_prompt

        prompt = load_prompt("report_summary", report_json=report_json, language=language)
        try:
            data = self._post_chat(build_chat_payload(prompt, [], "fast"))
            parsed = extract_json(normalize_chat_content(data))
            summary = str(parsed.get("summary", "")).strip()
        except Exception:
            return None
        return summary or None

    def judge_recheck(
        self, hazard_title: str, before: ImageRef | None, after: ImageRef | None
    ) -> dict[str, Any] | None:
        """Judge a contested re-check item (prompts/recheck_judge.md)."""
        from secondshift.providers.prompts import load_prompt

        prompt = load_prompt("recheck_judge", hazard=hazard_title)
        images = [img for img in (before, after) if img is not None]
        try:
            data = self._post_chat(build_chat_payload(prompt, images, "fast"))
            parsed = extract_json(normalize_chat_content(data))
        except Exception:
            return None
        return parsed if isinstance(parsed, dict) else None

    def plan_edit(self, image: ImageRef, instruction: str) -> str | None:
        """Rewrite a viz instruction against the actual photo
        (prompts/edit_instruction.md): names the existing surface the
        change belongs on, or phrases a move-out-of-frame as a removal.
        Returns None on any failure - the caller keeps the pack's
        original instruction (2026-10-30 edits experiment)."""
        from secondshift.providers.prompts import load_prompt

        prompt = load_prompt("edit_instruction", instruction=instruction)
        try:
            data = self._post_chat(build_chat_payload(prompt, [image], "fast"))
            parsed = extract_json(normalize_chat_content(data))
        except Exception:
            return None
        rewritten = str(parsed.get("instruction") or "").strip()
        return rewritten or None

    def routine_insights(self, computed_numbers: str) -> list[dict[str, Any]] | None:
        """Wonder writes routine summaries from geometry (prompts/routine_insights.md)."""

        from secondshift.providers.prompts import load_prompt

        prompt = load_prompt(
            "routine_insights",
            computed_numbers=computed_numbers,
            json_schema={"type": "array", "items": {"type": "object"}},
        )
        try:
            data = self._post_chat(build_chat_payload(prompt, [], "deep"))
            parsed = extract_json(normalize_chat_content(data))
        except Exception:
            return None
        items = parsed.get("insights", parsed) if isinstance(parsed, dict) else parsed
        return items if isinstance(items, list) else None

    def classify_room(self, image: ImageRef) -> dict[str, Any] | None:
        """Classify the room for the Watch guard (prompts/room_type.md)."""
        from secondshift.providers.prompts import load_prompt

        prompt = load_prompt("room_type")
        try:
            data = self._post_chat(build_chat_payload(prompt, [image], "fast"))
            parsed = extract_json(normalize_chat_content(data))
        except Exception:
            return None
        return parsed if isinstance(parsed, dict) else None

    def judge_state(self, target: str, question: str, image: ImageRef) -> str | None:
        """Judge one object's visible state (prompts/watch_state.md)."""
        from secondshift.providers.prompts import load_prompt

        prompt = load_prompt("watch_state", target=target, question=question)
        try:
            data = self._post_chat(
                build_chat_payload(prompt, [image], "fast", reasoning_effort="low")
            )
            parsed = extract_json(normalize_chat_content(data))
            state = str(parsed.get("state", "")).strip()
        except Exception:
            return None
        return state or None
