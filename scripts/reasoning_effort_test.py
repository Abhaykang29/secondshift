"""Reasoning-effort A/B (pass 2 follow-up, 2026-10-29).

Runs Appendix B through the LIVE compiler with reasoning_effort="low"
(the current code path for compile + judge) and reports status +
primitive accuracy and per-call latency from NEW ledger rows. The v2
baseline (no reasoning_effort) is in docs/LIVE_VERIFICATION.md:
status 38/40, primitives 15/16, ~5.6s/call wall average.
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))
import yaml  # noqa: E402
from secondshift.providers import ledger  # noqa: E402
from secondshift.providers.meta import transport  # noqa: E402
from secondshift.providers.meta.text_vision import MetaVisionReasoner  # noqa: E402
from secondshift.rules.compiler import compile_rule  # noqa: E402


def main() -> int:
    root = Path(__file__).parent.parent
    conn = ledger.connect(root / "data" / "costs.db")
    transport.configure(
        ledger_conn=conn,
        cache_mode="record",
        cache_dir=str(root / "data" / "verify-cache"),
        budget_usd=140.0,
        budget_override=False,
        phase_tag="pass2-re",
    )
    before = conn.execute("SELECT COALESCE(MAX(id), 0) FROM api_calls").fetchone()[0]
    vision = MetaVisionReasoner(None)
    entries = yaml.safe_load((root / "eval" / "rules" / "sentences.yaml").read_text())
    status_ok = prim_ok = prim_total = 0
    started = time.time()
    for entry in entries:
        spec = compile_rule(entry["text"], entry["mode_hint"], vision)
        if spec.status.value == entry["expected_status"]:
            status_ok += 1
        if entry["expected_status"] == "compiled":
            prim_total += 1
            if sorted(c.primitive.value for c in spec.conditions) == sorted(
                entry.get("expected_primitives", [])
            ):
                prim_ok += 1
    wall = time.time() - started
    rows = conn.execute(
        "SELECT latency_ms, actual_cost FROM api_calls WHERE id > ? AND cache_hit = 0",
        (before,),
    ).fetchall()
    lat = [r[0] / 1000 for r in rows]
    cost = sum(r[1] for r in rows)
    print(
        f"reasoning_effort=low on Appendix B: status {status_ok}/40, "
        f"primitives {prim_ok}/{prim_total}; live calls {len(rows)}, "
        f"latency mean {sum(lat) / len(lat):.2f}s p50 {sorted(lat)[len(lat) // 2]:.2f}s "
        f"max {max(lat):.2f}s; wall {wall:.0f}s; cost ${cost:.2f}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
