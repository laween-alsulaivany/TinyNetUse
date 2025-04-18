import sys
from pathlib import Path


def format_speed(bps, unit="auto", precision=1):
    """Format bytes per second into a human‑readable string."""
    units = [("B/s", 1), ("KB/s", 1 << 10), ("MB/s", 1 << 20)]
    if unit in ("KB/s", "MB/s"):
        target = next(u for u in units if u[0] == unit)
    else:  # auto
        target = max(units, key=lambda u: bps / u[1] >= 1)
    value = bps / target[1]
    return f"{value:.{precision}f} {target[0]}"


def resource_path(rel_path):
    """
    Get the absolute path to a resource, whether running from source
    or from a PyInstaller bundle.
    """
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).parent))
    return base / rel_path
