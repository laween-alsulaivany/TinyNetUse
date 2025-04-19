# settings_dialog.py

from PyQt5 import QtWidgets
from PyQt5.QtGui import QColor
from config import Config
from startup import install_startup, remove_startup

class SettingsDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_widget = parent
        self.config = parent.config if parent and hasattr(parent, "config") else Config()
        self._build_ui()
        self._load_values()
        self.setWindowTitle("TinyNetUse Settings")

    def _build_ui(self):
        self.setModal(True)
        layout = QtWidgets.QFormLayout(self)

        # Update Interval
        self.interval_spin = QtWidgets.QDoubleSpinBox()
        self.interval_spin.setRange(0.5, 5.0)
        self.interval_spin.setSingleStep(0.1)
        layout.addRow("Update Interval (s):", self.interval_spin)

        # Speed Unit
        self.unit_combo = QtWidgets.QComboBox()
        self.unit_combo.addItems(["auto", "B/s", "KB/s", "MB/s", "b/s", "Kib/s", "Mib/s"])
        layout.addRow("Speed Unit:", self.unit_combo)

        # Decimal Precision
        self.prec_spin = QtWidgets.QSpinBox()
        self.prec_spin.setRange(0, 2)
        layout.addRow("Decimal Precision:", self.prec_spin)

        # Notify Threshold
        self.threshold_spin = QtWidgets.QDoubleSpinBox()
        self.threshold_spin.setRange(0.0, 1000.0)
        self.threshold_spin.setSingleStep(0.1)
        self.threshold_spin.setSuffix(" MB/s")
        layout.addRow("Alert if Download >", self.threshold_spin)

        # Alert Color Picker
        self.color_btn = QtWidgets.QPushButton("Pick Alert Color")
        self.color_lbl = QtWidgets.QLabel()
        self.color_lbl.setFixedWidth(60)
        color_layout = QtWidgets.QHBoxLayout()
        color_layout.addWidget(self.color_btn)
        color_layout.addWidget(self.color_lbl)
        layout.addRow("Alert Color:", color_layout)
        self.color_btn.clicked.connect(self._pick_color)
        # Download Color Picker
        self.dl_color_btn = QtWidgets.QPushButton("Pick Download Color")
        self.dl_color_lbl = QtWidgets.QLabel()
        self.dl_color_lbl.setFixedWidth(60)
        dl_color_layout = QtWidgets.QHBoxLayout()
        dl_color_layout.addWidget(self.dl_color_btn)
        dl_color_layout.addWidget(self.dl_color_lbl)
        layout.addRow("Download Line Color:", dl_color_layout)
        self.dl_color_btn.clicked.connect(self._pick_dl_color)

        # Upload Color Picker
        self.ul_color_btn = QtWidgets.QPushButton("Pick Upload Color")
        self.ul_color_lbl = QtWidgets.QLabel()
        self.ul_color_lbl.setFixedWidth(60)
        ul_color_layout = QtWidgets.QHBoxLayout()
        ul_color_layout.addWidget(self.ul_color_btn)
        ul_color_layout.addWidget(self.ul_color_lbl)
        layout.addRow("Upload Line Color:", ul_color_layout)
        self.ul_color_btn.clicked.connect(self._pick_ul_color)
        # Start Minimized
        self.min_chk = QtWidgets.QCheckBox("Start Minimized")
        layout.addRow(self.min_chk)

        # Launch at Startup
        self.boot_chk = QtWidgets.QCheckBox("Launch at Windows Startup")
        layout.addRow(self.boot_chk)

        # View Graph
        self.view_graph_btn = QtWidgets.QPushButton("View Graph")
        self.view_graph_btn.clicked.connect(self._open_graph)
        layout.addRow(self.view_graph_btn)

        # Dialog buttons
        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def _load_values(self):
        d = self.config.data
        self.interval_spin.setValue(d["update_interval"])
        self.unit_combo.setCurrentText(d["unit"])
        self.prec_spin.setValue(d["precision"])
        thr = d["notify_threshold"].get("download") or 0.0
        self.threshold_spin.setValue(thr)
        self.min_chk.setChecked(d["start_minimized"])
        self.boot_chk.setChecked(d["start_on_boot"])
        self._set_color_label(d.get("alert_color", "#FF5555"))
        self._set_dl_color_label(d.get("download_color", "#4FC3F7"))
        self._set_ul_color_label(d.get("upload_color", "#FF8A65"))

    def _pick_color(self):
        d = self.config.data
        initial = d.get("alert_color", "#FF5555")
        color = QtWidgets.QColorDialog.getColor(QColor(initial), self, "Pick Alert Color")
        if color.isValid():
            hex_color = color.name()
            d["alert_color"] = hex_color
            self._set_color_label(hex_color)
    def _pick_dl_color(self):
        d = self.config.data
        initial = d.get("download_color", "#4FC3F7")
        color = QtWidgets.QColorDialog.getColor(QColor(initial), self, "Pick Download Color")
        if color.isValid():
            hex_color = color.name()
            d["download_color"] = hex_color
            self._set_dl_color_label(hex_color)

    def _pick_ul_color(self):
        d = self.config.data
        initial = d.get("upload_color", "#FF8A65")
        color = QtWidgets.QColorDialog.getColor(QColor(initial), self, "Pick Upload Color")
        if color.isValid():
            hex_color = color.name()
            d["upload_color"] = hex_color
            self._set_ul_color_label(hex_color)

    def _set_dl_color_label(self, color):
        self.dl_color_lbl.setStyleSheet(f"background: {color}; border: 1px solid #888;")
        self.dl_color_lbl.setText(color)

    def _set_ul_color_label(self, color):
        self.ul_color_lbl.setStyleSheet(f"background: {color}; border: 1px solid #888;")
        self.ul_color_lbl.setText(color)


    def _set_color_label(self, color):
        self.color_lbl.setStyleSheet(f"background: {color}; border: 1px solid #888;")
        self.color_lbl.setText(color)

    def _open_graph(self):
        from graph_window import GraphWindow
        gw = GraphWindow(self, config=self.config)
        gw.exec_()

    def accept(self):
        # 1) Update config dict
        d = self.config.data
        d["update_interval"] = self.interval_spin.value()
        d["unit"]            = self.unit_combo.currentText()
        d["precision"]       = self.prec_spin.value()
        raw_thr = self.threshold_spin.value()
        d["notify_threshold"]["download"] = raw_thr if raw_thr > 0 else None
        d["start_minimized"] = self.min_chk.isChecked()
        d["start_on_boot"]   = self.boot_chk.isChecked()
        d["alert_color"]     = self.color_lbl.text() or "#FF5555"
        d["download_color"]  = self.dl_color_lbl.text() or "#4FC3F7"
        d["upload_color"]    = self.ul_color_lbl.text() or "#FF8A65"

        # 2) Persist
        self.config.save()

        # 3) Autostart toggle
        if d["start_on_boot"]:
            install_startup()
        else:
            remove_startup()

        # 4) Immediately tell the main widget to re‑apply its settings
        if self.parent_widget and hasattr(self.parent_widget, "apply_settings"):
            self.parent_widget.apply_settings()

        super().accept()

