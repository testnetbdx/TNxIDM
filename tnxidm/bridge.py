"""Localhost bridge for the TNxIDM browser extension. Stdlib only.

The GUI runs a tiny HTTP server bound to 127.0.0.1 (default port 8765).
The browser extension POSTs JSON to /add whenever it intercepts a download;
GET /ping answers {"ok": true, "version": ...} so the extension popup can
show the connection status. Only loopback is bound - nothing leaves the
machine, and any page on the internet cannot reach this server.
"""
import json
import threading
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer

VERSION = "1.1"
DEFAULT_PORT = 8765
PORT_TRIES = 5  # GUI tries port..port+4, extension probes the same range


class _Handler(BaseHTTPRequestHandler):
    server_version = "TNxIDM-Bridge/1.1"

    def _send(self, code, obj):
        body = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        if self.path == "/ping":
            self._send(200, {"ok": True, "version": VERSION})
        else:
            self._send(404, {"ok": False})

    def do_POST(self):
        if self.path != "/add":
            self._send(404, {"ok": False})
            return
        try:
            length = int(self.headers.get("Content-Length", 0))
            if length <= 0 or length > 65536:
                raise ValueError("bad length")
            msg = json.loads(self.rfile.read(length).decode("utf-8"))
            if not isinstance(msg, dict):
                raise ValueError("bad json")
        except Exception:
            self._send(400, {"ok": False, "error": "bad request"})
            return
        url = str(msg.get("url", "") or "")
        if len(url) > 8192 or not (url.startswith("http://") or url.startswith("https://")):
            self._send(400, {"ok": False, "error": "bad url"})
            return
        item = {
            "url": url,
            "filename": str(msg.get("filename", "") or ""),
            "referrer": str(msg.get("referrer", "") or ""),
            "user_agent": str(msg.get("user_agent", "") or ""),
            "page_url": str(msg.get("page_url", "") or ""),
        }
        try:
            self.server.on_add(item)
        except Exception:
            self._send(500, {"ok": False})
            return
        self._send(200, {"ok": True})

    def log_message(self, *args):  # keep the console quiet
        pass


class BridgeServer:
    """Tiny loopback HTTP server running in a daemon thread."""

    def __init__(self, port=DEFAULT_PORT, on_add=None):
        self._srv = HTTPServer(("127.0.0.1", port), _Handler)
        self._srv.on_add = on_add or (lambda item: None)
        self.port = self._srv.server_address[1]
        self._thread = threading.Thread(target=self._srv.serve_forever, daemon=True)

    def start(self):
        self._thread.start()

    def stop(self):
        self._srv.shutdown()
        self._thread.join(timeout=2)


def self_test():
    """Exercise ping, add, and rejection paths against a live server."""
    got = []
    srv = BridgeServer(0, on_add=got.append)
    srv.start()
    try:
        base = f"http://127.0.0.1:{srv.port}"
        with urllib.request.urlopen(base + "/ping", timeout=5) as r:
            assert json.load(r)["ok"] is True, "ping failed"

        def post(path, obj):
            data = json.dumps(obj).encode("utf-8")
            req = urllib.request.Request(base + path, data=data,
                                         headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=5) as r:
                return json.load(r)

        assert post("/add", {"url": "https://example.com/f.zip", "filename": "f.zip"})["ok"] is True
        assert len(got) == 1 and got[0]["url"] == "https://example.com/f.zip"
        assert got[0]["filename"] == "f.zip"
        for bad in ({"url": "ftp://x/y"}, {"url": "https://ok.example/" + "a" * 9000}, {"nope": 1}):
            try:
                post("/add", bad)
            except urllib.error.HTTPError as e:
                assert e.code == 400, f"expected 400, got {e.code}"
            else:
                raise AssertionError(f"bad input accepted: {bad}")
        print("BRIDGE_SELFTEST_PASS")
    finally:
        srv.stop()


if __name__ == "__main__":
    self_test()
