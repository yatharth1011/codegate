#!/usr/bin/env python3
"""CodeGate server.

Runs on the Mac that hosts the workspaces and does three jobs:
  - the owner-only admin API (open/close rooms, starter files, members...) that
    Dromac's dashboard drives, on 127.0.0.1 only in effect: it answers only
    loopback clients that send a custom header;
  - a plain-HTTP info page + certificate download for people joining, on the
    LAN, so they can trust the gate's HTTPS certificate once;
  - starting/stopping the HTTPS gate (gate.py) that fronts each member's
    container (spaces.py).
"""
import http.server
import json
import os
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path

import gate
import spaces

BASE_DIR = Path(__file__).resolve().parent
PORT = gate.TRUST_PORT
COLLECTED_DIR = Path.home() / "Documents" / "CodeGate Collected"

SPACES = None
GATE = None


def _detect_lan_ip():
    """The address other machines on the network reach this Mac at. Asks the OS
    which local address would route outbound; a UDP connect sends nothing."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except Exception:
        try:
            return socket.gethostbyname(socket.gethostname())
        except Exception:
            return "127.0.0.1"


def log(msg, ip=""):
    line = f"{time.strftime('%Y-%m-%d %H:%M:%S')}  {ip or '-':15}  {msg}\n"
    with open(BASE_DIR / "access.log", "a") as f:
        f.write(line)
    print(f"[codegate] {msg} {ip}", file=sys.stderr)


def _esc(v):
    return str(v).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


class Handler(http.server.BaseHTTPRequestHandler):
    server_version = "CodeGate/1.0"

    def log_message(self, fmt, *args):
        pass

    # ------------------------------------------------------------- helpers

    def _send(self, status, ctype, body, extra=None):
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def _json(self, obj, status=200):
        self._send(status, "application/json", json.dumps(obj).encode())

    def _admin_ok(self):
        # Running other people's code on this Mac is owner-only: loopback
        # client and Host (blocks DNS rebinding), plus a custom header a
        # cross-site web page can't send without a CORS preflight.
        host = (self.headers.get("Host") or "").lower()
        return (self.client_address[0] in ("127.0.0.1", "::1")
                and host in (f"127.0.0.1:{PORT}", f"localhost:{PORT}")
                and self.headers.get("X-CodeGate-Local") == "1")

    def _status(self):
        return {"gate": {"running": GATE.running(), "url": GATE.url()}, **SPACES.status()}

    # ---------------------------------------------------------------- pages

    def _trust_page(self):
        if GATE.running():
            state = (f'<p>A room is open.</p><a class="btn" href="{_esc(GATE.url())}">Join a room</a>'
                     '<p class="dim">You\'ll need the PIN you were given.</p>')
        else:
            state = "<p>No room is open right now.</p>"
        body = f"""<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>CodeGate</title>
<style>{gate.CSS}</style></head><body><div class="box">
<h1>CodeGate</h1><p class="sub">Private workspaces in your browser.</p>{state}
<h2>First time on this device?</h2>
<p class="dim">Joining runs over HTTPS with this server's own certificate. Trust it once per device, or the
browser warns every time and notebooks and previews won't load.</p>
<a class="btn ghost" href="/ca.pem">Download certificate</a>
<ul class="dim">
<li><b>macOS:</b> open the file, Keychain Access adds it, double-click it, Trust, "Always Trust".</li>
<li><b>Windows:</b> rename it to .crt, open it, Install Certificate, Current User,
"Trusted Root Certification Authorities".</li>
<li><b>Linux (Chrome):</b> Settings, Privacy and security, Security, Manage certificates, Authorities, Import.</li>
</ul>
<p class="dim">It can only vouch for private network addresses (10.x, 172.16-31.x, 192.168.x, localhost),
so trusting it can't be used to impersonate real websites.</p>
</div></body></html>""".encode("utf-8")
        self._send(200, "text/html; charset=utf-8", body)

    # ------------------------------------------------------------- actions

    def _action(self, action, data):
        try:
            if action == "open":
                SPACES.open_room(data.get("kind"))
                GATE.start()
                if not SPACES.runtime_up():
                    SPACES.start_runtime()
            elif action == "close":
                SPACES.close_room(data.get("kind"))
            elif action == "stop_all":
                SPACES.stop_all("stopped from Dromac")
                for kind in list(SPACES.state["rooms"]):
                    SPACES.close_room(kind)
                GATE.stop()
            elif action == "add_starter":
                SPACES.add_starter(data.get("slug"), data.get("title"), data.get("folder"))
            elif action == "delete_starter":
                SPACES.delete_starter(data.get("slug"))
            elif action == "stop_member":
                SPACES.stop_member(data.get("id"))
                GATE.drop_member(data.get("id"))
            elif action == "remove_member":
                GATE.drop_member(data.get("id"))
                SPACES.remove_member(data.get("id"))
            elif action == "set_internet":
                SPACES.set_internet(bool(data.get("on")))
            elif action == "set_limit":
                SPACES.set_limit(data.get("kind"), data.get("n"))
            elif action == "start_runtime":
                SPACES.start_runtime()
            elif action == "build_image":
                SPACES.build_image(data.get("kind"))
            elif action == "export":
                ids = ([m["id"] for m in SPACES.status()["members"]] if data.get("id") == "*" else [data.get("id")])
                saved = [SPACES.export_member(i, data.get("starter") or None, COLLECTED_DIR) for i in ids
                         if SPACES.member(i)]
                if not saved:
                    raise spaces.SpacesError("Nothing to export.")
                subprocess.Popen(["open", "-R", saved[0]])
                return {**self._status(), "exported": len(saved), "folder": str(COLLECTED_DIR)}
            else:
                return {"error": "unknown action"}
        except spaces.SpacesError as e:
            return {"error": str(e)}
        return self._status()

    # -------------------------------------------------------------- routing

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path == "/":
            return self._trust_page()
        if path == "/ca.pem":
            return self._send(200, "application/x-x509-ca-cert", GATE.ca_pem(),
                              {"Content-Disposition": 'attachment; filename="CodeGate-CA.pem"'})
        if path == "/api/status":
            if not self._admin_ok():
                return self._json({"error": "only available on this Mac"}, 403)
            return self._json(self._status())
        self._send(404, "text/plain", b"Not found")

    def do_POST(self):
        path = self.path.split("?", 1)[0]
        if not path.startswith("/api/"):
            return self._send(404, "text/plain", b"Not found")
        if not self._admin_ok():
            return self._json({"error": "only available on this Mac"}, 403)
        length = int(self.headers.get("Content-Length", 0) or 0)
        try:
            data = json.loads(self.rfile.read(length) or b"{}") if length else {}
        except Exception:
            data = {}
        result = self._action(path[len("/api/"):], data)
        self._json(result, 400 if "error" in result else 200)


def main():
    global SPACES, GATE
    SPACES = spaces.Spaces(BASE_DIR, log)
    GATE = gate.Gate(BASE_DIR, _detect_lan_ip, SPACES, log)
    SPACES.on_idle = GATE.stop
    if SPACES.runtime_up():
        SPACES.stop_all("cleared at startup")  # leftovers from a previous run; workspaces persist
    if SPACES.any_room_open():
        GATE.start()  # a room was open when this last stopped; its PIN is still valid

    def shutdown(*_):
        # Never leave workspaces running with nothing in front of them.
        GATE.stop()
        SPACES.stop_all("stopped: server exiting")
        os._exit(0)
    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)

    server = http.server.ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print(f"CodeGate listening on http://{_detect_lan_ip()}:{PORT} (gate on https port {gate.GATE_PORT} while a room is open)",
          file=sys.stderr)
    server.serve_forever()


if __name__ == "__main__":
    main()
