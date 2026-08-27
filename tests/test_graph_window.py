from unittest.mock import Mock

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
