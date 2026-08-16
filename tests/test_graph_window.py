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
