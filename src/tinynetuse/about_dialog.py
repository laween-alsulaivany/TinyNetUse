"""TinyNetUse About dialog."""

from PySide6 import QtCore, QtGui, QtWidgets

from tinynetuse.update_check import (
    CheckStatus,
    LATEST_RELEASE_PAGE_URL,
    UpdateChecker,
)
from tinynetuse.version import __version__


PROJECT_URL = "https://github.com/laween-alsulaivany/TinyNetUse"
RELEASES_URL = f"{PROJECT_URL}/releases"
REPORT_BUG_URL = f"{PROJECT_URL}/issues/new?template=bug_report.yml"
QT_FOR_PYTHON_URL = "https://doc.qt.io/qtforpython-6/"


class AboutDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("About TinyNetUse")
        self.setModal(True)
        self.setMinimumWidth(360)

        icon = parent.windowIcon() if parent else QtWidgets.QApplication.windowIcon()
        self.setWindowIcon(icon)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 16)
        layout.setSpacing(10)

        header = QtWidgets.QHBoxLayout()
        header.setSpacing(14)

        self.icon_label = QtWidgets.QLabel()
        self.icon_label.setAccessibleName("TinyNetUse application icon")
        self.icon_label.setPixmap(icon.pixmap(64, 64))
        self.icon_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)
        header.addWidget(self.icon_label)

        title_layout = QtWidgets.QVBoxLayout()
        title_layout.setSpacing(3)

        self.name_label = QtWidgets.QLabel("TinyNetUse")
        name_font = self.name_label.font()
        name_font.setPointSize(name_font.pointSize() + 4)
        name_font.setBold(True)
        self.name_label.setFont(name_font)
        title_layout.addWidget(self.name_label)

        self.version_label = QtWidgets.QLabel(f"Version {__version__}")
        title_layout.addWidget(self.version_label)

        self.description_label = QtWidgets.QLabel(
            "A lightweight Windows network-speed overlay."
        )
        self.description_label.setWordWrap(True)
        title_layout.addWidget(self.description_label)
        header.addLayout(title_layout, 1)
        layout.addLayout(header)

        details = QtWidgets.QLabel(
            "Copyright © 2025-2026 Laween Al-Sulaivany<br>License: MIT"
        )
        details.setTextFormat(QtCore.Qt.TextFormat.RichText)
        layout.addWidget(details)

        self.links_label = QtWidgets.QLabel(
            f'<a href="{PROJECT_URL}">GitHub Repository</a>'
            " &nbsp;|&nbsp; "
            f'<a href="{RELEASES_URL}">View Releases</a>'
            " &nbsp;|&nbsp; "
            f'<a href="{REPORT_BUG_URL}">Report a Bug</a>'
        )
        self.links_label.setWordWrap(True)
        self._enable_links(self.links_label)
        layout.addWidget(self.links_label)

        self.privacy_label = QtWidgets.QLabel("No telemetry or analytics.")
        layout.addWidget(self.privacy_label)

        self.framework_label = QtWidgets.QLabel(
            f'Built with <a href="{QT_FOR_PYTHON_URL}">PySide6 '
            "(Qt for Python)</a>, available under LGPLv3/GPLv3 and "
            "commercial licenses."
        )
        self.framework_label.setWordWrap(True)
        self._enable_links(self.framework_label)
        layout.addWidget(self.framework_label)

        self.buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Close
        )
        self.check_updates_button = self.buttons.addButton(
            "Check for Updates",
            QtWidgets.QDialogButtonBox.ButtonRole.ActionRole,
        )
        self.update_checker = UpdateChecker(__version__, self)
        self.check_updates_button.clicked.connect(self._check_for_updates)
        self.update_checker.finished.connect(self._show_update_result)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)

    def _enable_links(self, label):
        label.setOpenExternalLinks(True)
        label.setTextInteractionFlags(
            QtCore.Qt.TextInteractionFlag.TextBrowserInteraction
        )
        label.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)

    def _check_for_updates(self):
        if self.update_checker.check():
            self.check_updates_button.setEnabled(False)

    def _show_update_result(self, result):
        self.check_updates_button.setEnabled(True)
        if not self.isVisible():
            return

        if result.status is CheckStatus.UP_TO_DATE:
            QtWidgets.QMessageBox.information(
                self, "Update Check", "TinyNetUse is up to date."
            )
        elif result.status is CheckStatus.UPDATE_AVAILABLE:
            message = QtWidgets.QMessageBox(self)
            message.setWindowTitle("Update Available")
            message.setText(f"Version {result.version} is available.")
            open_releases = message.addButton(
                "Open Releases", QtWidgets.QMessageBox.ButtonRole.ActionRole
            )
            message.addButton(QtWidgets.QMessageBox.StandardButton.Close)
            message.exec()
            if message.clickedButton() is open_releases:
                QtGui.QDesktopServices.openUrl(
                    QtCore.QUrl(LATEST_RELEASE_PAGE_URL)
                )
        elif result.status is CheckStatus.NETWORK_ERROR:
            QtWidgets.QMessageBox.information(
                self,
                "Update Check",
                "Unable to check for updates. Check your connection and try again.",
            )
        else:
            QtWidgets.QMessageBox.information(
                self,
                "Update Check",
                "GitHub could not complete the update check. Try again later.",
            )

    def done(self, result):
        self.update_checker.cancel()
        super().done(result)
