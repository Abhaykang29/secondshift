"""Live view of a running scan (2026-10-29 smoke test).

Serves one page that polls /status.json every 2s: the newest job's
step states (from data/store.json) and the newest API calls (from the
SQLite ledger) with model, cost and latency, plus running totals.
Read-only; makes no model calls. Run: .venv/bin/python scripts/live_view_server.py [port]
"""

import json
import sqlite3
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

ROOT = Path(__file__).parent.parent

PAGE = """<!doctype html><html><head><meta charset="utf-8">
<title>SecondShift - live scan</title>
<style>body{font-family:system-ui;background:#0b0f14;color:#e6edf3;margin:24px}
h1{font-size:20px} .step{display:inline-block;padding:4px 10px;border-radius:12px;background:#1c2733;margin-right:6px}
.done{background:#14532d}.running{background:#7c2d12}.pending{opacity:.55}
table{border-collapse:collapse;margin-top:12px} td,th{padding:3px 10px;border-bottom:1px solid #22303f;text-align:left;font-size:13px}
.big{font-size:28px;font-weight:600}</style></head><body>
<h1>SecondShift - live scan of test_1.mp4</h1>
<div id="steps"></div>
<p><span class="big" id="calls">0</span> model calls &nbsp; <span class="big" id="cost">$0.00</span> spent this run &nbsp; latest: <span id="latest"></span></p>
<table><thead><tr><th>time (UTC)</th><th>role</th><th>model</th><th>cost</th><th>latency</th><th>cache</th></tr></thead>
<tbody id="rows"></tbody></table>
<script>
async function tick(){
  const s = await (await fetch('/status.json')).json();
  document.getElementById('steps').innerHTML = s.steps.map(x =>
    `<span class="step ${x.state}">${x.name}: ${x.state}</span>`).join('');
  document.getElementById('calls').textContent = s.call_count;
  document.getElementById('cost').textContent = '$' + s.spent.toFixed(4);
  document.getElementById('latest').textContent = s.latest || '-';
  document.getElementById('rows').innerHTML = s.calls.map(c =>
    `<tr><td>${c.at}</td><td>${c.role}</td><td>${c.model}</td><td>$${c.cost.toFixed(4)}</td><td>${(c.latency_ms/1000).toFixed(1)}s</td><td>${c.cache_hit ? 'hit' : ''}</td></tr>`).join('');
}
tick(); setInterval(tick, 2000);
</script></body></html>"""


def status() -> dict:
    steps: list[dict[str, str]] = []
    try:
        store = json.loads((ROOT / "data" / "store.json").read_text())
        jobs = {k: v for k, v in store.items() if k.startswith("job:")}
        if jobs:
            job = list(jobs.values())[-1]
            raw = job.get("steps", [])
            if isinstance(raw, dict):
                steps = [{"name": k, "state": str(v)} for k, v in raw.items()]
            elif isinstance(raw, list):
                steps = [
                    {"name": str(s.get("name", "?")), "state": str(s.get("status", "?"))}
                    for s in raw if isinstance(s, dict)
                ]
            steps.append({"name": "job", "state": str(job.get("status", "?"))})
    except Exception:
        pass
    calls: list[dict[str, object]] = []
    spent = 0.0
    try:
        conn = sqlite3.connect(ROOT / "data" / "costs.db")
        rows = conn.execute(
            "SELECT at, role, model, actual_cost, latency_ms, cache_hit FROM api_calls "
            "WHERE phase_tag = 'pass2-smoke' ORDER BY id DESC LIMIT 25"
        ).fetchall()
        total = conn.execute(
            "SELECT COUNT(*), COALESCE(SUM(actual_cost), 0) FROM api_calls WHERE phase_tag = 'pass2-smoke'"
        ).fetchone()
        spent = float(total[1])
        calls = [
            {"at": r[0][11:19], "role": r[1], "model": r[2], "cost": r[3],
             "latency_ms": r[4], "cache_hit": bool(r[5])}
            for r in rows
        ]
        conn.close()
    except Exception:
        pass
    return {
        "steps": steps,
        "calls": calls,
        "call_count": len(calls) if calls else 0,
        "spent": spent,
        "latest": f"{calls[0]['role']} / {calls[0]['model']}" if calls else "",
    }


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/status.json":
            body = json.dumps(status()).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
        else:
            body = PAGE.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args: object) -> None:
        pass


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8799
    HTTPServer(("127.0.0.1", port), Handler).serve_forever()
