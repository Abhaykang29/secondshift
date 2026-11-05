"""Transient Meta API failures are retried instead of failing the scan."""

import io
import json
import urllib.request

import pytest
from secondshift.providers.meta import transport


class _Resp(io.BytesIO):
    def __enter__(self) -> "_Resp":
        return self

    def __exit__(self, *exc: object) -> None:
        return None


@pytest.mark.parametrize("error", [TimeoutError("read timed out"), ConnectionResetError("reset")])
def test_read_timeout_and_reset_are_retried(
    monkeypatch: pytest.MonkeyPatch, error: Exception
) -> None:
    calls = {"n": 0}

    def fake_urlopen(request: object, timeout: float) -> _Resp:
        calls["n"] += 1
        if calls["n"] < 3:
            raise error
        return _Resp(json.dumps({"ok": True}).encode())

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(transport._time, "sleep", lambda s: None)
    monkeypatch.setattr(transport, "auth_headers", lambda key: {})
    assert transport._raw_post("/x", {"model": "m"}, None, 1.0) == {"ok": True}
    assert calls["n"] == 3


def test_retry_after_header_is_honoured() -> None:
    assert transport._retry_wait(0, "7") == 7.0
    assert transport._retry_wait(10) <= 20.5
