"""Shared window geometry validation and recovery."""

import math
from numbers import Real

from PySide6 import QtCore, QtGui


DEFAULT_MARGIN = 10
MIN_VISIBLE_WIDTH = 48
MIN_VISIBLE_HEIGHT = 32
QT_COORD_LIMIT = 2_000_000_000


# Turn a saved [x, y, width, height] value into plain integers.
def parse_saved_geometry(value):
    if isinstance(value, QtCore.QRect):
        return value.x(), value.y(), value.width(), value.height()
    if not isinstance(value, (list, tuple)) or len(value) != 4:
        return None
    if any(
        not isinstance(item, Real)
        or isinstance(item, bool)
        or not math.isfinite(item)
        for item in value
    ):
        return None
    return tuple(int(item) for item in value)


# Get each monitor's usable area in Qt logical pixels.
def available_screen_geometries(screens=None):
    screens = QtGui.QGuiApplication.screens() if screens is None else screens
    return [QtCore.QRect(screen.availableGeometry()) for screen in screens]


# A usable patch this size is enough to drag a frameless window back.
def geometry_is_visible(rect, screens) -> bool:
    if not rect.isValid():
        return False
    visible_width = min(MIN_VISIBLE_WIDTH, rect.width())
    visible_height = min(MIN_VISIBLE_HEIGHT, rect.height())

    for screen in screens:
        overlap = rect.intersected(screen)
        if overlap.width() >= visible_width and overlap.height() >= visible_height:
            return True
    return False


# Keep restored sizes usable and no larger than a current monitor.
def _clamp_size(width, height, screens, minimum_size):
    max_width = max(screen.width() for screen in screens)
    max_height = max(screen.height() for screen in screens)
    min_width = min(max(1, minimum_size.width()), max_width)
    min_height = min(max(1, minimum_size.height()), max_height)
    width = min(max(int(width), min_width), max_width)
    height = min(max(int(height), min_height), max_height)
    return QtCore.QSize(width, height)


# Put a window at the lower-right of the primary screen.
def fallback_geometry(
    size,
    primary_screen,
    minimum_size,
    margin=DEFAULT_MARGIN,
    bottom_offset=0,
):
    margin = min(
        max(0, int(margin)),
        max(0, (primary_screen.width() - 1) // 2),
        max(0, (primary_screen.height() - 1) // 2),
    )
    usable_width = max(1, primary_screen.width() - margin * 2)
    usable_height = max(1, primary_screen.height() - margin * 2)
    bounded_screen = QtCore.QRect(
        primary_screen.x(), primary_screen.y(), usable_width, usable_height
    )
    bounded_size = _clamp_size(
        size.width(), size.height(), [bounded_screen], minimum_size
    )
    max_offset = max(
        0, primary_screen.height() - bounded_size.height() - margin * 2
    )
    bottom_offset = min(max(0, int(bottom_offset)), max_offset)
    x = primary_screen.x() + primary_screen.width() - bounded_size.width() - margin
    y = (
        primary_screen.y()
        + primary_screen.height()
        - bounded_size.height()
        - margin
        - bottom_offset
    )
    return QtCore.QRect(QtCore.QPoint(x, y), bounded_size)


# Validate saved geometry and recover it when its monitor is gone.
def recover_geometry(
    saved_geometry,
    screens,
    primary_screen,
    default_size,
    minimum_size,
):
    screens = [QtCore.QRect(screen) for screen in screens if screen.isValid()]
    primary_screen = QtCore.QRect(primary_screen)
    if not primary_screen.isValid() and screens:
        primary_screen = QtCore.QRect(screens[0])
    if not primary_screen.isValid():
        primary_screen = QtCore.QRect(
            0,
            0,
            max(default_size.width(), minimum_size.width()),
            max(default_size.height(), minimum_size.height()),
        )
    if not screens:
        screens = [primary_screen]

    parsed = parse_saved_geometry(saved_geometry)
    fallback_size = default_size
    if parsed:
        x, y, width, height = parsed
        size = _clamp_size(width, height, screens, minimum_size)
        fallback_size = size
        coordinates_fit_qt = (
            -QT_COORD_LIMIT <= x <= QT_COORD_LIMIT
            and -QT_COORD_LIMIT <= y <= QT_COORD_LIMIT
        )
        if coordinates_fit_qt:
            candidate = QtCore.QRect(QtCore.QPoint(x, y), size)
            if geometry_is_visible(candidate, screens):
                return candidate

    return fallback_geometry(fallback_size, primary_screen, minimum_size)


# Restore a QWidget using all screens currently known to Qt.
def restore_window_geometry(window, saved_geometry, default_size, minimum_size):
    screens = available_screen_geometries()
    primary = QtGui.QGuiApplication.primaryScreen()
    primary_rect = primary.availableGeometry() if primary else QtCore.QRect()
    rect = recover_geometry(
        saved_geometry, screens, primary_rect, default_size, minimum_size
    )
    window.setGeometry(rect)
    return rect


# Dock a QWidget to its normal fallback position.
def dock_window(window, size, minimum_size, bottom_offset=0):
    screens = available_screen_geometries()
    primary = QtGui.QGuiApplication.primaryScreen()
    primary_rect = primary.availableGeometry() if primary else QtCore.QRect()
    if not primary_rect.isValid() and screens:
        primary_rect = screens[0]
    if not primary_rect.isValid():
        primary_rect = QtCore.QRect(0, 0, size.width(), size.height())
    rect = fallback_geometry(
        size, primary_rect, minimum_size, bottom_offset=bottom_offset
    )
    window.setGeometry(rect)
    return rect


# Store geometry as JSON-friendly values.
def geometry_values(rect):
    return [rect.x(), rect.y(), rect.width(), rect.height()]
