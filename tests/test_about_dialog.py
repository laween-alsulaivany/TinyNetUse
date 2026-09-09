from pathlib import Path
from unittest.mock import Mock

import pytest
from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtCore import Qt

from tinynetuse.about_dialog import (
    AboutDialog,
    PROJECT_URL,
    QT_FOR_PYTHON_URL,
    LATEST_RELEASE_PAGE_URL,
    REPORT_BUG_URL,
    RELEASES_URL,
)
from tinynetuse.update_check import CheckStatus, UpdateCheckResult
from tinynetuse.version import __version__


ROOT = Path(__file__).parents[1]


def test_about_dialog_shows_project_information(qtbot):
    parent = QtWidgets.QWidget()
    parent.setWindowIcon(
        QtGui.QIcon(str(ROOT / "assets/windows-classic/TinyNetUse.ico"))
    )
    dialog = AboutDialog(parent)
    qtbot.addWidget(parent)
    qtbot.addWidget(dialog)

    assert dialog.windowTitle() == "About TinyNetUse"
    assert dialog.name_label.text() == "TinyNetUse"
    assert dialog.version_label.text() == f"Version {__version__}"
    assert dialog.description_label.text() == (
        "A lightweight Windows network-speed overlay."
    )
    assert "No telemetry or analytics." == dialog.privacy_label.text()
    assert not dialog.icon_label.pixmap().isNull()

    text = " ".join(
        label.text()
        for label in dialog.findChildren(QtWidgets.QLabel)
    )
    assert "Laween Al-Sulaivany" in text
    assert "License: MIT" in text
    assert PROJECT_URL in dialog.links_label.text()
    assert RELEASES_URL in dialog.links_label.text()
    assert REPORT_BUG_URL in dialog.links_label.text()
    assert QT_FOR_PYTHON_URL in dialog.framework_label.text()
    assert "LGPLv3/GPLv3" in dialog.framework_label.text()
    assert dialog.links_label.openExternalLinks()
    assert dialog.framework_label.openExternalLinks()
    assert dialog.links_label.focusPolicy() == Qt.FocusPolicy.StrongFocus
    assert dialog.framework_label.focusPolicy() == Qt.FocusPolicy.StrongFocus


def test_about_dialog_close_button_uses_native_dialog_behavior(qtbot):
    dialog = AboutDialog()
    qtbot.addWidget(dialog)
    dialog.show()

    close_button = dialog.buttons.button(
        QtWidgets.QDialogButtonBox.StandardButton.Close
    )
    qtbot.mouseClick(close_button, Qt.MouseButton.LeftButton)

    assert dialog.result() == QtWidgets.QDialog.DialogCode.Rejected


def test_about_dialog_checks_for_updates_only_when_requested(qtbot, monkeypatch):
    dialog = AboutDialog()
    qtbot.addWidget(dialog)
    dialog.show()
    qtbot.waitExposed(dialog)
    check = Mock(return_value=True)
    monkeypatch.setattr(dialog.update_checker, "check", check)

    assert dialog.check_updates_button.isEnabled()
    qtbot.mouseClick(dialog.check_updates_button, Qt.MouseButton.LeftButton)

    check.assert_called_once_with()
    assert not dialog.check_updates_button.isEnabled()

    messages = []

    def close_result_message():
        message = QtWidgets.QApplication.activeModalWidget()
        assert isinstance(message, QtWidgets.QMessageBox)
        messages.append((message.windowTitle(), message.text()))
        message.accept()

    QtCore.QTimer.singleShot(0, close_result_message)
    dialog.update_checker.finished.emit(UpdateCheckResult(CheckStatus.UP_TO_DATE))

    assert dialog.check_updates_button.isEnabled()
    assert messages == [("Update Check", "TinyNetUse is up to date.")]


@pytest.mark.parametrize("choose_open_releases", [False, True])
def test_about_dialog_opens_fixed_release_url_only_after_confirmation(
    qtbot, monkeypatch, choose_open_releases
):
    dialog = AboutDialog()
    qtbot.addWidget(dialog)
    dialog.show()
    open_url = Mock()
    monkeypatch.setattr(QtGui.QDesktopServices, "openUrl", open_url)

    def respond_to_update_prompt():
        message = QtWidgets.QApplication.activeModalWidget()
        assert isinstance(message, QtWidgets.QMessageBox)
        if choose_open_releases:
            open_releases = next(
                button
                for button in message.buttons()
                if button.text() == "Open Releases"
            )
            qtbot.mouseClick(open_releases, Qt.MouseButton.LeftButton)
        else:
            message.reject()

    QtCore.QTimer.singleShot(0, respond_to_update_prompt)

    dialog._show_update_result(
        UpdateCheckResult(CheckStatus.UPDATE_AVAILABLE, "999.999.999")
    )

    if choose_open_releases:
        open_url.assert_called_once_with(QtCore.QUrl(LATEST_RELEASE_PAGE_URL))
    else:
        open_url.assert_not_called()
