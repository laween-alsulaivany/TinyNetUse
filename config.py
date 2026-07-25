# config.py — Loads and saves config.json. Provides DEFAULTS and the Config class.

import json
import sys
from pathlib import Path

DEFAULTS = {
    "font": "Segoe UI",
    "font_size": 10,
    "font_color": "#FFFFFF",
    "font_bold": False,
    "widget_geometry": None,
    "widget_locked": False,
    "widget_always_on_top": True,
    "graph_visible": False,
    "graph_geometry": None,
    "graph_locked": False,
    "graph_always_on_top": True,
    "graph_history": 60,
    "update_interval": 1.0,
    "opacity": 0.8,
    "alert_color": "#FF5555",
    "download_color": "#4FC3F7",
    "upload_color": "#FF8A65",
    "unit": "auto",
    "precision": 1,
    "notify_threshold": {"download": None},
    "start_on_boot": False,
}


def _config_path() -> Path:
    # Frozen (PyInstaller --onefile): _MEIPASS is a temp dir that gets wiped on exit,
    # so we put config next to the exe instead. Script mode: next to this file.
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent / "config.json"
    return Path(__file__).parent / "config.json"


class Config:
    def __init__(self, path=None):
        self.path = Path(path) if path else _config_path()
        if not self.path.exists():
            self.data = DEFAULTS.copy()
            self.save()
        else:
            try:
                with open(self.path, "r") as f:
                    self.data = json.load(f)
            except json.JSONDecodeError:
                # Corrupt config (bad manual edit, truncated write, etc.) - start fresh.
                # The broken file gets overwritten on the next save.
                self.data = DEFAULTS.copy()
            for k, v in DEFAULTS.items():
                self.data.setdefault(k, v)

    def save(self):
        with open(self.path, "w") as f:
            json.dump(self.data, f, indent=2)
