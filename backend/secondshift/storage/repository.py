"""Storage repository layer (SQLite, stdlib).

Phase 0: an in-memory placeholder repository so the API can be wired and
tested. Phase 1-2 replaces this with the SQLite implementation behind the
same interface - callers must not depend on the in-memory detail.
Depends on: domain models.
"""

from typing import Any


class Repository:
    """Minimal key-value repository placeholder (Phase 0)."""

    def __init__(self) -> None:
        self._store: dict[str, dict[str, Any]] = {}

    def put(self, kind: str, object_id: str, payload: dict[str, Any]) -> None:
        """Store one object by kind and id."""
        self._store[f"{kind}:{object_id}"] = payload

    def get(self, kind: str, object_id: str) -> dict[str, Any] | None:
        """Fetch one object by kind and id, or None."""
        return self._store.get(f"{kind}:{object_id}")

    def list(self, kind: str) -> list[dict[str, Any]]:
        """List all objects of a kind."""
        prefix = f"{kind}:"
        return [v for k, v in self._store.items() if k.startswith(prefix)]
