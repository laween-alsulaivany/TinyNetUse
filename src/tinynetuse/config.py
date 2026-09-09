"""TinyNetUse settings paths, validation, and storage."""

from copy import deepcopy
from datetime import datetime
import json
import math
import os
from pathlib import Path
import re
import sys
import tempfile

from tinynetuse.units import AUTO_UNITS, SUPPORTED_UNITS


APP_NAME = "TinyNetUse"
CONFIG_FILENAME = "config.json"
CONFIG_VERSION = 10
PORTABLE_MARKER = "portable.flag"
GRAPH_STYLES = ("centered", "stacked", "overlay")

DEFAULTS = {
    "config_version": CONFIG_VERSION,
    "font": "Segoe UI",
    "font_size": 10,
    "font_color": "#FFFFFF",
    "font_bold": False,
    "widget_geometry": None,
    "widget_locked": False,
    "widget_always_on_top": True,
    "click_through_overlay": False,
    "graph_visible": False,
    "graph_geometry": None,
    "graph_locked": False,
    "graph_always_on_top": True,
    "graph_history": 60,
    "graph_style": "centered",
    "graph_opacity": 0.8,
    "update_interval": 1.0,
    "opacity": 0.8,
    "reduce_opacity_on_hover": False,
    "alert_color": "#FF5555",
    "download_color": "#2680EB",
    "upload_color": "#D97706",
    "network_adapter": "auto",
    "unit": "auto",
    "auto_unit_minimum": "B/s",
    "precision": 1,
    "notify_threshold": {"download": None, "upload": None},
}

BOOL_KEYS = (
    "font_bold",
    "widget_locked",
    "widget_always_on_top",
    "click_through_overlay",
    "graph_visible",
    "graph_locked",
    "graph_always_on_top",
    "reduce_opacity_on_hover",
)
COLOR_KEYS = ("font_color", "alert_color", "download_color", "upload_color")
GEOMETRY_KEYS = ("widget_geometry", "graph_geometry")
COLOR_PATTERN = re.compile(r"^#[0-9a-fA-F]{6}$")


# Always return a fresh copy because notify_threshold is nested.
def default_config() -> dict:
    # callers can safely modify the result without touching the shared defaults
    return deepcopy(DEFAULTS)


def _is_number(value) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _valid_int(value, minimum: int, maximum: int) -> bool:
    return (
        isinstance(value, int)
        and not isinstance(value, bool)
        and minimum <= value <= maximum
    )


def _valid_geometry(value) -> bool:
    if not isinstance(value, (list, tuple)) or len(value) != 4:
        return False
    if not all(isinstance(item, int) and not isinstance(item, bool) for item in value):
        return False
    return value[2] > 0 and value[3] > 0


# Migrate older configuration versions to the current schema for backward compatibility.
def _migrate(data: dict) -> dict:
    # migrate a copy so validation never mutates the loaded JSON object
    migrated = deepcopy(data)
    version = migrated.get("config_version", 0)

    if not isinstance(version, int) or isinstance(version, bool):
        version = 0

    # Windows owns this state now, so schema 2 drops the old cached boolean.
    if version < 2:
        migrated.pop("start_on_boot", None)

    # Schema 4 adds a separate upload highlight threshold.
    if version < 4 and isinstance(migrated.get("notify_threshold"), dict):
        migrated["notify_threshold"].setdefault("upload", None)

    if version < 10:
        migrated["graph_opacity"] = migrated.get("opacity", 0.8)

    migrated["config_version"] = CONFIG_VERSION

    return migrated


# Keep validation close to the settings UI ranges.
def validate_config(data) -> dict:
    # rebuild from defaults so unknown or malformed settings never leak through
    if not isinstance(data, dict):
        return default_config()

    data = _migrate(data)
    clean = default_config()

    if isinstance(data.get("font"), str) and data["font"].strip():
        clean["font"] = data["font"].strip()
    if _valid_int(data.get("font_size"), 6, 72):
        clean["font_size"] = data["font_size"]

    for key in COLOR_KEYS:
        if isinstance(data.get(key), str) and COLOR_PATTERN.fullmatch(data[key]):
            clean[key] = data[key]

    for key in BOOL_KEYS:
        if isinstance(data.get(key), bool):
            clean[key] = data[key]

    if clean["click_through_overlay"]:
        clean["reduce_opacity_on_hover"] = False

    for key in GEOMETRY_KEYS:
        value = data.get(key)
        if value is None:
            clean[key] = None
        elif _valid_geometry(value):
            clean[key] = list(value)

    if _valid_int(data.get("graph_history"), 2, 3600):
        clean["graph_history"] = data["graph_history"]
    if data.get("graph_style") in GRAPH_STYLES:
        clean["graph_style"] = data["graph_style"]

    interval = data.get("update_interval")
    if _is_number(interval) and 0.1 <= interval <= 60:
        clean["update_interval"] = interval

    opacity = data.get("opacity")
    if _is_number(opacity) and 0.2 <= opacity <= 1:
        clean["opacity"] = opacity

    graph_opacity = data.get("graph_opacity")
    if _is_number(graph_opacity) and 0.2 <= graph_opacity <= 1:
        clean["graph_opacity"] = graph_opacity

    if data.get("unit") in SUPPORTED_UNITS:
        clean["unit"] = data["unit"]
    if data.get("auto_unit_minimum") in AUTO_UNITS:
        clean["auto_unit_minimum"] = data["auto_unit_minimum"]
    if _valid_int(data.get("precision"), 0, 2):
        clean["precision"] = data["precision"]

    adapter = data.get("network_adapter")
    if (
        isinstance(adapter, str)
        and adapter.strip()
        and len(adapter.strip()) <= 256
        and "\0" not in adapter
    ):
        clean["network_adapter"] = adapter.strip()

    threshold = data.get("notify_threshold")
    if isinstance(threshold, dict):
        for direction in ("download", "upload"):
            value = threshold.get(direction)
            if value is None:
                clean["notify_threshold"][direction] = None
            elif _is_number(value) and 0 < value <= 1000:
                clean["notify_threshold"][direction] = value

    return clean


# Find the local application data directory.
def _local_app_data(local_app_data=None) -> Path:
    if local_app_data is not None:
        return Path(local_app_data)

    value = os.environ.get("LOCALAPPDATA")
    if value:
        return Path(value)
    return Path.home() / "AppData" / "Local"


# Check if the application is running in portable mode.
def is_portable_mode(executable=None, frozen=None) -> bool:
    if frozen is None:
        frozen = bool(getattr(sys, "frozen", False))
    executable = Path(executable or sys.executable)
    return frozen and (executable.parent / PORTABLE_MARKER).is_file()


# Source settings use a separate local folder so the repository stays untouched.
def resolve_config_path(frozen=None, executable=None, local_app_data=None) -> Path:

    if frozen is None:
        frozen = bool(getattr(sys, "frozen", False))

    executable = Path(executable or sys.executable)
    if is_portable_mode(executable, frozen):
        # Portable build:   beside TinyNetUse.exe
        return executable.parent / CONFIG_FILENAME

    app_data = _local_app_data(local_app_data) / APP_NAME
    if frozen:
        # Installed build:  %LOCALAPPDATA%\TinyNetUse\config.json
        return app_data / CONFIG_FILENAME
    # Source run:       %LOCALAPPDATA%\TinyNetUse\dev\config.json
    return app_data / "dev" / CONFIG_FILENAME


# Old location >> New location
# C:\Program Files\TinyNetUse\config.json >> C:\Users\Laween\AppData\Local\TinyNetUse\config.json
def _legacy_config_path() -> Path | None:
    frozen = bool(getattr(sys, "frozen", False))
    executable = Path(sys.executable)
    if not frozen or is_portable_mode(executable, frozen):
        return None
    return executable.parent / CONFIG_FILENAME


def _read_json(path: Path):
    # keep file parsing in one place so the load and legacy migration behave the same
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def _preserve_corrupt_file(path: Path) -> None:
    # keep the bad file available for diagnosis before replacing its settings, just in case
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    backup = path.with_name(f"{path.name}.corrupt-{stamp}")
    try:
        path.replace(backup)
    except OSError:
        pass


class Config:
    def __init__(self, path=None):
        # explicit paths are used by tests and must not trigger legacy discovery
        custom_path = path is not None
        self.path = Path(path) if custom_path else resolve_config_path()
        self.path.parent.mkdir(parents=True, exist_ok=True)

        legacy_path = None if custom_path else _legacy_config_path()
        if (
            legacy_path
            and legacy_path != self.path
            and legacy_path.is_file()
            and not self.path.exists()
        ):
            self._load_legacy(legacy_path)
        else:
            self._load()

    def _load(self) -> None:
        # create a usable config immediately when no file exists yet
        if not self.path.exists():
            self.data = default_config()
            self.save()
            return

        try:
            loaded = _read_json(self.path)
        except (json.JSONDecodeError, UnicodeDecodeError):
            # preserve malformed settings, then start from a clean configuration
            _preserve_corrupt_file(self.path)
            self.data = default_config()
            self.save()
            return

        self.data = validate_config(loaded)
        if self.data != loaded:
            self.save()

    def _load_legacy(self, legacy_path: Path) -> None:
        # import the old EXE-side file once, then continue using the resolved path
        try:
            loaded = _read_json(legacy_path)
        except (json.JSONDecodeError, UnicodeDecodeError):
            _preserve_corrupt_file(legacy_path)
            loaded = {}

        self.data = validate_config(loaded)
        self.save()

        # The AppData copy is safe now, so the old EXE-side file is no longer needed.
        try:
            legacy_path.unlink()
        except OSError:
            pass

    def save(self) -> None:
        # write beside the target and replace it only after the complete file is flushed
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.data = validate_config(self.data)
        temp_path = None

        try:
            with tempfile.NamedTemporaryFile(
                "w",
                encoding="utf-8",
                dir=self.path.parent,
                prefix=f".{self.path.name}.",
                suffix=".tmp",
                delete=False,
            ) as temp_file:
                temp_path = Path(temp_file.name)
                json.dump(self.data, temp_file, indent=2)
                temp_file.write("\n")
                temp_file.flush()
                os.fsync(temp_file.fileno())

            os.replace(temp_path, self.path)
        finally:
            if temp_path:
                temp_path.unlink(missing_ok=True)
