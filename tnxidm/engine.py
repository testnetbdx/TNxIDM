"""TNxIDM download engine - 100% original, Python standard library only.

Features: HTTP Range segmented downloads, clean single-connection fallback,
pause/resume from saved segment offsets, global speed limiting, redirects,
custom headers, filename/size detection, JSON-persistable state.
No third-party download library is used anywhere in this module.
"""
import hashlib, os, re, threading, time, urllib.error, urllib.parse, urllib.request
from pathlib import Path

DEFAULT_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
              "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36")
CHUNK = 64 * 1024

def format_size(n):
    try:
        n = float(n)
    except Exception:
        return "?"
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or unit == "TB":
            return f"{n:.1f} {unit}" if unit != "B" else f"{int(n)} B"
        n /= 1024
    return f"{n:.1f} TB"

def format_speed(bps):
    if bps <= 0:
        return "0 KB/s"
    return f"{format_size(bps)}/s"

def format_eta(remaining, bps):
    if bps <= 0 or remaining is None or remaining < 0:
        return "--:--"
    s = int(remaining / bps)
    h, s = divmod(s, 3600)
    m, s = divmod(s, 60)
    return f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"

def filename_from_headers(url, headers):
    cd = headers.get("Content-Disposition", "") if headers else ""
    m = re.search(r"filename\*=UTF-8''([^;]+)", cd) or re.search(r'filename="([^"]+)"', cd) or re.search(r"filename=([^;]+)", cd)
    if m:
        name = urllib.parse.unquote(m.group(1).strip().strip('"'))
        if name and "/" not in name and "\\" not in name:
            return name
    path = urllib.parse.urlparse(url).path.rstrip("/")
    name = urllib.parse.unquote(os.path.basename(path)) if path else ""
    return name or "download.bin"

class GlobalLimiter:
    """Token-bucket limiter shared across all active downloads."""
    def __init__(self, kbps=0):
        self.lock = threading.Lock()
        self.set_rate(kbps)
    def set_rate(self, kbps):
        with self.lock:
            self.rate = int(kbps or 0) * 1024  # bytes/sec, 0 = unlimited
            self.tokens = float(self.rate) if self.rate else 0.0
            self.last = time.monotonic()
    def acquire(self, n):
        if self.rate <= 0:
            return
        # Block in small slices so pause remains responsive.
        remaining = int(n)
        while remaining > 0:
            with self.lock:
                now = time.monotonic()
                elapsed = now - self.last
                self.last = now
                self.tokens = min(float(self.rate), self.tokens + elapsed * self.rate)
                take = min(remaining, int(self.tokens))
                if take > 0:
                    self.tokens -= take
                    remaining -= take
                    continue
                wait = (1 - self.tokens) / self.rate if self.rate else 0
            time.sleep(min(0.05, max(0.001, wait)))

def probe(url, headers=None):
    """Return (filename, total_bytes_or_None, supports_range). Follows redirects."""
    req = urllib.request.Request(url, method="GET", headers=_headers(headers))
    # Ask for first byte only to avoid downloading the body here.
    req.add_header("Range", "bytes=0-0")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            h = resp.headers
            total = None
            cr = h.get("Content-Range", "")
            m = re.search(r"/(\d+)", cr)
            if m:
                total = int(m.group(1))
            elif h.get("Content-Length"):
                try:
                    total = int(h.get("Content-Length"))
                except Exception:
                    total = None
            # If server ignored Range and sent 200, Content-Length is the full size.
            supports = (h.get("Accept-Ranges", "").lower() == "bytes") or resp.status == 206
            return filename_from_headers(resp.geturl(), h), total, supports
    except urllib.error.HTTPError as e:
        # Some servers reject Range probing; fall back to a plain HEAD-like GET.
        if e.code in (400, 403, 416):
            h = e.headers or {}
            total = None
            if h.get("Content-Length"):
                try:
                    total = int(h.get("Content-Length"))
                except Exception:
                    pass
            return filename_from_headers(url, h), total, False
        raise
    except Exception:
        raise

def _headers(custom):
    h = {"User-Agent": DEFAULT_UA}
    if custom:
        for k, v in custom.items():
            if v:
                h[k] = v
    return h

class Segment:
    def __init__(self, index, start, end, downloaded=0):
        self.index, self.start, self.end = index, start, end
        self.downloaded = downloaded  # bytes already written for this segment
    @property
    def size(self):
        return self.end - self.start + 1 if self.end is not None else 0
    def to_dict(self):
        return {"index": self.index, "start": self.start, "end": self.end, "downloaded": self.downloaded}
    @classmethod
    def from_dict(cls, d):
        return cls(int(d["index"]), int(d["start"]), int(d["end"]), int(d.get("downloaded", 0)))

class DownloadTask:
    def __init__(self, url, dest_dir, filename=None, connections=8, custom_headers=None,
                 scheduled_at=None, task_id=None, state_dir=None):
        self.url = url
        self.dest_dir = str(dest_dir)
        self.filename = filename
        self.connections = int(connections or 8)
        self.custom_headers = dict(custom_headers or {})
        self.scheduled_at = scheduled_at  # epoch float or None
        self.id = task_id or f"{int(time.time()*1000)}-{hashlib.md5(url.encode()).hexdigest()[:8]}"
        self.state_dir = Path(state_dir) if state_dir else Path(self.dest_dir)
        self.total = None
        self.supports_range = False
        self.segments = []
        self.status = "waiting"  # waiting/queued/downloading/paused/done/failed/cancelled/scheduled
        self.error = ""
        self.started_at = None
        self._pause = threading.Event()
        self._stop = threading.Event()
        self._threads = []
        self._lock = threading.Lock()
        self._bytes_since = 0
        self._last_speed_at = time.monotonic()
        self._last_speed_bytes = 0
        self.speed_bps = 0.0
        self.avg_bps = 0.0
        self._downloaded_at_start = 0
    @property
    def dest_path(self):
        return Path(self.dest_dir) / (self.filename or "download.bin")
    @property
    def downloaded(self):
        return sum(s.downloaded for s in self.segments) if self.segments else 0
    @property
    def percent(self):
        if self.total:
            return min(100.0, 100.0 * self.downloaded / self.total)
        return 0.0
    @property
    def eta(self):
        if self.total and self.speed_bps > 0:
            return format_eta(self.total - self.downloaded, self.speed_bps)
        return "--:--"
    def part_path(self, index):
        return self.state_dir / f".{self.id}.part{index}"
    def temp_path(self):
        return self.state_dir / f".{self.id}.tmp"
    def to_dict(self):
        return {"id": self.id, "url": self.url, "dest_dir": self.dest_dir, "filename": self.filename,
                "connections": self.connections, "custom_headers": self.custom_headers,
                "scheduled_at": self.scheduled_at, "total": self.total,
                "supports_range": self.supports_range,
                "segments": [s.to_dict() for s in self.segments],
                "status": self.status, "error": self.error}
    @classmethod
    def from_dict(cls, d, state_dir=None):
        t = cls(d["url"], d.get("dest_dir", "."), d.get("filename"), d.get("connections", 8),
                d.get("custom_headers"), d.get("scheduled_at"), d.get("id"), state_dir)
        t.total = d.get("total")
        t.supports_range = bool(d.get("supports_range"))
        t.segments = [Segment.from_dict(s) for s in d.get("segments", [])]
        t.status = d.get("status", "waiting")
        t.error = d.get("error", "")
        # A task that was downloading when the app closed resumes as paused, never as lost.
        if t.status == "downloading":
            t.status = "paused"
        return t
    def _sync_segment_sizes(self):
        """Trust part files on disk as the source of truth for offsets."""
        for s in self.segments:
            p = self.part_path(s.index)
            if p.exists():
                s.downloaded = p.stat().st_size
            elif s.downloaded and not p.exists() and self.supports_range:
                s.downloaded = 0
    def _segment_ranges(self, total, n):
        n = max(1, min(int(n), total)) if total else 1
        base, rem = divmod(total, n)
        out, pos = [], 0
        for i in range(n):
            size = base + (1 if i < rem else 0)
            out.append((pos, pos + size - 1))
            pos += size
        return out
    def _worker(self, seg, limiter):
        start = seg.start + seg.downloaded
        if seg.end is not None and start > seg.end:
            return
        req_headers = _headers(self.custom_headers)
        if self.supports_range and self.total:
            req_headers["Range"] = f"bytes={start}-{seg.end}"
        req = urllib.request.Request(self.url, headers=req_headers)
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                # A 200 reply to a Range request means no range support; the
                # caller already fell back, so this path should not duplicate data.
                path = self.part_path(seg.index) if self.supports_range else self.temp_path()
                mode = "ab" if path.exists() else "wb"
                with open(path, mode) as f:
                    # Single-connection path always writes from the start;
                    # prepare() already discarded any stale single-connection
                    # partial, because a no-Range server cannot resume it.
                    while not self._stop.is_set():
                        if self._pause.is_set():
                            return
                        try:
                            chunk = resp.read(CHUNK)
                        except Exception:
                            break
                        if not chunk:
                            break
                        limiter.acquire(len(chunk))
                        f.write(chunk)
                        f.flush()
                        with self._lock:
                            seg.downloaded += len(chunk)
                            self._bytes_since += len(chunk)
                        self._update_speed()
                        if self._pause.is_set():
                            return
        except Exception as e:
            with self._lock:
                if not self.error:
                    self.error = str(e)
    def _update_speed(self):
        now = time.monotonic()
        dt = now - self._last_speed_at
        if dt >= 0.5:
            total_dl = self.downloaded
            self.speed_bps = (total_dl - self._last_speed_bytes) / dt if dt else 0
            self._last_speed_bytes = total_dl
            self._last_speed_at = now
            if self.started_at:
                elapsed = max(0.1, now - self.started_at)
                self.avg_bps = (total_dl - self._downloaded_at_start) / elapsed
    def prepare(self):
        """Probe once, set filename/size/segments. Idempotent for resume."""
        if self.filename and self.total is not None and self.segments:
            self._sync_segment_sizes()
            return
        fname, total, supports = probe(self.url, self.custom_headers)
        if not self.filename:
            self.filename = fname
        self.total = total
        self.supports_range = bool(supports and total)
        Path(self.dest_dir).mkdir(parents=True, exist_ok=True)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        if self.supports_range:
            ranges = self._segment_ranges(total, self.connections)
            # Keep existing offsets on resume; only rebuild when segment count changed.
            if len(self.segments) != len(ranges):
                self.segments = [Segment(i, s, e) for i, (s, e) in enumerate(ranges)]
            self._sync_segment_sizes()
        else:
            # No Range support: a partial single-connection file cannot be
            # resumed (the server would resend from byte 0), so discard it
            # and download cleanly from the start. Segmented downloads
            # (the normal case) are unaffected and resume from offsets.
            self.temp_path().unlink(missing_ok=True)
            self.segments = [Segment(0, 0, (total - 1) if total else 0)]
    def run(self, limiter, on_progress=None):
        """Blocking download. Returns True on completion, False on pause/stop/fail."""
        self._pause.clear(); self._stop.clear()
        self.error = ""
        try:
            self.prepare()
        except Exception as e:
            self.status = "failed"; self.error = str(e)
            return False
        self.status = "downloading"
        self.started_at = time.monotonic()
        self._downloaded_at_start = self.downloaded
        self._last_speed_bytes = self.downloaded
        self._last_speed_at = time.monotonic()
        self._threads = []
        for seg in self.segments:
            if seg.end is not None and seg.downloaded >= seg.size:
                continue
            th = threading.Thread(target=self._worker, args=(seg, limiter), daemon=True)
            th.start(); self._threads.append(th)
        for th in self._threads:
            th.join()
        self._update_speed()
        if self._stop.is_set():
            self.status = "cancelled"
            return False
        if self._pause.is_set():
            self.status = "paused"
            return False
        if self.error:
            # Partial segment errors with incomplete data count as failure, not success.
            if self.total and self.downloaded < self.total:
                self.status = "failed"
                return False
        if self.total and self.downloaded < self.total:
            # Server closed early without an explicit error.
            if not self.error:
                self.error = "Incomplete download"
            self.status = "failed"
            return False
        try:
            self._merge()
        except Exception as e:
            self.status = "failed"; self.error = str(e)
            return False
        self.status = "done"
        self.speed_bps = 0
        return True
    def _merge(self):
        final = self.dest_path
        final.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.state_dir / f".{self.id}.merged"
        with open(tmp, "wb") as out:
            if self.supports_range:
                for seg in self.segments:
                    p = self.part_path(seg.index)
                    if p.exists():
                        with open(p, "rb") as f:
                            while True:
                                c = f.read(CHUNK)
                                if not c:
                                    break
                                out.write(c)
            else:
                p = self.temp_path()
                if p.exists():
                    with open(p, "rb") as f:
                        while True:
                            c = f.read(CHUNK)
                            if not c:
                                break
                            out.write(c)
        os.replace(tmp, final)
        for seg in self.segments:
            self.part_path(seg.index).unlink(missing_ok=True)
        self.temp_path().unlink(missing_ok=True)
    def pause(self):
        self._pause.set()
    def cancel(self):
        self._stop.set(); self._pause.clear()
        # Best-effort cleanup after threads exit is done by the manager.
    def cleanup_parts(self):
        for seg in self.segments:
            self.part_path(seg.index).unlink(missing_ok=True)
        self.temp_path().unlink(missing_ok=True)

class DownloadManager:
    """FIFO queue, max-concurrent enforcement, persistent state, scheduler hook."""
    def __init__(self, state_path, limiter=None, on_change=None):
        self.state_path = Path(state_path)
        self.limiter = limiter or GlobalLimiter(0)
        self.on_change = on_change
        self.tasks = []
        self.max_concurrent = 2
        self._lock = threading.Lock()
        self._running = {}  # id -> thread
        self._stop_scheduler = threading.Event()
        self._load()
    def _load(self):
        from .settings import load_state
        state_dir = self.state_path.parent
        for d in load_state(self.state_path):
            try:
                self.tasks.append(DownloadTask.from_dict(d, state_dir=state_dir))
            except Exception:
                continue
    def save(self):
        from .settings import save_state
        with self._lock:
            save_state(self.state_path, [t.to_dict() for t in self.tasks])
    def add(self, task):
        with self._lock:
            self.tasks.append(task)
        self.save(); self._notify()
        self.pump()
        return task
    def active_count(self):
        return sum(1 for t in self.tasks if t.status == "downloading")
    def _notify(self):
        if self.on_change:
            try:
                self.on_change()
            except Exception:
                pass
    def pump(self):
        """Start waiting/scheduled-due tasks up to max_concurrent, FIFO."""
        now = time.time()
        for task in list(self.tasks):
            if self.active_count() >= self.max_concurrent:
                break
            if task.status in ("waiting", "queued", "scheduled"):
                if task.scheduled_at and task.scheduled_at > now:
                    continue
                self._start(task)
            elif task.status == "paused" and getattr(task, "_resume_requested", False):
                task._resume_requested = False
                self._start(task)
    def _start(self, task):
        task.status = "downloading"
        th = threading.Thread(target=self._run_task, args=(task,), daemon=True)
        self._running[task.id] = th
        th.start(); self._notify()
    def _run_task(self, task):
        try:
            task.run(self.limiter)
        finally:
            self._running.pop(task.id, None)
            if task.status == "cancelled":
                task.cleanup_parts()
            self.save(); self._notify()
            self.pump()
    def pause_task(self, task):
        task.pause()
    def resume_task(self, task):
        if task.status in ("paused", "failed"):
            task._resume_requested = True
            task.status = "paused"
            self.pump()
            # If a slot is free, pump starts it; otherwise it stays queued via flag.
            if task.status == "paused" and self.active_count() < self.max_concurrent:
                task._resume_requested = False
                self._start(task)
    def retry_task(self, task):
        task.error = ""
        self.resume_task(task)
    def restart_task(self, task):
        task.cleanup_parts()
        task.segments = []; task.total = None
        task.status = "waiting"; task.error = ""
        self.save(); self.pump()
    def cancel_task(self, task):
        task.cancel()
        # If not running, clean up immediately.
        if task.id not in self._running:
            task.cleanup_parts(); task.status = "cancelled"
        self.save(); self._notify()
    def remove_task(self, task, delete_file=False):
        self.cancel_task(task)
        if delete_file:
            try:
                task.dest_path.unlink(missing_ok=True)
            except Exception:
                pass
        with self._lock:
            self.tasks = [t for t in self.tasks if t.id != task.id]
        self.save(); self._notify()
    def pause_all(self):
        for t in self.tasks:
            if t.status == "downloading":
                t.pause()
    def resume_all(self):
        for t in self.tasks:
            if t.status == "paused":
                self.resume_task(t)
    def total_speed(self):
        return sum(t.speed_bps for t in self.tasks if t.status == "downloading")
    def start_scheduler(self, interval=20):
        def loop():
            while not self._stop_scheduler.is_set():
                self.pump(); self.save()
                self._stop_scheduler.wait(interval)
        threading.Thread(target=loop, daemon=True).start()
    def stop_scheduler(self):
        self._stop_scheduler.set()
