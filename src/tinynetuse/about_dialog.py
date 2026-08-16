"""TinyNetUse About dialog."""

from PySide6 import QtCore, QtWidgets

from tinynetuse.version import __version__


PROJECT_URL = "https://github.com/laween-alsulaivany/TinyNetUse"
RELEASES_URL = f"{PROJECT_URL}/releases"
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
        )
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
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)

    def _enable_links(self, label):
        label.setOpenExternalLinks(True)
        label.setTextInteractionFlags(
            QtCore.Qt.TextInteractionFlag.TextBrowserInteraction
        )
        label.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)
