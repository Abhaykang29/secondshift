"""SQLite call ledger (pass 2 Phase B) - the persistent cost record.

Why SQLite: the in-memory ledger reset on every restart, so the budget
guard and /api/costs lied across runs. This table is the single source
of truth for spend: the budget check SUMs it, so the cap survives
restarts. One row per provider call (cache hits included, cost 0).
Depends on: stdlib sqlite3 only.
"""

import sqlite3
import threading
from pathlib import Path
from typing import Any

_lock = threading.Lock()

SCHEMA = """
CREATE TABLE IF NOT EXISTS api_calls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    at TEXT NOT NULL,
    role TEXT NOT NULL,
    model TEXT NOT NULL,
    endpoint TEXT NOT NULL,
    est_cost REAL NOT NULL,
    actual_cost REAL NOT NULL,
    cache_hit INTEGER NOT NULL DEFAULT 0,
    latency_ms REAL NOT NULL DEFAULT 0,
    phase_tag TEXT NOT NULL DEFAULT 'app'
);
"""


def connect(db_path: str | Path) -> sqlite3.Connection:
    """Open (creating if needed) the ledger database."""
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), check_same_thread=False)
    conn.execute(SCHEMA)
    conn.commit()
    return conn


def insert(conn: sqlite3.Connection, row: dict[str, Any]) -> None:
    """Append one call row."""
    with _lock:
        conn.execute(
            "INSERT INTO api_calls (at, role, model, endpoint, est_cost,"
            " actual_cost, cache_hit, latency_ms, phase_tag)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                row["at"],
                row["role"],
                row["model"],
                row["endpoint"],
                float(row["est_cost"]),
                float(row["actual_cost"]),
                1 if row.get("cache_hit") else 0,
                float(row.get("latency_ms", 0.0)),
                row.get("phase_tag", "app"),
            ),
        )
        conn.commit()


def total(conn: sqlite3.Connection) -> float:
    """Total actual spend across all rows."""
    with _lock:
        cur = conn.execute("SELECT COALESCE(SUM(actual_cost), 0) FROM api_calls")
        return float(cur.fetchone()[0])


def totals_by(conn: sqlite3.Connection, field: str) -> dict[str, float]:
    """Actual spend grouped by a column (model or phase_tag)."""
    if field not in ("model", "phase_tag", "role", "endpoint"):
        raise ValueError(f"cannot group by {field}")
    with _lock:
        cur = conn.execute(
            f"SELECT {field}, COALESCE(SUM(actual_cost), 0) FROM api_calls GROUP BY {field}"
        )
        return {str(k): float(v) for k, v in cur.fetchall()}


def recent(conn: sqlite3.Connection, limit: int = 50) -> list[dict[str, Any]]:
    """Most recent call rows, newest first."""
    with _lock:
        cur = conn.execute(
            "SELECT at, role, model, endpoint, est_cost, actual_cost, cache_hit,"
            " latency_ms, phase_tag FROM api_calls ORDER BY id DESC LIMIT ?",
            (limit,),
        )
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, row, strict=True)) for row in cur.fetchall()]
