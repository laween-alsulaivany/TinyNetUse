"""Network rate conversion and formatting."""


SUPPORTED_UNITS = ["auto", "B/s", "KB/s", "MB/s", "b/s", "Kib/s", "Mib/s"]

KIB = 1024
MIB = 1024 * 1024

# TinyNetUse has always used binary values for its KB/MB labels.
BYTES_PER_UNIT = {
    "B/s": 1.0,
    "KB/s": KIB,
    "MB/s": MIB,
    "b/s": 1.0 / 8,
    "Kib/s": KIB / 8,
    "Mib/s": MIB / 8,
}

# Thresholds are saved as MB/s for compatibility with existing configs.
THRESHOLD_UNIT = "MB/s"


# Converts bytes/sec to one fixed unit.
def convert_rate(rate_bytes_per_sec: float, unit: str) -> float:
    return max(0.0, rate_bytes_per_sec) / BYTES_PER_UNIT[unit]


# Picks B/s, KB/s, or MB/s for auto display.
def select_auto_unit(rate_bytes_per_sec: float) -> str:
    rate = max(0.0, rate_bytes_per_sec)
    if rate >= MIB:
        return "MB/s"
    if rate >= KIB:
        return "KB/s"
    # B/s keeps zero and very small rates readable instead of rounding KB/s to zero.
    return "B/s"


# Formats a rate for the overlay and graph labels.
def format_rate(rate_bytes_per_sec: float, unit: str, precision: int) -> str:
    if unit == "auto":
        unit = select_auto_unit(rate_bytes_per_sec)
    value = convert_rate(rate_bytes_per_sec, unit)
    return f"{value:.{precision}f} {unit}"


# Formats a rate using the auto unit rules. meant for testing, not used in the main application.
def format_auto_rate(rate_bytes_per_sec: float, precision: int) -> str:
    return format_rate(rate_bytes_per_sec, "auto", precision)


# Note: All thresholds are internally stored as MB/s in the configuration for consistency. The two methods below
# handle conversion between the display value and the stored MB/s threshold.


# Converts the settings value to the stored MB/s threshold.
def threshold_from_display(value: float | None, unit: str) -> float | None:
    if value is None or value <= 0:
        return None
    if unit == "auto":
        unit = THRESHOLD_UNIT
    bytes_per_sec = value * BYTES_PER_UNIT[unit]
    return bytes_per_sec / MIB


# Converts the stored MB/s threshold for the settings field.
def threshold_to_display(value: float | None, unit: str) -> float | None:
    if value is None:
        return None
    if unit == "auto":
        unit = THRESHOLD_UNIT
    return convert_rate(value * MIB, unit)


# Converts the stored threshold before comparing it with the live rates.
def threshold_bytes_per_sec(value: float | None) -> float | None:
    if value is None:
        return None
    return value * MIB
