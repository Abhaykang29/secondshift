"""Storage repository layer (spec section 7: SQLite stdlib planned).

Phase 1 implementation: a JSON-file-backed repository with the same
put/get/list interface the Phase 0 placeholder fixed, so API and pipeline
code survive restarts and never depend on the storage detail. The SQLite
swap stays behind this interface if scale ever demands it.
Depends on: stdlib only.
"""

import json
from pathlib import Path
from typing import Any


class Repository:
    """Key-value repository, optionally persisted to one JSON file."""

    def __init__(self, path: str | Path | None = None) -> None:
        self._path = Path(path) if path else None
        self._store: dict[str, dict[str, Any]] = {}
        if self._path and self._path.exists():
            self._store = json.loads(self._path.read_text())

    def _save(self) -> None:
        if self._path:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._path.write_text(json.dumps(self._store, default=str))

    def put(self, kind: str, object_id: str, payload: dict[str, Any]) -> None:
        """Store one object by kind and id."""
        self._store[f"{kind}:{object_id}"] = payload
        self._save()

    def get(self, kind: str, object_id: str) -> dict[str, Any] | None:
        """Fetch one object by kind and id, or None."""
        return self._store.get(f"{kind}:{object_id}")

    def list(self, kind: str) -> list[dict[str, Any]]:
        """List all objects of a kind."""
        prefix = f"{kind}:"
        return [v for k, v in self._store.items() if k.startswith(prefix)]

    def delete(self, kind: str, object_id: str) -> bool:
        """Delete one object by kind and id. Returns True if it existed."""
        key = f"{kind}:{object_id}"
        if key not in self._store:
            return False
        del self._store[key]
        self._save()
        return True

    def delete_all(self) -> None:
        """Delete everything (the Settings 'Delete everything' button)."""
        self._store = {}
        self._save()
