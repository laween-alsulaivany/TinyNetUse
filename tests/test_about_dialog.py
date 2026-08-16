from pathlib import Path

from PySide6 import QtGui, QtWidgets
from PySide6.QtCore import Qt

from tinynetuse.about_dialog import (
    AboutDialog,
    PROJECT_URL,
    QT_FOR_PYTHON_URL,
    RELEASES_URL,
)
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
