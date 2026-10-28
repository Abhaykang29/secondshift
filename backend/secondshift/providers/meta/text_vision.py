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
from pathlib import Path
from typing import Any, Literal, TypeVar

from pydantic import BaseModel

from secondshift.providers.base import (
    ImageRef,
    JudgeRequest,
    JudgeResponse,
    ProposeRequest,
    ProposeResponse,
)
from secondshift.providers.cost import ProviderUnavailable

SchemaT = TypeVar("SchemaT", bound=BaseModel)

# TODO(API): confirm the real base URL + chat path against dev.meta.ai docs.
BASE_URL = "https://api.meta.ai/v1"  # TODO(API)
CHAT_PATH = "/chat/completions"  # TODO(API)
MODEL_BY_ROLE = {"fast": "muse-spark-1.3", "deep": "muse-wonder-1.0"}


def _require(api_key: str | None) -> str:
    if not api_key:
        raise ProviderUnavailable(
            "META_API_KEY is not set - the Meta adapters stay off until Phase 7 keys arrive."
        )
    return api_key


def image_part(image: ImageRef) -> dict[str, Any]:
    """Encode one image as a chat content part (data URI).

    TODO(API): confirm the expected field name (image_url vs image) and
    whether base64 data URIs are accepted vs uploaded file ids.
    """
    data = Path(image.path).read_bytes()
    encoded = base64.b64encode(data).decode()
    return {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encoded}"}}


def build_chat_payload(
    prompt: str, images: list[ImageRef], model_role: Literal["fast", "deep"]
) -> dict[str, Any]:
    """Build the chat request body. TODO(API): response_format for JSON mode."""
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


class MetaVisionReasoner:
    """Real Muse Spark/Wonder client (Phase 7 plug-in)."""

    def __init__(self, api_key: str | None) -> None:
        self.api_key = api_key

    def _post_chat(self, payload: dict[str, Any]) -> dict[str, Any]:
        import httpx

        key = _require(self.api_key)
        response = httpx.post(
            f"{BASE_URL}{CHAT_PATH}",
            json=payload,
            headers={"Authorization": f"Bearer {key}"},  # TODO(API): auth header
            timeout=120.0,
        )
        response.raise_for_status()
        data: dict[str, Any] = response.json()
        return data

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
        prompt = (
            "You are the hazard proposer for a home-safety check-up. Use ONLY item_ids "
            f"from this pack list:\n{req.pack_items_yaml}\n"
            f"Narration facts: {req.narration_facts}\nMeasurements: {req.measurements}\n"
            f"Already found: {req.previous_findings_summary}\n"
            "Respond with JSON: {\"proposals\": [...], \"rooms_seen\": [...], "
            "\"cannot_assess\": []} where each proposal matches the HazardProposal schema."
        )
        images = [ImageRef(path=k.image_path, keyframe_id=k.id) for k in req.keyframes]
        data = self._post_chat(build_chat_payload(prompt, images, "fast"))
        parsed = extract_json(normalize_chat_content(data))
        from secondshift.domain.hazards import CannotAssess, HazardProposal

        return ProposeResponse(
            proposals=[HazardProposal.model_validate(p) for p in parsed.get("proposals", [])],
            rooms_seen=[str(r) for r in parsed.get("rooms_seen", [])],
            cannot_assess=[CannotAssess.model_validate(c) for c in parsed.get("cannot_assess", [])],
        )

    def judge(self, req: JudgeRequest) -> JudgeResponse:
        """Judge one contested claim (deep model)."""
        prompt = (f"Claim: {req.claim}\nContext: {req.context}\n"
                  "Decide the verification: confirmed, needs_human, or rejected. "
                  "Respond with JSON: {\"verification\": ..., \"reason\": ...}")
        data = self._post_chat(build_chat_payload(prompt, req.images, "deep"))
        parsed = extract_json(normalize_chat_content(data))
        return JudgeResponse(
            verification=str(parsed.get("verification", "needs_human")),
            reason=str(parsed.get("reason", "")),
        )
