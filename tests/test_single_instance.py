import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from PySide6 import QtWidgets

from tinynetuse.app import TinyNetUseWidget
from tinynetuse.single_instance import SingleInstance


@pytest.fixture(scope="module")
def app():
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


# Process Qt events until an IPC signal arrives or the test times out.
def wait_for(check, app, timeout=1):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        app.processEvents()
        if check():
            return True
        time.sleep(0.01)
    return False


# Run the client off the GUI thread, like a real second process would.
def launch_second(instance_id, app, command="show"):
    with ThreadPoolExecutor(max_workers=1) as pool:
        result = pool.submit(lambda: SingleInstance(instance_id).start(command))
        assert wait_for(result.done, app, timeout=3)
        return result.result()


def test_first_launch_owns_the_instance(app):
    owner = SingleInstance(f"TinyNetUse.Test.{uuid.uuid4()}")
    try:
        assert owner.start()
    finally:
        owner.close()


def test_repeated_launches_notify_the_first_instance(app):
    instance_id = f"TinyNetUse.Test.{uuid.uuid4()}"
    owner = SingleInstance(instance_id)
    activations = []
    owner.show_requested.connect(lambda: activations.append(True))

    try:
        assert owner.start()

        for _ in range(3):
            assert not launch_second(instance_id, app)

        assert wait_for(lambda: len(activations) == 3, app)
    finally:
        owner.close()


def test_instance_can_start_after_the_owner_exits(app):
    instance_id = f"TinyNetUse.Test.{uuid.uuid4()}"
    old_owner = SingleInstance(instance_id)
    assert old_owner.start()
    old_owner.close()

    new_owner = SingleInstance(instance_id)
    try:
        assert new_owner.start()
    finally:
        new_owner.close()


def test_quit_command_releases_the_instance(app):
    instance_id = f"TinyNetUse.Test.{uuid.uuid4()}"
    owner = SingleInstance(instance_id)
    owner.quit_requested.connect(owner.close)
    assert owner.start()

    assert not launch_second(instance_id, app, "quit")

    replacement = SingleInstance(instance_id)
    try:
        assert replacement.start()
    finally:
        replacement.close()


@pytest.mark.parametrize("state", ["hidden", "minimized"])
def test_activation_shows_the_overlay(app, state):
    widget = QtWidgets.QWidget()
    if state == "minimized":
        widget.showMinimized()
    else:
        widget.hide()
    app.processEvents()

    TinyNetUseWidget.show_overlay(widget)
    app.processEvents()

    assert widget.isVisible()
    assert not widget.isMinimized()
    widget.close()


def test_installer_uses_ipc_shutdown_instead_of_app_mutex():
    installer = Path("packaging/installer.iss").read_text(encoding="utf-8")

    assert "AppMutex=" not in installer
    assert 'Parameters: "--quit"' in installer
    assert "CloseApplications=yes" in installer
