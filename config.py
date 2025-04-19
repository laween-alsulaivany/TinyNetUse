# config.py

import json
import os

DEFAULTS = {
    "update_interval": 1.0,
    "unit": "auto",
    "precision": 1,
    "font": "Segoe UI",
    "font_size": 10,
    "graph_always_on_top": False,
    "net_always_on_top": True,
    "opacity": 0.8,
    "widget_geometry": [100, 100, 300, 120],
    "graph_geometry": [100, 100, 300, 120],
    "start_minimized": False,
    "start_on_boot": False,
    "notify_threshold": {"download": None},
    "locked": False
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