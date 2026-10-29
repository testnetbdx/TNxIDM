"""JSON settings and queue-state persistence. Stdlib only."""
import json, os
from pathlib import Path

def data_dir():
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    d = base / "TNxIDM"
    d.mkdir(parents=True, exist_ok=True)
    return d

def default_base_folder():
    return str(Path.home() / "Downloads" / "TNxIDM")

DEFAULTS = {
    "default_connections": 8,
    "max_concurrent": 2,
    "speed_limit_kbps": 0,
    "base_folder": default_base_folder(),
    "clipboard_monitor": True,
    "language": "bn",
    "minimize_to_tray": True,
}

class Settings:
    def __init__(self, path=None):
        self.path = Path(path) if path else data_dir() / "settings.json"
        self.data = dict(DEFAULTS)
        self.load()
    def load(self):
        try:
            if self.path.exists():
                loaded = json.loads(self.path.read_text(encoding="utf-8"))
                if isinstance(loaded, dict):
                    self.data.update(loaded)
        except Exception:
            pass
    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.data, indent=2, ensure_ascii=False), encoding="utf-8")
    def get(self, k, default=None):
        return self.data.get(k, default)
    def set(self, k, v):
        self.data[k] = v
        self.save()

def load_state(path):
    try:
        if Path(path).exists():
            data = json.loads(Path(path).read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
    except Exception:
        return []
    return []

def save_state(path, items):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(items, indent=2, ensure_ascii=False), encoding="utf-8")
