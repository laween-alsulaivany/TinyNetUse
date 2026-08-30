from types import SimpleNamespace
from unittest.mock import Mock

from PySide6 import QtGui, QtWidgets

import tinynetuse.app as app_module
from tinynetuse.app import TinyNetUseWidget
from tinynetuse.config import Config


class StubSampler:
    def __init__(self, samples):
        self.selected_adapter = "Ethernet"
        self.resolved_adapter = None
        self.source_revision = 0
        self._samples = iter(samples)

    def set_adapter(self, adapter):
        return False

    def sample(self):
        return next(self._samples)


def make_widget(tmp_path, qtbot, monkeypatch, samples):
    config = Config(tmp_path / "config.json")
    config.data.update(
        {
            "network_adapter": "Ethernet",
            "unit": "MB/s",
            "precision": 1,
            "notify_threshold": {"download": 1, "upload": None},
            "alert_color": "#123456",
        }
    )
    config.save()
    sampler = StubSampler(samples)
    monkeypatch.setattr(app_module, "Config", lambda: config)
    monkeypatch.setattr(app_module, "NetworkSampler", lambda adapter: sampler)
    monkeypatch.setattr(TinyNetUseWidget, "_setup_tray", lambda self: None)
    widget = TinyNetUseWidget()
    qtbot.addWidget(widget)
    return widget, sampler


def menu_owner(visible=True):
    return SimpleNamespace(
        isVisible=lambda: visible,
        graph_visible=True,
        always_on_top=False,
        locked=True,
        toggle_overlay_visibility=Mock(),
        toggle_graph=Mock(),
        toggle_always_on_top=Mock(),
        toggle_lock=Mock(),
        open_settings=Mock(),
        reset_window_positions=Mock(),
        open_about=Mock(),
    )


def menu_labels(menu):
    return [
        "<separator>" if action.isSeparator() else action.text()
        for action in menu.actions()
    ]


def test_main_menu_is_short_and_logically_ordered(qtbot):
    menu = QtWidgets.QMenu()
    qtbot.addWidget(menu)
    owner = menu_owner()

    TinyNetUseWidget._populate_app_menu(owner, menu)

    assert menu_labels(menu) == [
        "Hide Overlay",
        "Show Graph",
        "Always On Top",
        "Lock Position",
        "Settings",
        "Reset Window Positions",
        "About TinyNetUse",
        "<separator>",
        "Quit",
    ]
    assert menu.actions()[1].isChecked()
    assert not menu.actions()[2].isChecked()
    assert menu.actions()[3].isChecked()


def test_menu_offers_show_when_overlay_is_hidden(qtbot):
    menu = QtWidgets.QMenu()
    qtbot.addWidget(menu)

    TinyNetUseWidget._populate_app_menu(menu_owner(visible=False), menu)

    assert menu.actions()[0].text() == "Show Overlay"


def test_overlay_visibility_toggle_changes_a_real_widget(
    tmp_path, qtbot, monkeypatch
):
    widget, _ = make_widget(
        tmp_path,
        qtbot,
        monkeypatch,
        [(0, 0), (0, 0)],
    )
    widget.show()
    qtbot.waitUntil(widget.isVisible)

    widget.toggle_overlay_visibility()
    assert not widget.isVisible()

    widget.toggle_overlay_visibility()
    assert widget.isVisible()


def test_reopening_graph_reuses_and_clears_the_real_window(
    tmp_path, qtbot, monkeypatch
):
    widget, _ = make_widget(
        tmp_path,
        qtbot,
        monkeypatch,
        [(100, 250), (100, 250)],
    )
    widget.toggle_graph(True)
    graph = widget.graph_window
    qtbot.addWidget(graph)
    widget._update_speeds()

    assert graph.last_ul == 100
    assert graph.last_dl == 250

    widget.toggle_graph(False)
    widget.toggle_graph(True)

    assert widget.graph_window is graph
    assert graph.isVisible()
    assert not any(graph.sent_hist)
    assert not any(graph.recv_hist)


def test_overlay_updates_labels_graph_and_alert_rendering(
    tmp_path, qtbot, monkeypatch
):
    widget, _ = make_widget(
        tmp_path,
        qtbot,
        monkeypatch,
        [(1_048_576, 2_097_152), (1_048_576, 2_097_152)],
    )
    widget.resize(240, 120)
    widget.show()
    qtbot.waitUntil(widget.isVisible)
    widget.toggle_graph(True)
    graph = widget.graph_window
    qtbot.addWidget(graph)

    widget._update_speeds()

    assert widget.dl_label.text() == f"{chr(0x2193)} 2.0 MB/s"
    assert widget.ul_label.text() == f"{chr(0x2191)} 1.0 MB/s"
    assert graph.last_dl == 2_097_152
    assert graph.last_ul == 1_048_576
    assert widget._alert_active
    assert widget.grab().toImage().pixelColor(120, 100) == QtGui.QColor(
        "#123456"
    )


def test_tray_tooltip_shows_the_auto_resolved_adapter(
    tmp_path, qtbot, monkeypatch
):
    widget, sampler = make_widget(
        tmp_path,
        qtbot,
        monkeypatch,
        [(0, 0), (0, 0)],
    )
    widget.tray = Mock()
    sampler.resolved_adapter = "Wi-Fi"

    widget._update_tray_tooltip()

    widget.tray.setToolTip.assert_called_once_with("TinyNetUse - Auto: Wi-Fi")


def test_tray_tooltip_stays_default_for_manual_adapter(
    tmp_path, qtbot, monkeypatch
):
    widget, sampler = make_widget(
        tmp_path,
        qtbot,
        monkeypatch,
        [(0, 0), (0, 0)],
    )
    widget.tray = Mock()
    sampler.resolved_adapter = None

    widget._update_tray_tooltip()

    widget.tray.setToolTip.assert_called_once_with("TinyNetUse")


def test_overlay_font_settings_do_not_change_the_application_font(
    tmp_path, qtbot, monkeypatch
):
    application_font = QtWidgets.QApplication.font()
    widget, _ = make_widget(
        tmp_path,
        qtbot,
        monkeypatch,
        [(0, 0), (0, 0)],
    )
    widget.config.data.update(
        {"font": "Segoe UI", "font_size": 14, "font_bold": False}
    )

    widget.apply_settings()

    assert QtWidgets.QApplication.font().key() == application_font.key()
    assert widget.dl_label.font().family() == "Segoe UI"
    assert widget.dl_label.font().pointSize() == 14
    assert not widget.dl_label.font().bold()


def test_overlay_font_change_expands_and_saves_minimum_geometry(
    tmp_path, qtbot, monkeypatch
):
    widget, _ = make_widget(
        tmp_path,
        qtbot,
        monkeypatch,
        [(0, 0), (0, 0)],
    )
    widget.resize(100, 40)
    widget.config.data.update(
        {"font_size": 72, "widget_geometry": [0, 0, 100, 40]}
    )

    widget.apply_settings()

    layout_minimum = widget.layout().minimumSize()
    assert widget.minimumSize() == layout_minimum.expandedTo(
        app_module.OVERLAY_MINIMUM_SIZE
    )
    assert widget.width() >= widget.minimumWidth()
    assert widget.height() >= widget.minimumHeight()
    assert widget.config.data["widget_geometry"] == [
        widget.x(),
        widget.y(),
        widget.width(),
        widget.height(),
    ]
