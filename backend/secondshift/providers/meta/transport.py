"""Auth + HTTP transport for the Meta Model API (Phase 7, verified live).

VERIFIED 2026-10-28 against dev.meta.ai's Meta Model API:
- Base URL https://api.meta.ai/v1, Bearer auth.
- GET /v1/models lists muse-spark-1.3, muse-wonder-1.0, sam-3.1,
  muse-image-1.0, muse-voice-transcribe-1.0 (plus contributor variants
  this app must never call).

Credential resolution, in order:
1. META_API_KEY from the environment / .env (real deployments).
2. The Muse vault surrogate for the custom.meta-ai connector: the
   surrogate (an hsurr: token, NOT the real key) is fetched from the
   local authd via dynamic_credentials and sent as the Bearer value;
   the runtime swaps it for the real key on egress to api.meta.ai.
   The real key never enters this process.

Depends on: stdlib urllib; optionally the custom-connector
dynamic_credentials helper (path overridable via SECONDSHIFT_CRED_BIN).
"""

import hashlib
import json as _json
import os
import random
import sqlite3
import sys
import time as _time
from datetime import UTC as _UTC
from datetime import datetime as _datetime
from pathlib import Path
from typing import Any

from secondshift.config import PRICE_TABLE
from secondshift.providers import ledger as _ledger

BASE_URL = "https://api.meta.ai/v1"
ALLOWED_HOST = "api.meta.ai"
CONNECTOR_NAME = "custom.meta-ai"
DEFAULT_CRED_BIN = "/opt/muse/skills/custom-connector-setup/bin"

_surrogate_cache: str | None = None


def _surrogate() -> str | None:
    """Fetch (once) the vault surrogate for custom.meta-ai, if available."""
    global _surrogate_cache
    if _surrogate_cache:
        return _surrogate_cache
    cred_bin = os.environ.get("SECONDSHIFT_CRED_BIN", DEFAULT_CRED_BIN)
    if not Path(cred_bin, "dynamic_credentials.py").exists():
        return None
    try:
        sys.path.insert(0, cred_bin)
        from dynamic_credentials import dynamic_credential_entry  # type: ignore[import-not-found]

        entry = dynamic_credential_entry(CONNECTOR_NAME)
        _surrogate_cache = str(entry["surrogate"]).strip()
        return _surrogate_cache
    except Exception:
        return None


def auth_headers(explicit_key: str | None = None) -> dict[str, str]:
    """Authorization header from explicit key, env key, or vault surrogate."""
    from secondshift.providers.cost import ProviderUnavailable

    key = explicit_key or os.environ.get("META_API_KEY") or _surrogate()
    if not key:
        raise ProviderUnavailable(
            "No Meta credential: set META_API_KEY or connect the "
            "custom.meta-ai connector (vault surrogate)."
        )
    return {"Authorization": f"Bearer {key}"}


# ---------------------------------------------------------------------------
# Pass 2 Phase B: cache + cost guard + retries around every live call.
# configure() is called once by providers.registry.build_providers; when
# unconfigured (smoke scripts), post_json is a plain authenticated POST.
# ---------------------------------------------------------------------------
_config: dict[str, Any] = {}
_last_call_at: dict[str, float] = {}


def configure(
    *,
    ledger_conn: sqlite3.Connection | None,
    cache_mode: str,
    cache_dir: str,
    budget_usd: float,
    budget_override: bool,
    phase_tag: str,
    image_tokens_estimate: int = 1200,
) -> None:
    """Install the ledger/cache/budget wiring for live calls."""
    _config.update(
        ledger=ledger_conn,
        cache_mode=cache_mode,
        cache_dir=cache_dir,
        budget_usd=budget_usd,
        budget_override=budget_override,
        phase_tag=phase_tag,
        image_tokens_estimate=image_tokens_estimate,
    )


class CacheMiss(Exception):
    """Raised in replay mode when a call was never recorded."""


def _hash_images(node: Any) -> Any:
    """Replace base64 image payloads with their sha256 (spec 11.3 keying)."""
    if isinstance(node, dict):
        return {k: _hash_images(v) for k, v in node.items()}
    if isinstance(node, list):
        return [_hash_images(v) for v in node]
    if isinstance(node, str) and node.startswith("data:") and ";base64," in node:
        raw = node.split(";base64,", 1)[1]
        try:
            digest = hashlib.sha256(__import__("base64").b64decode(raw)).hexdigest()
        except Exception:
            digest = hashlib.sha256(raw.encode()).hexdigest()
        return f"data:sha256:{digest}"
    return node


def request_key(path: str, body: dict[str, Any]) -> str:
    """Cache key: provider + model + endpoint + normalized request."""
    material = _json.dumps(
        {"endpoint": path, "model": body.get("model"), "body": _hash_images(body)},
        sort_keys=True,
    )
    return hashlib.sha256(material.encode()).hexdigest()


def _cache_path(key: str) -> Path:
    return Path(str(_config["cache_dir"])) / "meta-cache" / f"{key}.json"


def _role_for(path: str) -> str:
    if path.startswith("/chat"):
        return "vision"
    if path.startswith("/responses"):
        return "segmenter"
    if path.startswith("/images"):
        return "image_editor"
    if path.startswith("/audio"):
        return "transcriber"
    return "vision"


def estimate_cost(path: str, body: dict[str, Any]) -> float:
    """Pre-call estimate from the price table (documented approximations)."""
    model = str(body.get("model", ""))
    prices = PRICE_TABLE.get(model, {})
    if path.startswith("/responses"):
        return float(prices.get("per_image", 0.0025))
    if path.startswith("/images"):
        return float(prices.get("per_image", 0.01))
    text = _json.dumps(_hash_images(body))
    n_images = text.count("data:sha256:")
    in_tokens = n_images * int(_config.get("image_tokens_estimate", 1200)) + len(text) // 4
    out_tokens = 1500
    return in_tokens / 1_000_000 * float(
        prices.get("input_per_m", 1.25)
    ) + out_tokens / 1_000_000 * float(prices.get("output_per_m", 4.25))


def actual_cost(path: str, body: dict[str, Any], payload: dict[str, Any]) -> float:
    """Actual cost from the response usage block (spec Phase B.3)."""
    model = str(body.get("model", ""))
    prices = PRICE_TABLE.get(model, {})
    usage = payload.get("usage") or {}
    if path.startswith("/responses"):
        return float(usage.get("images_processed", 1)) * float(prices.get("per_image", 0.0025))
    if path.startswith("/images"):
        return len(payload.get("data") or [1]) * float(prices.get("per_image", 0.01))
    prompt_tokens = float(usage.get("prompt_tokens", usage.get("input_tokens", 0)))
    completion_tokens = float(usage.get("completion_tokens", usage.get("output_tokens", 0)))
    return prompt_tokens / 1_000_000 * float(
        prices.get("input_per_m", 1.25)
    ) + completion_tokens / 1_000_000 * float(prices.get("output_per_m", 4.25))


def _record(
    path: str, body: dict[str, Any], est: float, actual: float, cache_hit: bool, latency_ms: float
) -> None:
    conn = _config.get("ledger")
    if conn is None:
        return
    _ledger.insert(
        conn,
        {
            "at": _datetime.now(_UTC).isoformat(),
            "role": _role_for(path),
            "model": str(body.get("model", "")),
            "endpoint": path,
            "est_cost": est,
            "actual_cost": actual,
            "cache_hit": cache_hit,
            "latency_ms": latency_ms,
            "phase_tag": str(_config.get("phase_tag", "app")),
        },
    )


def _throttle(model: str) -> None:
    """Per-model client-side rate limit (min 0.2s between calls)."""
    now = _time.monotonic()
    wait = 0.2 - (now - _last_call_at.get(model, 0.0))
    if wait > 0:
        _time.sleep(wait)
    _last_call_at[model] = _time.monotonic()


def _raw_post(
    path: str, body: dict[str, Any], explicit_key: str | None, timeout: float
) -> dict[str, Any]:
    """One authenticated POST with retries on 429/5xx (max 3, backoff)."""
    import urllib.error
    import urllib.request

    from secondshift.providers.cost import ProviderUnavailable

    data = _json.dumps(body).encode()
    last_exc: Exception | None = None
    for attempt in range(4):
        request = urllib.request.Request(f"{BASE_URL}{path}", data=data, method="POST")
        request.add_header("Content-Type", "application/json")
        for name, value in auth_headers(explicit_key).items():
            request.add_header(name, value)
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                parsed: dict[str, Any] = _json.loads(response.read().decode())
                return parsed
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode(errors="replace")[:300]
            if exc.code == 429 or exc.code >= 500:
                last_exc = ProviderUnavailable(f"Meta API {path} HTTP {exc.code}: {detail}")
                _time.sleep(0.5 * (2**attempt) + random.uniform(0, 0.25))
                continue
            raise ProviderUnavailable(
                f"Meta API {path} returned HTTP {exc.code}: {detail}"
            ) from exc
        except urllib.error.URLError as exc:
            last_exc = exc
            _time.sleep(0.5 * (2**attempt) + random.uniform(0, 0.25))
    raise ProviderUnavailable(f"Meta API {path} failed after retries: {last_exc}")


def post_json(
    path: str, body: dict[str, Any], explicit_key: str | None = None, timeout: float = 120.0
) -> dict[str, Any]:
    """POST JSON to the Meta API through cache + cost guard + retries.

    Order (pass 2 Phase B): replay/record cache lookup -> budget check
    on the estimate -> throttled raw POST with retries -> actual cost
    from the usage block -> ledger row -> cache store.
    """
    if not _config:
        return _raw_post(path, body, explicit_key, timeout)
    from secondshift.providers.cost import BudgetExceeded

    mode = str(_config.get("cache_mode", "off"))
    key = request_key(path, body)
    est = estimate_cost(path, body)
    if mode in ("record", "replay"):
        cached = _cache_path(key)
        if cached.exists():
            payload: dict[str, Any] = _json.loads(cached.read_text())
            _record(path, body, est, 0.0, True, 0.0)
            return payload
        if mode == "replay":
            raise CacheMiss(
                f"No recorded response for {path} (key {key[:12]}...) - "
                "this demo step was not recorded."
            )
    conn = _config.get("ledger")
    if conn is not None and not _config.get("budget_override"):
        if _ledger.total(conn) + est > float(_config.get("budget_usd", 140.0)):
            raise BudgetExceeded(
                f"Budget cap reached: ledger total + estimate exceeds "
                f"${float(_config.get('budget_usd', 140.0)):.2f}."
            )
    _throttle(str(body.get("model", "")))
    started = _time.monotonic()
    payload = _raw_post(path, body, explicit_key, timeout)
    latency_ms = (_time.monotonic() - started) * 1000
    actual = actual_cost(path, body, payload)
    _record(path, body, est, actual, False, latency_ms)
    if mode == "record":
        target = _cache_path(key)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(_json.dumps(payload))
    return payload
