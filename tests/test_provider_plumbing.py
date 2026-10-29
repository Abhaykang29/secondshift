"""Pass 2 Phase B tests: ledger persistence, transport cache/cost, prompts."""

import sqlite3

import pytest
from secondshift.providers import ledger
from secondshift.providers.meta import transport


def _conn(tmp_path) -> sqlite3.Connection:  # type: ignore[no-untyped-def]
    return ledger.connect(tmp_path / "costs.db")


def test_ledger_survives_restart(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """Rows written by one connection are summed by a fresh connection."""
    conn = _conn(tmp_path)
    ledger.insert(
        conn,
        {
            "at": "2026-10-28T00:00:00Z",
            "role": "vision",
            "model": "muse-spark-1.3",
            "endpoint": "/chat/completions",
            "est_cost": 0.01,
            "actual_cost": 0.009,
            "cache_hit": False,
            "latency_ms": 5,
            "phase_tag": "pass2",
        },
    )
    reopened = _conn(tmp_path)
    assert ledger.total(reopened) == pytest.approx(0.009)
    assert ledger.totals_by(reopened, "phase_tag") == {"pass2": pytest.approx(0.009)}


def test_actual_cost_from_usage_payloads() -> None:
    """Actual cost is computed from real usage shapes (saved payloads)."""
    chat = {"usage": {"prompt_tokens": 1200, "completion_tokens": 500}}
    assert transport.actual_cost(
        "/chat/completions", {"model": "muse-spark-1.3"}, chat
    ) == pytest.approx(1200 / 1e6 * 1.25 + 500 / 1e6 * 4.25)
    sam = {"usage": {"images_processed": 3}}
    assert transport.actual_cost("/responses", {"model": "sam-3.1"}, sam) == pytest.approx(
        3 * 0.0025
    )


def test_second_identical_call_is_free_and_offline(tmp_path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """Record mode: the replay of an identical request costs $0, 0 calls."""
    calls = {"n": 0}

    def fake_raw(path, body, key, timeout):  # type: ignore[no-untyped-def]
        calls["n"] += 1
        return {"usage": {"prompt_tokens": 10, "completion_tokens": 5}, "ok": True}

    monkeypatch.setattr(transport, "_raw_post", fake_raw)
    monkeypatch.setattr(transport, "_throttle", lambda model: None)
    transport.configure(
        ledger_conn=_conn(tmp_path),
        cache_mode="record",
        cache_dir=str(tmp_path / "cache"),
        budget_usd=140.0,
        budget_override=False,
        phase_tag="pass2",
    )
    body = {"model": "muse-spark-1.3", "messages": [{"role": "user", "content": "hi"}]}
    first = transport.post_json("/chat/completions", body)
    second = transport.post_json("/chat/completions", body)
    assert first == second
    assert calls["n"] == 1  # the second call never touched the network
    rows = ledger.recent(transport._config["ledger"], 10)  # noqa: SLF001
    assert rows[0]["cache_hit"] == 1 and rows[0]["actual_cost"] == 0.0
    transport._config.clear()  # noqa: SLF001


def test_replay_mode_miss_raises_cache_miss(tmp_path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """Replay with an empty cache fails loudly, never silently live."""
    transport.configure(
        ledger_conn=_conn(tmp_path),
        cache_mode="replay",
        cache_dir=str(tmp_path / "empty"),
        budget_usd=140.0,
        budget_override=False,
        phase_tag="pass2",
    )
    with pytest.raises(transport.CacheMiss):
        transport.post_json("/chat/completions", {"model": "muse-spark-1.3"})
    transport._config.clear()  # noqa: SLF001


def test_prompt_files_are_used_and_no_long_inline_prompts() -> None:
    """Every live prompt loads from prompts/*.md; no >200-char prompts in code.

    Files wired in later phases are enumerated explicitly (never hidden).
    """
    import re
    from pathlib import Path

    from secondshift.providers.prompts import prompt_names

    backend = Path(__file__).parent.parent / "backend" / "secondshift"
    used = set()
    long_literals: list[str] = []
    for py in backend.rglob("*.py"):
        text = py.read_text()
        for match in re.finditer(r'load_prompt\(\s*"([a-z_]+)"', text):
            used.add(match.group(1))
        if "prompts" not in py.parts:
            for literal in re.finditer(r'"""(.*?)"""', text, re.DOTALL):
                if len(literal.group(1)) > 200 and "You are" in literal.group(1):
                    long_literals.append(f"{py.name}: {literal.group(1)[:40]}")
    pending = {  # wired in their phases - tracked, not forgotten
        "rule_compiler": "D",
        "routine_insights": "E",
        "fix_plan": "E",
        "report_summary": "E",
        "recheck_judge": "E",
        "room_type": "G",
        "narration_facts": "H",
        "ask_answer": "H",
        "watch_state": "G",
    }
    assert set(prompt_names()) - used - set(pending) == set()
    assert long_literals == []
