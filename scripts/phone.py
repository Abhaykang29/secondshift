"""make phone - put the full app on a phone, judge-style.

Builds the frontend, serves it FROM the backend on one HTTPS origin
(https://<LAN-IP>:8000), generates a self-signed cert whose SAN
includes this machine's current LAN IP, and prints the URL plus a
terminal QR code. With --tunnel (make phone TUNNEL=1) it also opens
a Cloudflare quick tunnel for networks with client isolation.

The Meta API key is read by the backend only (env / .env on this
machine); it is never sent to the browser. With no key configured
the app runs in demo mode and the on-screen banner says so.

Stop everything with Ctrl+C.
"""

import argparse
import os
import re
import shutil
import socket
import subprocess
import sys
import threading
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CERT_DIR = ROOT / ".local" / "certs"
PORT = 8000


def lan_ip() -> str:
    """This machine's primary LAN address (no packets are sent)."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            return str(sock.getsockname()[0])
    except OSError:
        out = subprocess.run(
            ["hostname", "-I"], capture_output=True, text=True, check=False
        ).stdout.split()
        for token in out:
            if token.count(".") == 3 and not token.startswith("127."):
                return token
    return "127.0.0.1"


def key_configured() -> bool:
    """True when a Meta key is in the environment or the repo .env -
    the value itself is never read into this process's output."""
    if os.environ.get("META_API_KEY"):
        return True
    env_file = ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text(errors="ignore").splitlines():
            if line.startswith("META_API_KEY=") and line.split("=", 1)[1].strip():
                return True
    return False


def build_frontend() -> None:
    print("Building the frontend (npm run build) ...")
    result = subprocess.run(
        ["npm", "run", "build"], cwd=ROOT / "frontend", check=False
    )
    if result.returncode != 0 or not (ROOT / "frontend" / "dist" / "index.html").exists():
        sys.exit("Frontend build failed - run `cd frontend && npm install` once, then retry.")


def ensure_cert(ip: str) -> tuple[Path, Path]:
    """Self-signed cert whose SAN covers localhost + the LAN IP.
    Regenerated whenever the LAN IP changes."""
    CERT_DIR.mkdir(parents=True, exist_ok=True)
    cert = CERT_DIR / "phone-cert.pem"
    key = CERT_DIR / "phone-key.pem"
    stamp = CERT_DIR / "phone-ip.txt"
    if cert.exists() and key.exists() and stamp.exists() and stamp.read_text().strip() == ip:
        return cert, key
    subprocess.run(
        [
            "openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes",
            "-keyout", str(key), "-out", str(cert), "-days", "365",
            "-subj", "/CN=secondshift-phone",
            "-addext",
            f"subjectAltName=DNS:localhost,IP:127.0.0.1,IP:{ip}",
        ],
        check=True,
        capture_output=True,
    )
    stamp.write_text(ip)
    print(f"Certificate written (SAN includes {ip}; self-signed, local only).")
    return cert, key


def print_qr(url: str) -> None:
    """Terminal QR code. Installs the pure-python `qrcode` package
    into the venv on first use; degrades to URL-only if it cannot."""
    try:
        import qrcode
    except ImportError:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-q", "qrcode"],
            check=False,
            capture_output=True,
        )
        try:
            import qrcode
        except ImportError:
            print("(QR code unavailable - type the URL into the phone browser.)")
            return
    qr = qrcode.QRCode(border=1)
    qr.add_data(url)
    qr.make()
    qr.print_ascii(invert=True)


def wait_healthy() -> bool:
    import ssl

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    for _ in range(40):
        try:
            with urllib.request.urlopen(
                f"https://127.0.0.1:{PORT}/api/health", context=ctx, timeout=2
            ) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            time.sleep(0.5)
    return False


def start_tunnel() -> str | None:
    """Cloudflare quick tunnel; returns the public URL or None."""
    exe = shutil.which("cloudflared")
    if exe is None:
        print("cloudflared is not installed, so no tunnel was started.")
        print("Install it with one of:")
        print("  macOS:   brew install cloudflared")
        print("  Linux:   https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/")
        print("Then run:  make phone TUNNEL=1")
        return None
    proc = subprocess.Popen(
        [exe, "tunnel", "--url", f"https://localhost:{PORT}", "--no-tls-verify"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    found: list[str] = []

    def _read() -> None:
        assert proc.stdout is not None
        for line in proc.stdout:
            match = re.search(r"https://[a-z0-9-]+\.trycloudflare\.com", line)
            if match:
                found.append(match.group(0))
                return

    threading.Thread(target=_read, daemon=True).start()
    for _ in range(60):
        if found:
            return found[0]
        if proc.poll() is not None:
            return None
        time.sleep(0.5)
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve SecondShift to a phone.")
    parser.add_argument("--tunnel", action="store_true", help="also open a Cloudflare quick tunnel")
    parser.add_argument("--no-build", action="store_true", help="skip the frontend build")
    args = parser.parse_args()

    ip = lan_ip()
    if not args.no_build:
        build_frontend()
    cert, key = ensure_cert(ip)

    env = dict(os.environ, SERVE_FRONTEND="1")
    if key_configured() and "PROVIDER" not in env:
        # A key on this machine means the presenter wants live mode;
        # an explicit PROVIDER (e.g. PROVIDER=mock) always wins.
        env["PROVIDER"] = "meta"
        print("Meta key found on this machine - serving in LIVE mode.")
    server = subprocess.Popen(
        [
            sys.executable, "-m", "uvicorn", "secondshift.main:app",
            "--app-dir", "backend", "--host", "0.0.0.0", "--port", str(PORT),
            "--ssl-certfile", str(cert), "--ssl-keyfile", str(key),
        ],
        cwd=ROOT,
        env=env,
    )
    try:
        if not wait_healthy():
            sys.exit("The server did not come up - check the output above.")
        url = f"https://{ip}:{PORT}"
        print()
        print("=" * 62)
        print("  SecondShift is live for your phone (same Wi-Fi):")
        print(f"  {url}")
        print("=" * 62)
        print_qr(url)
        print("On the phone: open the URL, accept the certificate warning")
        print("once (Advanced -> Proceed). For the camera on iPhone, iOS")
        print("may also need the cert trusted: Settings > General > About")
        print("> Certificate Trust Settings - or use TUNNEL=1 below.")
        if not key_configured():
            print()
            print("No META_API_KEY found in the environment or .env:")
            print("the app loads in DEMO mode and says so on screen.")
        if args.tunnel:
            print()
            print("Starting the tunnel (fallback for isolating Wi-Fi) ...")
            tunnel_url = start_tunnel()
            if tunnel_url:
                print()
                print("!" * 62)
                print("  WARNING: anyone with this link can use your API")
                print("  credits while it is open - stop it when done (Ctrl+C).")
                print("!" * 62)
                print(f"  Tunnel URL: {tunnel_url}")
                print_qr(tunnel_url)
        print()
        print("Serving - press Ctrl+C to stop.")
        server.wait()
    except KeyboardInterrupt:
        print("\nStopping ...")
    finally:
        server.terminate()


if __name__ == "__main__":
    main()
