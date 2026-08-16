import pytest
from PySide6.QtCore import QRect, QSize

from tinynetuse.geometry import (
    fallback_geometry,
    geometry_is_visible,
    parse_saved_geometry,
    recover_geometry,
)


PRIMARY = QRect(0, 0, 1920, 1080)
DEFAULT_SIZE = QSize(600, 320)
MINIMUM_SIZE = QSize(200, 100)


def recover(saved, screens, primary=PRIMARY):
    return recover_geometry(
        saved,
        screens,
        primary,
        DEFAULT_SIZE,
        MINIMUM_SIZE,
    )


@pytest.mark.parametrize(
    ("screens", "saved"),
    [
        ([PRIMARY], [100, 100, 600, 320]),
        ([PRIMARY, QRect(1920, 0, 1920, 1080)], [2100, 100, 600, 320]),
        ([PRIMARY, QRect(-1920, 0, 1920, 1080)], [-1800, 100, 600, 320]),
        ([PRIMARY, QRect(0, -1080, 1920, 1080)], [100, -900, 600, 320]),
    ],
)
def test_valid_geometry_is_kept_on_any_monitor(screens, saved):
    assert recover(saved, screens) == QRect(*saved)


def test_partially_visible_window_is_not_moved():
    saved = [1700, 100, 600, 320]

    assert recover(saved, [PRIMARY]) == QRect(*saved)


def test_tiny_offscreen_sliver_is_not_enough_to_recover_window():
    saved = [1900, 100, 600, 320]

    assert not geometry_is_visible(QRect(*saved), [PRIMARY])
    assert recover(saved, [PRIMARY]) == QRect(1310, 750, 600, 320)


def test_removed_monitor_recovers_to_primary_and_keeps_size():
    saved = [2100, 100, 500, 260]

    assert recover(saved, [PRIMARY]) == QRect(1410, 810, 500, 260)


def test_completely_offscreen_window_recovers_to_primary():
    saved = [5000, -3000, 600, 320]

    assert recover(saved, [PRIMARY]) == QRect(1310, 750, 600, 320)


def test_resolution_change_recovers_inside_new_available_area():
    smaller_primary = QRect(0, 0, 1280, 720)
    saved = [1400, 700, 600, 320]

    assert recover(saved, [smaller_primary], smaller_primary) == QRect(
        670, 390, 600, 320
    )


@pytest.mark.parametrize(
    ("saved", "expected_size"),
    [
        ([100, 100, 1, 1], QSize(200, 100)),
        ([100, 100, 50_000, 50_000], QSize(1920, 1080)),
        ([100, 100, -1, 0], QSize(200, 100)),
    ],
)
def test_invalid_or_absurd_sizes_are_clamped(saved, expected_size):
    assert recover(saved, [PRIMARY]).size() == expected_size


@pytest.mark.parametrize(
    "saved",
    [None, [], [1, 2, 3], ["1", 2, 3, 4], [True, 2, 3, 4]],
)
def test_malformed_saved_geometry_uses_default(saved):
    expected = fallback_geometry(DEFAULT_SIZE, PRIMARY, MINIMUM_SIZE)

    assert recover(saved, [PRIMARY]) == expected


def test_extreme_coordinates_do_not_overflow_qrect():
    saved = [10**100, -(10**100), 500, 260]

    assert recover(saved, [PRIMARY]) == QRect(1410, 810, 500, 260)


def test_parse_saved_qrect():
    assert parse_saved_geometry(QRect(-10, -20, 300, 200)) == (
        -10,
        -20,
        300,
        200,
    )


def test_fallback_can_leave_room_above_another_window():
    rect = fallback_geometry(
        QSize(140, 60),
        PRIMARY,
        QSize(100, 40),
        bottom_offset=330,
    )

    assert rect == QRect(1770, 680, 140, 60)


def test_reset_positions_updates_both_windows_and_saves_once(monkeypatch):
    import tinynetuse.app as app_module

    class FakeConfig:
        def __init__(self):
            self.data = {}
            self.save_count = 0

        def save(self):
            self.save_count += 1

    class FakeGraph:
        def isVisible(self):
            return True

        def reset_position(self):
            return QRect(1310, 750, 600, 320)

    dock_calls = []

    def fake_dock(window, size, minimum_size, bottom_offset=0):
        dock_calls.append(bottom_offset)
        return QRect(1770, 680, size.width(), size.height())

    monkeypatch.setattr(app_module, "dock_window", fake_dock)
    config = FakeConfig()
    widget = type(
        "FakeWidget",
        (),
        {
            "config": config,
            "graph_window": FakeGraph(),
            "size": lambda self: QSize(140, 60),
        },
    )()

    app_module.TinyNetUseWidget.reset_window_positions(widget)

    assert dock_calls == [330]
    assert config.data["widget_geometry"] == [1770, 680, 140, 60]
    assert config.data["graph_geometry"] == [1310, 750, 600, 320]
    assert config.save_count == 1
