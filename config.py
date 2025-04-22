# config.py

import json
import os

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
    "start_on_boot": False

}

class Config:
    def __init__(self, path="config.json"):
        self.path = path
        if not os.path.exists(path):
            self.data = DEFAULTS.copy()
            self.save()
        else:
            with open(path, "r") as f:
                self.data = json.load(f)
            for k, v in DEFAULTS.items():
                self.data.setdefault(k, v)

    def save(self):
        with open(self.path, "w") as f:
            json.dump(self.data, f, indent=2)