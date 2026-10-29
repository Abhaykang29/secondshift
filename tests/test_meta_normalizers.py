"""Phase 7 plug-in tests: the response normalizers against sample payloads
(best-known shapes from spec section 12 - every shape assumption is
TODO(API) in the adapters and gets re-verified when the key arrives)."""

import base64

import pytest
from secondshift.providers.meta.image_edit import normalize_image_response
from secondshift.providers.meta.segmentation import normalize_sam_response
from secondshift.providers.meta.speech import normalize_transcript
from secondshift.providers.meta.text_vision import (
    build_chat_payload,
    extract_json,
    normalize_chat_content,
)


def test_chat_content_string_and_parts_shapes() -> None:
    """Both the string-content and parts-list chat shapes normalize."""
    assert normalize_chat_content({"choices": [{"message": {"content": "hello"}}]}) == "hello"
    parts = {
        "choices": [
            {"message": {"content": [{"type": "text", "text": "a"}, {"type": "text", "text": "b"}]}}
        ]
    }
    assert normalize_chat_content(parts) == "ab"
    with pytest.raises(ValueError):
        normalize_chat_content({"unexpected": True})


def test_extract_json_tolerates_code_fences() -> None:
    """Structured output often arrives fenced; the parser handles it."""
    assert extract_json('```json\n{"ok": true}\n```') == {"ok": True}
    assert extract_json('prefix {"a": 1} suffix') == {"a": 1}


def test_chat_payload_uses_standard_tier_models_only() -> None:
    """Hard rule (spec 6): no *-contributor model id may ever be built."""
    payload = build_chat_payload("hi", [], "fast")
    assert payload["model"] == "muse-spark-1.3"
    assert "contributor" not in str(payload)


def test_sam_normalizer_polygon_and_flat_points() -> None:
    """Polygon list and flat points shapes both normalize to Masks."""
    payload = {
        "masks": [
            {
                "polygon": [[0.1, 0.2], [0.5, 0.2], [0.5, 0.6], [0.1, 0.6]],
                "score": 0.9,
                "label": "throw rug",
            },
            {
                "points": [0.0, 0.0, 1.0, 0.0, 1.0, 1.0, 0.0, 1.0],
                "confidence": 0.8,
                "bbox": [0.0, 0.0, 1.0, 1.0],
            },
        ]
    }
    masks = normalize_sam_response(payload, "kf-1")
    assert len(masks) == 2
    assert masks[0].prompt == "throw rug" and masks[0].bbox == (0.1, 0.2, 0.5, 0.6)
    assert masks[1].score == 0.8 and len(masks[1].polygon or []) == 4


def test_sam_normalizer_rejects_rle_loudly() -> None:
    """An RLE payload must fail loudly (runbook fix), never silently."""
    with pytest.raises(ValueError, match="RLE"):
        normalize_sam_response(
            {"masks": [{"segmentation": {"counts": "abc", "size": [10, 10]}}]}, "kf"
        )


def test_image_normalizer_b64() -> None:
    """b64_json entries decode to bytes."""
    raw = base64.b64encode(b"PNGDATA").decode()
    assert normalize_image_response({"data": [{"b64_json": raw}]}) == b"PNGDATA"


def test_transcript_normalizer_segment_families() -> None:
    """start/end and start/duration segment families both normalize."""
    payload = {
        "language": "en",
        "segments": [
            {"start": 1.0, "end": 3.5, "text": "hello"},
            {"start": 4.0, "duration": 2.0, "text": "world"},
        ],
    }
    segments = normalize_transcript(payload, capture_id="cap-1")
    assert [(s.t_start, s.t_end, s.text) for s in segments] == [
        (1.0, 3.5, "hello"),
        (4.0, 6.0, "world"),
    ]
    assert segments[0].capture_id == "cap-1"
    single = normalize_transcript({"text": "all of it", "duration": 9.0})
    assert single[0].t_end == 9.0


def test_sam_responses_fixture_parses_exact_box() -> None:
    """The REAL captured SAM /v1/responses shape parses to the exact box.

    Probe image (2026-10-28): a red rectangle drawn at pixels
    (500,200)-(800,600) in a 1280x720 frame; the live API returned
    exactly those coordinates.
    """
    import json
    from pathlib import Path

    from secondshift.providers.meta.segmentation import normalize_sam_responses

    payload = json.loads(
        (Path(__file__).parent / "fixtures" / "sam_responses_sample.json").read_text()
    )
    masks = normalize_sam_responses(payload, "kf-1", "red rectangle")
    assert len(masks) == 1
    assert masks[0].bbox == (500 / 1280, 200 / 720, 800 / 1280, 600 / 720)
    assert masks[0].prompt == "red rectangle"


def test_sam_responses_empty_text_means_no_mask() -> None:
    """No box segments in the output text = the object was not found."""
    from secondshift.providers.meta.segmentation import parse_sam_responses_text

    assert parse_sam_responses_text("", "kf-1", "elephant") == []
