import json
import os

DEFAULTS = {
    "update_interval": 1.0,
    "interface": "All",
    "unit": "auto",         # "auto", "KB/s", "MB/s"
    "precision": 1,         # 0,1,2
    "theme": "dark",        # "light" or "dark"
    "font": "Helvetica",
    "font_size": 10,
    "always_on_top": True,
    "opacity": 0.9,
    "geometry": None,
    "start_minimized": False,
    "start_on_boot": False,
    "notify_threshold": {"download": None, "upload": None}
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
            # fill missing defaults
            for k, v in DEFAULTS.items():
                self.data.setdefault(k, v)

    def save(self):
        with open(self.path, "w") as f:
            json.dump(self.data, f, indent=2)
