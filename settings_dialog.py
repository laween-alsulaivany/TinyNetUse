# settings_dialog.py — Settings modal dialog. Reads from and writes back to Config.

from PyQt5 import QtWidgets, QtGui
from PyQt5.QtGui import QColor
from config import Config
from startup import install_startup, remove_startup


class SettingsDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_widget = parent
        self.config = (
            parent.config if parent and hasattr(parent, "config") else Config()
        )
        self.setWindowTitle("TinyNetUse Settings")
        # Icon comes from QApplication.setWindowIcon() set in main.py.
        # Setting it here with a bare relative path produced a null icon that
        # silently overrode the app-level one.
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
            ["auto", "B/s", "KB/s", "MB/s", "b/s", "Kib/s", "Mib/s"]
        )
        layout.addRow("Speed Unit:", self.unit_combo)

        # Decimal Precision
        self.prec_spin = QtWidgets.QSpinBox()
        self.prec_spin.setRange(0, 2)
        layout.addRow("Decimal Precision:", self.prec_spin)

        # Notify Threshold
        self.threshold_spin = QtWidgets.QDoubleSpinBox()
        self.threshold_spin.setSingleStep(0.1)
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
        self.btn_font.clicked.connect(lambda: self._pick("font_color", self.btn_font))
        layout.addRow(QtWidgets.QLabel("Font Color:"), self.btn_font)

        # Bold checkbox
        self.bold_check = QtWidgets.QCheckBox("Bold Text")
        self.bold_check.setChecked(self.config.data.get("font_bold", True))
        layout.addWidget(self.bold_check)

        # Alert Color
        self.btn_alert = QtWidgets.QPushButton()
        self.btn_alert.clicked.connect(
            lambda: self._pick("alert_color", self.btn_alert)
        )
        layout.addRow("Alert Color:", self.btn_alert)
        # Download Color
        self.btn_dl = QtWidgets.QPushButton()
        self.btn_dl.clicked.connect(lambda: self._pick("download_color", self.btn_dl))
        layout.addRow("Download Color:", self.btn_dl)
        # Upload Color
        self.btn_ul = QtWidgets.QPushButton()
        self.btn_ul.clicked.connect(lambda: self._pick("upload_color", self.btn_ul))
        layout.addRow("Upload Color:", self.btn_ul)

        # Launch at Startup
        self.boot_chk = QtWidgets.QCheckBox("Launch at Startup")
        layout.addRow(self.boot_chk)

        # Sync threshold suffix/range whenever the unit changes so it always
        # shows the threshold in the same unit the widget is displaying.
        self._threshold_unit = "MB/s"
        self._update_threshold_display("MB/s")
        self.unit_combo.currentTextChanged.connect(self._on_unit_changed)

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
        # Convert stored MB/s threshold to whatever unit is currently displayed.
        stored_mb = d["notify_threshold"].get("download") or 0.0
        self.threshold_spin.setValue(
            self._threshold_mb_to_display(stored_mb, self._threshold_unit)
        )
        self.opacity_spin.setValue(d.get("opacity", 0.8) * 100)
        self.font_combo.setCurrentFont(QtGui.QFont(d.get("font", "Segoe UI")))
        self.font_size_spin.setValue(d.get("font_size", 10))
        self.boot_chk.setChecked(d["start_on_boot"])

        for key, btn in [
            ("alert_color", self.btn_alert),
            ("download_color", self.btn_dl),
            ("upload_color", self.btn_ul),
            ("font_color", self.btn_font),
        ]:
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

    def _on_unit_changed(self, new_unit):
        # Rescale the threshold value so the logical threshold stays the same.
        # Threshold is always stored and compared in MB/s internally.
        old_mb = self._threshold_display_to_mb(
            self.threshold_spin.value(), self._threshold_unit
        )
        self._threshold_unit = new_unit
        self._update_threshold_display(new_unit)
        self.threshold_spin.setValue(self._threshold_mb_to_display(old_mb, new_unit))

    def _update_threshold_display(self, unit):
        """Sync the threshold spin's suffix, range, and step for the given unit."""
        label = unit if unit != "auto" else "MB/s"
        max_val = self._threshold_mb_to_display(1000.0, unit)
        step = max(0.01, max_val / 10000)
        self.threshold_spin.setSuffix(f" {label}")
        self.threshold_spin.setRange(0.0, max_val)
        self.threshold_spin.setSingleStep(round(step, 4))

    def _threshold_display_to_mb(self, val, unit):
        """Convert a threshold value in the display unit to MB/s (internal storage)."""
        factors = {
            "auto": 1,
            "B/s": 1 / (1 << 20),
            "KB/s": 1 / 1024,
            "MB/s": 1,
            "b/s": 1 / (8 * (1 << 20)),
            "Kib/s": 1 / (8 * 1024),
            "Mib/s": 1 / 8,
        }
        return val * factors.get(unit, 1)

    def _threshold_mb_to_display(self, mb_val, unit):
        """Convert a MB/s threshold value to the given display unit."""
        factors = {
            "auto": 1,
            "B/s": 1 << 20,
            "KB/s": 1024,
            "MB/s": 1,
            "b/s": 8 * (1 << 20),
            "Kib/s": 8 * 1024,
            "Mib/s": 8,
        }
        return mb_val * factors.get(unit, 1)

    def accept(self):
        d = self.config.data
        d["update_interval"] = self.interval.value()
        d["unit"] = self.unit_combo.currentText()
        d["precision"] = self.prec_spin.value()
        raw_thr = self.threshold_spin.value()
        mb_thr = self._threshold_display_to_mb(raw_thr, self._threshold_unit)
        d["notify_threshold"]["download"] = mb_thr if mb_thr > 0 else None
        d["opacity"] = self.opacity_spin.value() / 100.0
        d["font"] = self.font_combo.currentFont().family()
        d["font_size"] = self.font_size_spin.value()
        d["start_on_boot"] = self.boot_chk.isChecked()
        d["font_bold"] = self.bold_check.isChecked()

        self.config.save()

        if d["start_on_boot"]:
            try:
                install_startup()
            except Exception as e:
                QtWidgets.QMessageBox.warning(
                    self, "Startup Error", f"Could not create startup shortcut:\n{e}"
                )
                d["start_on_boot"] = False
                self.config.save()
        else:
            try:
                remove_startup()
            except Exception:
                pass  # file already gone, nothing to do

        if self.parent_widget and hasattr(self.parent_widget, "apply_settings"):
            self.parent_widget.apply_settings()

        super().accept()
