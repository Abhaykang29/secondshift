"""Record/replay cache for provider calls (spec section 11.3).

Why: the demo must be deterministic and cost $0. Real runs are recorded;
demo mode replays them. A replay miss is an error, never a silent live call.
Key = sha256 of {provider, model, endpoint, request JSON, media hashes}.
Depends on: domain.enums.CacheMode.
"""

import hashlib
import json
from pathlib import Path
from typing import Any

from secondshift.domain.enums import CacheMode


class CacheMiss(Exception):
    """Raised in replay mode when no recording exists for a key."""


def cache_key(
    provider: str, model: str, endpoint: str, request: dict[str, Any], media_hashes: list[str]
) -> str:
    """Compute the deterministic cache key for one provider call."""
    payload = {
        "provider": provider,
        "model": model,
        "endpoint": endpoint,
        "request": request,
        "media_sha256": media_hashes,
    }
    raw = json.dumps(payload, sort_keys=True, default=str).encode()
    return hashlib.sha256(raw).hexdigest()


def hash_bytes(data: bytes) -> str:
    """sha256 hex digest of raw media bytes."""
    return hashlib.sha256(data).hexdigest()


class RecordReplayCache:
    """File-backed record/replay cache rooted at a directory."""

    def __init__(self, root: str | Path, mode: CacheMode) -> None:
        self.root = Path(root)
        self.mode = mode

    def _path(self, key: str) -> Path:
        return self.root / f"{key}.json"

    def get(self, key: str) -> dict[str, Any] | None:
        """Return a cached response, or None (raise CacheMiss in replay)."""
        if self.mode is CacheMode.OFF:
            return None
        path = self._path(key)
        if path.exists():
            data: dict[str, Any] = json.loads(path.read_text())
            return data
        if self.mode is CacheMode.REPLAY:
            raise CacheMiss(f"No recording for key {key} (replay mode never calls live).")
        return None

    def put(self, key: str, response: dict[str, Any], model: str) -> None:
        """Store a response (no-op unless mode records: record/auto)."""
        if self.mode not in (CacheMode.RECORD, CacheMode.AUTO):
            return
        self.root.mkdir(parents=True, exist_ok=True)
        payload = {"model": model, "response": response}
        self._path(key).write_text(json.dumps(payload, indent=2, default=str))

    def should_call_live(self, key: str) -> bool:
        """Whether a miss for this key may go to the real provider."""
        if self.mode in (CacheMode.RECORD, CacheMode.AUTO, CacheMode.OFF):
            return True
        return False
