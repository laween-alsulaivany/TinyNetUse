# settings_dialog.py

from PyQt5 import QtWidgets, QtGui
from PyQt5.QtGui import QColor
from config import Config
from startup import install_startup, remove_startup


class SettingsDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_widget = parent
        self.config = parent.config if parent and hasattr(
            parent, "config") else Config()
        self.setWindowTitle("TinyNetUse Settings")
        self.setWindowIcon(QtGui.QIcon("assets/icon.ico"))
        self._build_ui()
        self._load_values()

    def _build_ui(self):
        self.setModal(True)
        layout = QtWidgets.QFormLayout(self)
        d = self.config.data

        # Update Interval
        self.interval = QtWidgets.QDoubleSpinBox()
        self.interval.setRange(0.1, 60.0)
        self.interval.setSingleStep(0.1)
        layout.addRow("Update Interval (s):", self.interval)

        # Speed Unit
        self.unit_combo = QtWidgets.QComboBox()
        self.unit_combo.addItems(
            ["auto", "B/s", "KB/s", "MB/s", "b/s", "Kib/s", "Mib/s"])
        layout.addRow("Speed Unit:", self.unit_combo)

        # Decimal Precision
        self.prec_spin = QtWidgets.QSpinBox()
        self.prec_spin.setRange(0, 2)
        layout.addRow("Decimal Precision:", self.prec_spin)

        # Notify Threshold
        self.threshold_spin = QtWidgets.QDoubleSpinBox()
        self.threshold_spin.setRange(0.0, 1000.0)
        self.threshold_spin.setSingleStep(0.1)
        # TODO: Make this dynamic based on unit
        self.threshold_spin.setSuffix(" MB/s")
        layout.addRow("Alert if Download >", self.threshold_spin)

        # Opacity
        self.opacity_spin = QtWidgets.QDoubleSpinBox()
        self.opacity_spin.setRange(0, 100)
        self.opacity_spin.setSingleStep(10)
        self.opacity_spin.setSuffix(" %")
        layout.addRow("Opacity:", self.opacity_spin)

        # Font
        self.font_combo = QtWidgets.QFontComboBox()
        self.font_combo.setCurrentFont(QtGui.QFont(d.get("font", "Segoe UI")))
        layout.addRow(QtWidgets.QLabel("Font:"), self.font_combo)

        # Font size
        self.font_size_spin = QtWidgets.QSpinBox()
        self.font_size_spin.setRange(6, 72)
        self.font_size_spin.setValue(d.get("font_size", 10))
        layout.addRow(QtWidgets.QLabel("Font Size:"), self.font_size_spin)

        self.btn_font = QtWidgets.QPushButton()
        self.btn_font.clicked.connect(
            lambda: self._pick("font_color", self.btn_font))
        layout.addRow(QtWidgets.QLabel("Font Color:"), self.btn_font)

        # Bold checkbox
        self.bold_check = QtWidgets.QCheckBox("Bold Text")
        self.bold_check.setChecked(self.config.data.get("font_bold", True))
        layout.addWidget(self.bold_check)

        # Alert Color
        self.btn_alert = QtWidgets.QPushButton()
        self.btn_alert.clicked.connect(
            lambda: self._pick("alert_color", self.btn_alert))
        layout.addRow("Alert Color:", self.btn_alert)
        # Download Color
        self.btn_dl = QtWidgets.QPushButton()
        self.btn_dl.clicked.connect(
            lambda: self._pick("download_color", self.btn_dl))
        layout.addRow("Download Color:", self.btn_dl)
        # Upload Color
        self.btn_ul = QtWidgets.QPushButton()
        self.btn_ul.clicked.connect(
            lambda: self._pick("upload_color", self.btn_ul))
        layout.addRow("Upload Color:", self.btn_ul)

        # Launch at Startup
        self.boot_chk = QtWidgets.QCheckBox("Launch at Startup")
        layout.addRow(self.boot_chk)

        # Dialog buttons
        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )

        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def _load_values(self):
        d = self.config.data
        self.interval.setValue(d["update_interval"])
        self.unit_combo.setCurrentText(d["unit"])
        self.prec_spin.setValue(d["precision"])
        thr = d["notify_threshold"].get("download") or 0.0
        self.threshold_spin.setValue(thr)
        self.opacity_spin.setValue(d.get("opacity", 0.8) * 100)
        self.font_combo.setCurrentFont(QtGui.QFont(d.get("font", "Segoe UI")))
        self.font_size_spin.setValue(d.get("font_size", 10))
        self.boot_chk.setChecked(d["start_on_boot"])

        for key, btn in [("alert_color", self.btn_alert), ("download_color", self.btn_dl), ("upload_color", self.btn_ul), ("font_color", self.btn_font)]:
            col = d.get(key)
            btn.setStyleSheet(f"background:{col};border:1px solid #888;")

    # color picker
    def _pick(self, key, btn):
        init = QColor(self.config.data.get(key))
        c = QtWidgets.QColorDialog.getColor(init, self, "Pick Color")
        if c.isValid():
            hexc = c.name()
            self.config.data[key] = hexc
            btn.setStyleSheet(f"background:{hexc};border:1px solid #888;")

    def _open_graph(self):
        from graph_window import GraphWindow
        gw = GraphWindow(self, config=self.config)
        gw.exec_()

    def accept(self):
        d = self.config.data
        d["update_interval"] = self.interval.value()
        d["unit"] = self.unit_combo.currentText()
        d["precision"] = self.prec_spin.value()
        raw_thr = self.threshold_spin.value()
        d["notify_threshold"]["download"] = raw_thr if raw_thr > 0 else None
        d["opacity"] = self.opacity_spin.value() / 100.0
        d["font"] = self.font_combo.currentFont().family()
        d["font_size"] = self.font_size_spin.value()
        d["start_on_boot"] = self.boot_chk.isChecked()
        d["font_bold"] = self.bold_check.isChecked()

        self.config.save()

        if d["start_on_boot"]:
            install_startup()
        else:
            remove_startup()

        if self.parent_widget and hasattr(self.parent_widget, "apply_settings"):
            self.parent_widget.apply_settings()

        super().accept()
