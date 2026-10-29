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

import os
import sys
from pathlib import Path
from typing import Any

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


def post_json(
    path: str, body: dict[str, Any], explicit_key: str | None = None, timeout: float = 120.0
) -> dict[str, Any]:
    """POST JSON to the Meta API and return the parsed response body.

    Uses urllib on purpose: it honors the environment's egress-proxy
    variables (where the vault surrogate is swapped for the real key),
    while httpx's stricter parsing of this environment's NO_PROXY list
    (bare IPv6 entries) raises InvalidURL before any request is sent -
    observed live 2026-10-28.
    """
    import json
    import urllib.request

    request = urllib.request.Request(
        f"{BASE_URL}{path}",
        data=json.dumps(body).encode(),
        method="POST",
    )
    request.add_header("Content-Type", "application/json")
    for name, value in auth_headers(explicit_key).items():
        request.add_header(name, value)
    import urllib.error

    from secondshift.providers.cost import ProviderUnavailable

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data: dict[str, Any] = json.loads(response.read().decode())
            return data
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="replace")[:400]
        raise ProviderUnavailable(f"Meta API {path} returned HTTP {exc.code}: {detail}") from exc
