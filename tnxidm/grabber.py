"""Light site grabber: direct file links only. Stdlib only."""
import re, urllib.parse, urllib.request
from .categories import downloadable_extensions
from .engine import DEFAULT_UA

LINK_RE = re.compile(r'''(?:href|src)\s*=\s*["']([^"']+)["']''', re.I)

def fetch_links(page_url, timeout=30):
    req = urllib.request.Request(page_url, headers={"User-Agent": DEFAULT_UA})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        html = resp.read(2_000_000).decode("utf-8", errors="ignore")
        base = resp.geturl()
    exts = downloadable_extensions()
    seen, out = set(), []
    for raw in LINK_RE.findall(html):
        url = urllib.parse.urljoin(base, raw.strip())
        path = urllib.parse.urlparse(url).path.lower()
        ext = path.rsplit(".", 1)[-1] if "." in path else ""
        if ext in exts and url not in seen:
            seen.add(url)
            out.append({"url": url, "filename": urllib.parse.unquote(url.rsplit("/", 1)[-1]), "size": None})
    return out

def probe_size(url, timeout=15):
    try:
        req = urllib.request.Request(url, method="GET", headers={"User-Agent": DEFAULT_UA, "Range": "bytes=0-0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            cr = resp.headers.get("Content-Range", "")
            m = re.search(r"/(\d+)", cr)
            if m:
                return int(m.group(1))
            if resp.headers.get("Content-Length"):
                return int(resp.headers["Content-Length"])
    except Exception:
        pass
    return None
