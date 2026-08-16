from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from PySide6 import QtWidgets

from tinynetuse.app import TinyNetUseWidget


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


def test_overlay_visibility_action_hides_or_restores():
    visible = SimpleNamespace(
        isVisible=lambda: True,
        hide=Mock(),
        show_overlay=Mock(),
    )
    hidden = SimpleNamespace(
        isVisible=lambda: False,
        hide=Mock(),
        show_overlay=Mock(),
    )

    TinyNetUseWidget.toggle_overlay_visibility(visible)
    TinyNetUseWidget.toggle_overlay_visibility(hidden)

    visible.hide.assert_called_once()
    visible.show_overlay.assert_not_called()
    hidden.hide.assert_not_called()
    hidden.show_overlay.assert_called_once()


def test_reopening_graph_reuses_the_existing_window():
    graph = Mock()
    graph.isVisible.return_value = False
    owner = SimpleNamespace(
        graph_visible=False,
        graph_window=graph,
        config=SimpleNamespace(data={}, save=Mock()),
    )

    TinyNetUseWidget.toggle_graph(owner, True)

    assert owner.graph_window is graph
    graph.clear_history.assert_called_once()
    graph.show.assert_called_once()
    graph.raise_.assert_called_once()
    graph.activateWindow.assert_called_once()
    owner.config.save.assert_called_once()


@pytest.mark.parametrize(
    ("sent", "received", "download_threshold", "upload_threshold", "active"),
    [
        (50, 50, None, None, False),
        (50, 101, 100, None, True),
        (101, 50, None, 100, True),
        (100, 100, 100, 100, False),
    ],
)
def test_overlay_highlights_for_either_threshold(
    sent, received, download_threshold, upload_threshold, active
):
    sampler = Mock()
    sampler.source_revision = 0
    sampler.selected_adapter = "auto"
    sampler.sample.return_value = (sent, received)
    owner = SimpleNamespace(
        sampler=sampler,
        config=SimpleNamespace(data={"network_adapter": "auto"}, save=Mock()),
        graph_window=None,
        dl_label=Mock(),
        ul_label=Mock(),
        unit="B/s",
        precision=0,
        download_threshold=download_threshold,
        upload_threshold=upload_threshold,
        update=Mock(),
    )

    TinyNetUseWidget._update_speeds(owner)

    assert owner._alert_active is active
