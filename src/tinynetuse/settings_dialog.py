"""TinyNetUse settings dialog."""

from copy import deepcopy

from PySide6 import QtGui, QtWidgets
from PySide6.QtGui import QColor

from tinynetuse.config import Config, default_config, validate_config
from tinynetuse.network import AUTO_ADAPTER, AUTO_ADAPTER_LABEL
from tinynetuse.startup import disable_startup, enable_startup, is_startup_enabled, startup_shortcut_exists
from tinynetuse.units import SUPPORTED_UNITS, THRESHOLD_UNIT, threshold_from_display, threshold_to_display


COLOR_KEYS = ("alert_color", "download_color", "upload_color", "font_color")
RESET_KEYS = (
    "font",
    "font_size",
    "font_color",
    "font_bold",
    "update_interval",
    "opacity",
    "reduce_opacity_on_hover",
    "alert_color",
    "download_color",
    "upload_color",
    "network_adapter",
    "unit",
    "precision",
    "notify_threshold",
)


class SettingsDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_widget = parent
        self.config = (
            parent.config if parent and hasattr(parent, "config") else Config()
        )
        self.working = deepcopy(self.config.data)
        self._startup_enabled = is_startup_enabled()
        self._working_startup = self._startup_enabled

        self.setWindowTitle("TinyNetUse Settings")
        self._build_ui()
        self._load_values()

    def _build_ui(self):
        self.setModal(True)
        layout = QtWidgets.QFormLayout(self)
        d = self.working

        self.adapter_combo = QtWidgets.QComboBox()
        adapter_help = (
            "<p style='white-space: normal; width: 320px;'>"
            "Auto monitors the active network connection. Select an adapter "
            "manually if you want to monitor a specific Ethernet, Wi-Fi, VPN, "
            "or virtual interface.</p>"
        )
        adapter_label = QtWidgets.QLabel("Network Adapter:")
        adapter_label.setBuddy(self.adapter_combo)
        self.adapter_help_button = QtWidgets.QToolButton()
        self.adapter_help_button.setIcon(
            self.style().standardIcon(
                QtWidgets.QStyle.StandardPixmap.SP_MessageBoxInformation
            )
        )
        self.adapter_help_button.setAutoRaise(True)
        self.adapter_help_button.setFixedSize(20, 20)
        self.adapter_help_button.setToolTip(adapter_help)
        self.adapter_help_button.setAccessibleName("Network Adapter Help")
        self.adapter_help_button.setAccessibleDescription(
            "Explains how to select a network adapter."
        )
        adapter_label_layout = QtWidgets.QHBoxLayout()
        adapter_label_layout.setContentsMargins(0, 0, 0, 0)
        adapter_label_layout.setSpacing(2)
        adapter_label_layout.addWidget(adapter_label)
        adapter_label_layout.addWidget(self.adapter_help_button)
        adapter_label_layout.addStretch()
        adapter_label_widget = QtWidgets.QWidget()
        adapter_label_widget.setLayout(adapter_label_layout)
        layout.addRow(adapter_label_widget, self.adapter_combo)
        self._refresh_adapter_list()

        self.interval = QtWidgets.QDoubleSpinBox()
        self.interval.setRange(0.1, 60.0)
        self.interval.setSingleStep(0.1)
        layout.addRow("Update Interval (s):", self.interval)

        self.unit_combo = QtWidgets.QComboBox()
        self.unit_combo.addItems(SUPPORTED_UNITS)
        layout.addRow("Speed Unit:", self.unit_combo)

        self.prec_spin = QtWidgets.QSpinBox()
        self.prec_spin.setRange(0, 2)
        layout.addRow("Decimal Precision:", self.prec_spin)

        self.download_threshold_spin = QtWidgets.QDoubleSpinBox()
        self.upload_threshold_spin = QtWidgets.QDoubleSpinBox()
        self.threshold_spins = {
            "download": self.download_threshold_spin,
            "upload": self.upload_threshold_spin,
        }
        layout.addRow("Highlight when download exceeds:", self.download_threshold_spin)
        layout.addRow("Highlight when upload exceeds:", self.upload_threshold_spin)

        self.opacity_spin = QtWidgets.QDoubleSpinBox()
        self.opacity_spin.setRange(20, 100)
        self.opacity_spin.setSingleStep(10)
        self.opacity_spin.setSuffix(" %")
        layout.addRow("Opacity:", self.opacity_spin)

        self.hover_opacity_check = QtWidgets.QCheckBox("Reduce opacity on hover")
        self.hover_opacity_help_button = QtWidgets.QToolButton()
        self.hover_opacity_help_button.setIcon(
            self.style().standardIcon(
                QtWidgets.QStyle.StandardPixmap.SP_MessageBoxInformation
            )
        )
        self.hover_opacity_help_button.setAutoRaise(True)
        self.hover_opacity_help_button.setFixedSize(20, 20)
        self.hover_opacity_help_button.setToolTip(
            "<p style='white-space: normal; width: 320px;'>"
            "When enabled, the overlay uses 25% opacity while the pointer is "
            "over it. It returns to the configured opacity when the pointer "
            "leaves.</p>"
        )
        self.hover_opacity_help_button.setAccessibleName("Hover Opacity Help")
        self.hover_opacity_help_button.setAccessibleDescription(
            "Explains the overlay opacity change while the pointer is over it."
        )
        hover_opacity_layout = QtWidgets.QHBoxLayout()
        hover_opacity_layout.setContentsMargins(0, 0, 0, 0)
        hover_opacity_layout.setSpacing(2)
        hover_opacity_layout.addWidget(self.hover_opacity_check)
        hover_opacity_layout.addWidget(self.hover_opacity_help_button)
        hover_opacity_layout.addStretch()
        hover_opacity_widget = QtWidgets.QWidget()
        hover_opacity_widget.setLayout(hover_opacity_layout)
        layout.addRow(hover_opacity_widget)

        self.font_combo = QtWidgets.QFontComboBox()
        self.font_combo.setCurrentFont(QtGui.QFont(d["font"]))
        layout.addRow("Font:", self.font_combo)

        self.font_size_spin = QtWidgets.QSpinBox()
        self.font_size_spin.setRange(6, 72)
        layout.addRow("Font Size:", self.font_size_spin)

        self.btn_font = QtWidgets.QPushButton()
        self.btn_font.clicked.connect(lambda: self._pick("font_color", self.btn_font))
        layout.addRow("Font Color:", self.btn_font)

        self.bold_check = QtWidgets.QCheckBox("Bold Text")
        layout.addWidget(self.bold_check)

        self.btn_alert = QtWidgets.QPushButton()
        self.btn_alert.clicked.connect(
            lambda: self._pick("alert_color", self.btn_alert)
        )
        layout.addRow("Highlight Color:", self.btn_alert)

        self.btn_dl = QtWidgets.QPushButton()
        self.btn_dl.clicked.connect(lambda: self._pick("download_color", self.btn_dl))
        layout.addRow("Download Color:", self.btn_dl)

        self.btn_ul = QtWidgets.QPushButton()
        self.btn_ul.clicked.connect(lambda: self._pick("upload_color", self.btn_ul))
        layout.addRow("Upload Color:", self.btn_ul)

        self.boot_chk = QtWidgets.QCheckBox("Launch at Startup")
        layout.addRow(self.boot_chk)

        # set the initial threshold unit for the display
        self._threshold_unit = THRESHOLD_UNIT
        self._update_threshold_display(THRESHOLD_UNIT)
        self.unit_combo.currentTextChanged.connect(self._on_unit_changed)

        self.buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok
            | QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        self.reset_button = self.buttons.addButton(
            "Reset Settings",
            QtWidgets.QDialogButtonBox.ButtonRole.ResetRole,
        )
        self.reset_button.clicked.connect(self._reset_settings)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addRow(self.buttons)

    def _color_buttons(self):
        return {
            "alert_color": self.btn_alert,
            "download_color": self.btn_dl,
            "upload_color": self.btn_ul,
            "font_color": self.btn_font,
        }

    def _load_values(self):
        d = self.working
        adapter_index = self.adapter_combo.findData(d["network_adapter"])
        self.adapter_combo.setCurrentIndex(max(0, adapter_index))
        self.interval.setValue(d["update_interval"])
        self.unit_combo.setCurrentText(d["unit"])
        self.prec_spin.setValue(d["precision"])
        for direction, spin in self.threshold_spins.items():
            spin.setValue(
                threshold_to_display(
                    d["notify_threshold"].get(direction),
                    self._threshold_unit,
                )
                or 0.0
            )
        self.opacity_spin.setValue(d["opacity"] * 100)
        self.hover_opacity_check.setChecked(d["reduce_opacity_on_hover"])
        self.font_combo.setCurrentFont(QtGui.QFont(d["font"]))
        self.font_size_spin.setValue(d["font_size"])
        self.bold_check.setChecked(d["font_bold"])
        self.boot_chk.setChecked(self._working_startup)

        for key, button in self._color_buttons().items():
            button.setStyleSheet(
                f"background:{d[key]};border:1px solid #888;"
            )

    def _pick(self, key, button):
        color = QtWidgets.QColorDialog.getColor(
            QColor(self.working[key]), self, "Pick Color"
        )
        if color.isValid():
            self.working[key] = color.name()
            button.setStyleSheet(
                f"background:{self.working[key]};border:1px solid #888;"
            )

    def _on_unit_changed(self, new_unit):
        # Keep the threshold value equivalent when switching units.
        thresholds = {
            direction: threshold_from_display(spin.value(), self._threshold_unit)
            for direction, spin in self.threshold_spins.items()
        }
        self._threshold_unit = new_unit
        self._update_threshold_display(new_unit)
        for direction, spin in self.threshold_spins.items():
            spin.setValue(
                threshold_to_display(thresholds[direction], new_unit) or 0.0
            )

    def _update_threshold_display(self, unit):
        label = unit if unit != "auto" else THRESHOLD_UNIT
        max_value = threshold_to_display(1000, unit)
        step = max(0.01, max_value / 10000)
        for spin in self.threshold_spins.values():
            spin.setSuffix(f" {label}")
            spin.setRange(0.0, max_value)
            spin.setSingleStep(round(step, 4))

    def _read_values(self):
        d = self.working
        d["network_adapter"] = self.adapter_combo.currentData()
        d["update_interval"] = self.interval.value()
        d["unit"] = self.unit_combo.currentText()
        d["precision"] = self.prec_spin.value()
        for direction, spin in self.threshold_spins.items():
            d["notify_threshold"][direction] = threshold_from_display(
                spin.value(), self._threshold_unit
            )
        d["opacity"] = self.opacity_spin.value() / 100.0
        d["reduce_opacity_on_hover"] = self.hover_opacity_check.isChecked()
        d["font"] = self.font_combo.currentFont().family()
        d["font_size"] = self.font_size_spin.value()
        d["font_bold"] = self.bold_check.isChecked()

    # Re-read adapters every time a new Settings dialog opens.
    def _refresh_adapter_list(self):
        monitor = getattr(self.parent_widget, "sampler", None)
        adapters = monitor.available_adapters() if monitor else []

        self.adapter_combo.clear()
        self.adapter_combo.addItem(AUTO_ADAPTER_LABEL, AUTO_ADAPTER)
        for name in adapters:
            self.adapter_combo.addItem(name, name)

        selected = self.working.get("network_adapter", AUTO_ADAPTER)
        if self.adapter_combo.findData(selected) < 0:
            self.working["network_adapter"] = AUTO_ADAPTER

    def _reset_settings(self):
        defaults = default_config()
        for key in RESET_KEYS:
            self.working[key] = deepcopy(defaults[key])
        self._working_startup = False
        self._load_values()

    def accept(self):
        self._read_values()
        approved = validate_config(self.working)
        startup_enabled = self.boot_chk.isChecked()

        previous = deepcopy(self.config.data)
        self.config.data = approved
        try:
            self.config.save()
        except OSError as error:
            self.config.data = previous
            QtWidgets.QMessageBox.warning(
                self,
                "Settings Error",
                f"Could not save TinyNetUse settings:\n{error}",
            )
            return

        if self.parent_widget and hasattr(self.parent_widget, "apply_settings"):
            self.parent_widget.apply_settings()

        if startup_enabled != self._startup_enabled or (
            not startup_enabled and startup_shortcut_exists()
        ):
            try:
                if startup_enabled:
                    enable_startup()
                else:
                    disable_startup()
            except Exception as error:
                self._startup_enabled = is_startup_enabled()
                self._working_startup = self._startup_enabled
                self.boot_chk.setChecked(self._startup_enabled)
                QtWidgets.QMessageBox.warning(
                    self,
                    "Startup Error",
                    f"Could not update the Startup shortcut:\n{error}",
                )
            else:
                self._startup_enabled = startup_enabled

        super().accept()
