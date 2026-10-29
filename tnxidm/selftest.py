"""--self-test: local Range server, 8-segment download, pause, resume, SHA-256."""
import hashlib, http.server, os, random, socketserver, sys, threading, time
from pathlib import Path

TEST_SIZE = 4 * 1024 * 1024  # 4 MiB: fast, still exercises 8 segments

class RangeHandler(http.server.BaseHTTPRequestHandler):
    data = b""
    def log_message(self, *a):
        pass
    def _send_range(self):
        data = self.data
        rng = self.headers.get("Range")
        start, end = 0, len(data) - 1
        status = 200
        if rng and rng.startswith("bytes="):
            try:
                a, b = rng[6:].split("-", 1)
                start = int(a) if a else 0
                end = int(b) if b else len(data) - 1
                status = 206
            except Exception:
                pass
        body = data[start:end + 1]
        self.send_response(status)
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Type", "application/octet-stream")
        if status == 206:
            self.send_header("Content-Range", f"bytes {start}-{end}/{len(data)}")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        # Throttle slightly so pause can land mid-download.
        for i in range(0, len(body), 64 * 1024):
            try:
                self.wfile.write(body[i:i + 64 * 1024])
                self.wfile.flush()
            except Exception:
                break
            time.sleep(0.002)
    do_GET = _send_range
    do_HEAD = _send_range

def run_selftest(dest_dir=None):
    from .engine import DownloadManager, DownloadTask, GlobalLimiter
    rng = random.Random(12345)
    original = bytes(rng.randrange(256) for _ in range(TEST_SIZE))
    orig_sha = hashlib.sha256(original).hexdigest()
    RangeHandler.data = original
    with socketserver.ThreadingTCPServer(("127.0.0.1", 0), RangeHandler) as httpd:
        port = httpd.server_address[1]
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        tmp = Path(dest_dir) if dest_dir else Path(os.environ.get("TMP", "/tmp")) / "tnxidm-selftest"
        tmp.mkdir(parents=True, exist_ok=True)
        for p in tmp.glob("*"):
            try:
                p.unlink()
            except Exception:
                pass
        url = f"http://127.0.0.1:{port}/testfile.bin"
        task = DownloadTask(url, str(tmp), filename="testfile.bin", connections=8,
                            state_dir=str(tmp))
        # Drive the task directly so pause/resume is deterministic.
        limiter = GlobalLimiter(0)
        thread = threading.Thread(target=lambda: task.run(limiter), daemon=True)
        thread.start()
        paused = False
        deadline = time.time() + 60
        while thread.is_alive() and time.time() < deadline:
            if task.downloaded > 0 and task.total and task.downloaded < task.total:
                task.pause()
                paused = True
                break
            time.sleep(0.02)
        thread.join(timeout=30)
        if not paused:
            print("FAIL: could not pause mid-download")
            return 1
        print(f"Paused at {task.downloaded}/{task.total} bytes, segments={[s.downloaded for s in task.segments]}")
        if task.downloaded <= 0 or task.downloaded >= (task.total or 0):
            print("FAIL: pause did not land mid-download")
            return 1
        # Resume from saved offsets (same task object, same part files).
        ok = task.run(limiter)
        httpd.shutdown()
        if not ok or task.status != "done":
            print(f"FAIL: resume did not complete (status={task.status} error={task.error})")
            return 1
        final = tmp / "testfile.bin"
        if not final.exists():
            print("FAIL: merged file missing")
            return 1
        got_sha = hashlib.sha256(final.read_bytes()).hexdigest()
        print(f"Original SHA-256: {orig_sha}")
        print(f"Merged   SHA-256: {got_sha}")
        print(f"Segments used: 8, size: {final.stat().st_size} bytes")
        if got_sha == orig_sha:
            print("PASS")
            return 0
        print("FAIL: SHA-256 mismatch")
        return 1

if __name__ == "__main__":
    sys.exit(run_selftest())
