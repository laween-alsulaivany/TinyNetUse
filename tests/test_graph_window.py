from unittest.mock import Mock

from PySide6 import QtWidgets

from tinynetuse.config import Config
from tinynetuse.graph_window import GraphWindow


def test_graph_uses_samples_supplied_by_the_main_monitor(tmp_path, qtbot):
    config = Config(tmp_path / "config.json")
    config.data["graph_history"] = 3
    config.save()
    graph = GraphWindow(config=config)
    qtbot.addWidget(graph)

    graph.add_sample(100, 250)

    assert list(graph.sent_hist) == [0.0, 0.0, 100]
    assert list(graph.recv_hist) == [0.0, 0.0, 250]
    assert graph.last_ul == 100
    assert graph.last_dl == 250


def test_graph_history_is_cleared_when_network_source_changes(tmp_path, qtbot):
    graph = GraphWindow(config=Config(tmp_path / "config.json"))
    qtbot.addWidget(graph)
    graph.add_sample(100, 250)

    graph.clear_history()

    assert not any(graph.sent_hist)
    assert not any(graph.recv_hist)
    assert graph.last_ul == 0
    assert graph.last_dl == 0
    assert not graph.has_samples


def test_paused_graph_keeps_its_samples_and_resets_when_reopened(
    tmp_path, qtbot
):
    graph = GraphWindow(config=Config(tmp_path / "config.json"))
    qtbot.addWidget(graph)
    graph.add_sample(100, 250)

    graph._toggle_pause(True)
    graph.add_sample(200, 500)

    assert graph.paused
    assert graph.last_ul == 100
    assert graph.last_dl == 250

    graph.reset_for_reopen()

    assert not graph.paused
    assert not graph.has_samples
    assert not any(graph.sent_hist)
    assert not any(graph.recv_hist)


def test_graph_waits_for_a_sample_before_plotting_history(tmp_path, qtbot):
    graph = GraphWindow(config=Config(tmp_path / "config.json"))
    qtbot.addWidget(graph)

    assert not graph.has_samples

    graph.add_sample(0, 0)

    assert graph.has_samples


def test_graph_renders_waiting_and_sampled_states(tmp_path, qtbot):
    graph = GraphWindow(config=Config(tmp_path / "config.json"))
    qtbot.addWidget(graph)
    graph.resize(320, 200)
    graph.show()
    qtbot.waitExposed(graph)

    waiting_image = graph.grab().toImage()
    graph.add_sample(100, 250)
    sampled_image = graph.grab().toImage()

    assert waiting_image.width() == graph.width() * waiting_image.devicePixelRatio()
    assert waiting_image.height() == graph.height() * waiting_image.devicePixelRatio()
    assert sampled_image.width() == graph.width() * sampled_image.devicePixelRatio()
    assert sampled_image.height() == graph.height() * sampled_image.devicePixelRatio()
    assert waiting_image != sampled_image


def test_graph_resizes_history_without_discarding_recent_samples(
    tmp_path, qtbot
):
    config = Config(tmp_path / "config.json")
    config.data["graph_history"] = 3
    config.save()
    graph = GraphWindow(config=config)
    qtbot.addWidget(graph)
    graph.add_sample(10, 100)
    graph.add_sample(20, 200)

    config.data["graph_history"] = 5
    graph.apply_settings()

    assert list(graph.sent_hist) == [0.0, 0.0, 0.0, 10, 20]
    assert list(graph.recv_hist) == [0.0, 0.0, 0.0, 100, 200]

    config.data["graph_history"] = 2
    graph.apply_settings()

    assert list(graph.sent_hist) == [10, 20]
    assert list(graph.recv_hist) == [100, 200]


def test_swapping_graph_colors_updates_the_persisted_preferences(
    tmp_path, qtbot
):
    config = Config(tmp_path / "config.json")
    config.data["download_color"] = "#123456"
    config.data["upload_color"] = "#abcdef"
    config.save()
    graph = GraphWindow(config=config)
    qtbot.addWidget(graph)

    graph._swap_colors()

    assert graph.line_dl.name() == "#abcdef"
    assert graph.line_ul.name() == "#123456"
    assert config.data["download_color"] == "#abcdef"
    assert config.data["upload_color"] == "#123456"


def test_graph_labels_use_the_application_font_not_overlay_preferences(
    tmp_path, qtbot
):
    config = Config(tmp_path / "config.json")
    config.data.update({"font": "Segoe UI", "font_bold": True, "font_size": 14})
    graph = GraphWindow(config=config)
    qtbot.addWidget(graph)
    graph.resize(600, 320)

    label_font = graph._label_font()
    application_font = QtWidgets.QApplication.font()

    assert label_font.family() == application_font.family()
    assert label_font.bold() == application_font.bold()
    assert label_font.pointSize() == 12


def test_graph_auto_unit_respects_the_configured_minimum(tmp_path, qtbot):
    config = Config(tmp_path / "config.json")
    config.data.update({"unit": "auto", "auto_unit_minimum": "KB/s"})
    graph = GraphWindow(config=config)
    qtbot.addWidget(graph)
    graph.add_sample(100, 500)

    assert graph._display_unit() == "KB/s"


def test_graph_close_notifies_owner_without_saving_twice(tmp_path, qtbot):
    config = Config(tmp_path / "config.json")
    graph = GraphWindow(config=config)
    qtbot.addWidget(graph)
    config.save = Mock()
    closed = Mock()
    graph.closed.connect(closed)

    graph.close()

    closed.assert_called_once()
    config.save.assert_not_called()
