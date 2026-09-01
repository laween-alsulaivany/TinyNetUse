"""Application startup, overlay widget, tray icon, and update loop."""

import sys
from pathlib import Path

# PySide6 imports for Qt GUI elements.
from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtCore import Qt, QRectF

from tinynetuse.about_dialog import AboutDialog
from tinynetuse.config import Config
from tinynetuse.geometry import dock_window, geometry_values, restore_window_geometry
from tinynetuse.graph_window import GraphWindow
from tinynetuse.network import NetworkSampler
from tinynetuse.settings_dialog import SettingsDialog
from tinynetuse.single_instance import SingleInstance
from tinynetuse.units import format_rate, threshold_bytes_per_sec
from tinynetuse.version import __version__


OVERLAY_DEFAULT_SIZE = QtCore.QSize(140, 60)
OVERLAY_MINIMUM_SIZE = QtCore.QSize(100, 40)
HOVER_OPACITY = 0.25

# row indicator bars live in the left margin, left of the label text
ROW_INDICATOR_X = 6.0
ROW_INDICATOR_WIDTH = 4.0
ROW_INDICATOR_TEXT_GAP = 6.0


def _asset_path(relative: str) -> str:
    # PyInstaller extracts bundled files to _MEIPASS.
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).parents[2]))
    return str(base / relative)


class TinyNetUseWidget(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()

        # ── Load Config & State ──
        self.config = Config()
        self.locked = False

        # ── Window Setup ──
        d = self.config.data
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setMinimumSize(OVERLAY_MINIMUM_SIZE)
        self.resize(OVERLAY_DEFAULT_SIZE)
        base_flags = Qt.FramelessWindowHint | Qt.Tool
        self.setWindowFlags(base_flags | (Qt.WindowStaysOnTopHint if d.get("widget_always_on_top") else 0))
        self.setWindowOpacity(d.get("opacity", 1.0))
        self.always_on_top = d.get("widget_always_on_top", True)

        # ── App Icon ──
        app_icon = QtGui.QIcon()
        for _s in [16, 20, 24, 32, 48, 64, 128, 256]:
            app_icon.addFile(
                _asset_path(f"assets/windows-classic/png/app-icon-{_s}.png"),
                QtCore.QSize(_s, _s),
            )
        self.setWindowIcon(app_icon)
        QtWidgets.QApplication.setWindowIcon(app_icon)

        # ── Labels ──
        layout = QtWidgets.QVBoxLayout(self)
        left_margin = ROW_INDICATOR_X + ROW_INDICATOR_WIDTH + ROW_INDICATOR_TEXT_GAP
        layout.setContentsMargins(int(left_margin), 8, 8, 8)
        layout.setSpacing(2)
        self.dl_label = QtWidgets.QLabel()
        self.ul_label = QtWidgets.QLabel()
        for lbl in (self.dl_label, self.ul_label):
            # Dynamic initial color
            lbl.setStyleSheet(f"color: {d.get('font_color', 'white')}")
            layout.addWidget(lbl)

        self.sampler = NetworkSampler(d.get("network_adapter", "auto"))
        if d.get("network_adapter") != self.sampler.selected_adapter:
            d["network_adapter"] = self.sampler.selected_adapter
            self.config.save()

        # ── Update Timer ──
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self._update_speeds)

        restored = restore_window_geometry(
            self,
            d.get("widget_geometry"),
            OVERLAY_DEFAULT_SIZE,
            OVERLAY_MINIMUM_SIZE,
        )
        restored_values = geometry_values(restored)
        if d.get("widget_geometry") != restored_values:
            d["widget_geometry"] = restored_values
            self.config.save()

        # ── Locked? ──
        self.locked = bool(d.get("widget_locked", False))

        # ── Drag support ──
        self._drag_offset = None
        self._pointer_over_overlay = False

        # ── Resizing support ──
        self._resizing = False
        self._resize_start_pos = None
        self._resize_start_geom = None

        # ── Graph Window ──

        self.graph_window = None
        self.graph_visible = d.get("graph_visible", False)
        if self.graph_visible:
            self.graph_window = GraphWindow(parent=self, config=self.config)
            self.graph_window.closed.connect(self._on_graph_closed)
            self.graph_window.show()

        # ── Apply current settings ──
        self.apply_settings()

        # ── System Tray ──
        self._setup_tray()

    def contextMenuEvent(self, event):
        menu = QtWidgets.QMenu(self)
        self._populate_app_menu(menu)
        menu.exec(event.globalPos())

    def toggle_graph(self, visible):
        if visible:
            self.graph_visible = True
            self.config.data["graph_visible"] = True
            self.config.save()
            if self.graph_window is None:
                self.graph_window = GraphWindow(parent=self, config=self.config)
                self.graph_window.closed.connect(self._on_graph_closed)
            elif not self.graph_window.isVisible():
                self.graph_window.reset_for_reopen()
            self.graph_window.show()
            self.graph_window.raise_()
            self.graph_window.activateWindow()
        else:
            if self.graph_window:
                self.graph_window.close()
            else:
                self._on_graph_closed()

    def toggle_always_on_top(self, on: bool):
        self.always_on_top = on
        f = self.windowFlags() & ~Qt.WindowStaysOnTopHint
        if on:
            f |= Qt.WindowStaysOnTopHint
        self.setWindowFlags(f)
        self.show()
        self.raise_()
        self.activateWindow()
        self.config.data["widget_always_on_top"] = on
        self.config.save()

    def toggle_lock(self, lock: bool):
        self.locked = lock
        self.config.data["widget_locked"] = lock
        self.config.save()

    def toggle_click_through(self, enabled: bool):
        if enabled and self.reduce_opacity_on_hover:
            QtWidgets.QMessageBox.information(
                self,
                "Incompatible Overlay Options",
                "Click Through Overlay has disabled Reduce opacity on hover. "
                "Both options cannot be enabled because a click-through "
                "overlay cannot detect the pointer.",
            )
            self.reduce_opacity_on_hover = False
            self.config.data["reduce_opacity_on_hover"] = False
            self._update_window_opacity()
        self.click_through_overlay = enabled
        self._update_click_through()
        self.config.data["click_through_overlay"] = enabled
        self.config.save()

    def open_settings(self):
        SettingsDialog(self).exec()

    def open_about(self):
        AboutDialog(self).exec()

    def apply_settings(self):
        d = self.config.data

        previous_source = self.sampler.source_revision
        self.sampler.set_adapter(d.get("network_adapter", "auto"))
        if d.get("network_adapter") != self.sampler.selected_adapter:
            d["network_adapter"] = self.sampler.selected_adapter
            self.config.save()
        if (
            self.graph_window
            and self.graph_window.isVisible()
            and self.sampler.source_revision != previous_source
        ):
            self.graph_window.clear_history()

        # Alert color
        self.alert_color = d.get("alert_color", "#FF5555")
        self._alert_active = False

        # Interval
        self.timer.setInterval(int(d["update_interval"] * 1000))
        self.timer.start()

        # Formatting
        self.unit = d["unit"]
        self.auto_minimum_unit = d["auto_unit_minimum"]
        self.precision = d["precision"]
        self.download_threshold = threshold_bytes_per_sec(
            d["notify_threshold"].get("download")
        )
        self.upload_threshold = threshold_bytes_per_sec(
            d["notify_threshold"].get("upload")
        )
        self.opacity = d["opacity"]
        self.reduce_opacity_on_hover = d["reduce_opacity_on_hover"]
        self.click_through_overlay = d["click_through_overlay"]

        # Font settings
        self.font = d.get("font", "Segoe UI")
        self.font_size = d.get("font_size", 10)
        self.font_color = d.get("font_color", "white")
        self.font_bold = d.get("font_bold", True)

        # Update labels' color
        for lbl in (self.dl_label, self.ul_label):
            lbl.setStyleSheet(f"color: {self.font_color}")

        label_font = QtGui.QFont(self.font, self.font_size)
        label_font.setBold(self.font_bold)
        for lbl in (self.dl_label, self.ul_label):
            lbl.setFont(label_font)

        self._update_window_opacity()
        self._update_click_through()

        # Update graph window settings
        if self.graph_window:
            self.graph_window.apply_settings()
        # Immediately refresh
        self._update_speeds()
        self._update_minimum_size()

    def _update_minimum_size(self):
        layout = self.layout()
        assert layout is not None
        layout.activate()
        minimum_size = layout.minimumSize().expandedTo(OVERLAY_MINIMUM_SIZE)
        self.setMinimumSize(minimum_size)
        current_size = self.size()
        if (
            current_size.width() < minimum_size.width()
            or current_size.height() < minimum_size.height()
        ):
            self.resize(current_size.expandedTo(minimum_size))

        geometry = geometry_values(self.geometry())
        if self.config.data.get("widget_geometry") != geometry:
            self.config.data["widget_geometry"] = geometry
            self.config.save()

    # Put both persistent windows back in their default locations.
    def reset_window_positions(self):
        overlay_offset = 0
        self.config.data["graph_geometry"] = None

        if self.graph_window and self.graph_window.isVisible():
            graph_rect = self.graph_window.reset_position()
            self.config.data["graph_geometry"] = geometry_values(graph_rect)
            overlay_offset = graph_rect.height() + 10

        overlay_rect = dock_window(
            self,
            self.size(),
            OVERLAY_MINIMUM_SIZE,
            bottom_offset=overlay_offset,
        )
        self.config.data["widget_geometry"] = geometry_values(overlay_rect)

        self.config.save()

    def _update_speeds(self):
        previous_source = self.sampler.source_revision
        sent_per_sec, recv_per_sec = self.sampler.sample()
        source_changed = self.sampler.source_revision != previous_source

        self._update_tray_tooltip()

        if self.config.data.get("network_adapter") != self.sampler.selected_adapter:
            self.config.data["network_adapter"] = self.sampler.selected_adapter
            self.config.save()

        if self.graph_window and self.graph_window.isVisible():
            if source_changed:
                self.graph_window.clear_history()
            self.graph_window.add_sample(sent_per_sec, recv_per_sec)

        self.dl_label.setText(
            "↓ "
            + format_rate(
                recv_per_sec,
                self.unit,
                self.precision,
                self.auto_minimum_unit,
            )
        )
        self.ul_label.setText(
            "↑ "
            + format_rate(
                sent_per_sec,
                self.unit,
                self.precision,
                self.auto_minimum_unit,
            )
        )

        self._download_alert = (
            self.download_threshold is not None
            and recv_per_sec > self.download_threshold
        )
        self._upload_alert = (
            self.upload_threshold is not None
            and sent_per_sec > self.upload_threshold
        )
        self._alert_active = self._download_alert or self._upload_alert

        self.update()  # for trigger repaint

    def paintEvent(self, event):
        radius = 8.0
        rect = QRectF(self.rect())
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)

        # bg is always dark/translucent, alert_color is only ever an accent
        bg_path = QtGui.QPainterPath()
        bg_path.addRoundedRect(rect, radius, radius)
        p.fillPath(bg_path, QtGui.QColor(0, 0, 0, 160))

        if getattr(self, "_alert_active", False):
            self._paint_alert_border(p, rect, radius)
        self._paint_row_indicators(p)

        # For Drag Handle
        p.setPen(QtGui.QPen(QtGui.QColor("#aaa")))
        size = 16
        for i in range(4, size, 4):
            p.drawLine(self.width() - i, self.height(), self.width(), self.height() - i)

    def _paint_alert_border(self, p, rect, radius):
        color = QtGui.QColor(self.alert_color)
        border_rect = rect.adjusted(1.0, 1.0, -1.0, -1.0)
        p.setBrush(Qt.NoBrush)

        # glow: a few fading passes, widest/faintest first, corners get more overlap naturally
        for width, alpha in ((6.0, 25), (4.0, 45), (2.0, 75)):
            glow = QtGui.QColor(color)
            glow.setAlpha(alpha)
            p.setPen(QtGui.QPen(glow, width))
            p.drawRoundedRect(border_rect, radius, radius)

        # crisp rim on top
        rim = QtGui.QColor(color)
        rim.setAlpha(235)
        p.setPen(QtGui.QPen(rim, 1.4))
        p.drawRoundedRect(border_rect, radius, radius)

    def _paint_row_indicators(self, p):
        neutral_color = QtGui.QColor(70, 70, 70, 210)
        alert_qcolor = QtGui.QColor(self.alert_color)

        p.setPen(Qt.NoPen)
        for label, active in (
            (self.dl_label, getattr(self, "_download_alert", False)),
            (self.ul_label, getattr(self, "_upload_alert", False)),
        ):
            # tied to font metrics, not label geometry, so resizing the widget doesn't stretch the bar
            bar_height = label.fontMetrics().height() * 0.75
            center_y = label.geometry().center().y()
            bar_rect = QRectF(
                ROW_INDICATOR_X,
                center_y - bar_height / 2,
                ROW_INDICATOR_WIDTH,
                bar_height,
            )
            p.setBrush(alert_qcolor if active else neutral_color)
            p.drawRoundedRect(bar_rect, ROW_INDICATOR_WIDTH / 2, ROW_INDICATOR_WIDTH / 2)

    def enterEvent(self, event):
        self._pointer_over_overlay = True
        self._update_window_opacity()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._pointer_over_overlay = False
        self._update_window_opacity()
        super().leaveEvent(event)

    def _update_window_opacity(self):
        opacity = self.opacity
        if self.reduce_opacity_on_hover and self._pointer_over_overlay:
            opacity = min(opacity, HOVER_OPACITY)
        self.setWindowOpacity(opacity)

    def _update_click_through(self):
        current = bool(self.windowFlags() & Qt.WindowTransparentForInput)
        if current != self.click_through_overlay:
            visible = self.isVisible()
            self.setWindowFlag(
                Qt.WindowTransparentForInput, self.click_through_overlay
            )
            if visible:
                self.show()
        self.setCursor(Qt.ArrowCursor)

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton and not self.locked:
            grip = 16
            pos = e.position().toPoint()
            if pos.x() > self.width() - grip and pos.y() > self.height() - grip:
                # Capture the start geometry once so the delta stays stable during drag.
                self._resizing = True
                self._resize_start_pos = e.globalPosition().toPoint()
                self._resize_start_geom = self.geometry()
            else:
                self._drag_offset = (
                    e.globalPosition().toPoint() - self.frameGeometry().topLeft()
                )

    def mouseMoveEvent(self, e):
        grip_size = 16
        pos = e.position()
        in_grip_area = (
            self.width() - grip_size < pos.x() < self.width()
            and self.height() - grip_size < pos.y() < self.height()
        )

        if self._resizing:
            global_pos = e.globalPosition().toPoint()
            dx = global_pos.x() - self._resize_start_pos.x()
            dy = global_pos.y() - self._resize_start_pos.y()
            new_w = max(self.minimumWidth(), self._resize_start_geom.width() + dx)
            new_h = max(self.minimumHeight(), self._resize_start_geom.height() + dy)
            self.resize(new_w, new_h)
        elif in_grip_area:
            self.setCursor(Qt.SizeFDiagCursor)
        elif not self.locked and self._drag_offset and (e.buttons() & Qt.LeftButton):
            self.move(e.globalPosition().toPoint() - self._drag_offset)
            self.setCursor(Qt.ClosedHandCursor)
        else:
            self.setCursor(Qt.ArrowCursor)

    def mouseReleaseEvent(self, e):

        # release the resizing flag and reset cursor
        self._resizing = False
        self.setCursor(QtCore.Qt.ArrowCursor)
        self._resize_start_pos = None
        self._resize_start_geom = None

        if not self.locked:
            self._drag_offset = None
        g = self.geometry()
        self.config.data["widget_geometry"] = [g.x(), g.y(), g.width(), g.height()]
        self.config.save()

    def _setup_tray(self):
        tray_icon = QtGui.QIcon()
        for _s in [16, 20, 24, 32]:
            tray_icon.addFile(
                _asset_path(f"assets/tray/tray-color-{_s}.png"),
                QtCore.QSize(_s, _s),
            )
        self.tray = QtWidgets.QSystemTrayIcon(tray_icon, self)
        self._update_tray_tooltip()
        self._tray_menu = QtWidgets.QMenu()
        # Rebuild the menu on open so checked states are always current.
        self._tray_menu.aboutToShow.connect(self._build_tray_menu)
        self.tray.setContextMenu(self._tray_menu)
        self.tray.activated.connect(self._on_tray_activated)
        self.tray.show()

    def _update_tray_tooltip(self):
        adapter = self.sampler.resolved_adapter
        tooltip = f"TinyNetUse - Auto: {adapter}" if adapter else "TinyNetUse"
        if hasattr(self, "tray"):
            self.tray.setToolTip(tooltip)

    def _build_tray_menu(self):
        self._tray_menu.clear()
        self._populate_app_menu(self._tray_menu)

    def _populate_app_menu(self, menu):
        overlay_text = "Hide Overlay" if self.isVisible() else "Show Overlay"
        overlay = menu.addAction(overlay_text)
        overlay.triggered.connect(self.toggle_overlay_visibility)

        graph = menu.addAction("Show Graph")
        graph.setCheckable(True)
        graph.setChecked(self.graph_visible)
        graph.triggered.connect(self.toggle_graph)

        atop = menu.addAction("Always On Top")
        atop.setCheckable(True)
        atop.setChecked(self.always_on_top)
        atop.triggered.connect(self.toggle_always_on_top)

        lock = menu.addAction("Lock Position")
        lock.setCheckable(True)
        lock.setChecked(self.locked)
        lock.triggered.connect(self.toggle_lock)

        click_through = menu.addAction("Click Through Overlay")
        click_through.setCheckable(True)
        click_through.setChecked(self.click_through_overlay)
        click_through.triggered.connect(self.toggle_click_through)

        menu.addAction("Settings", self.open_settings)
        menu.addAction("Reset Window Positions", self.reset_window_positions)
        menu.addAction("About TinyNetUse", self.open_about)
        menu.addSeparator()
        menu.addAction("Quit", QtWidgets.QApplication.quit)

    def _on_tray_activated(self, reason):
        # Single click: bring widget forward in case it got buried.
        if reason == QtWidgets.QSystemTrayIcon.ActivationReason.Trigger:
            self.show_overlay()

    def toggle_overlay_visibility(self):
        if self.isVisible():
            self.hide()
        else:
            self.show_overlay()

    # Used by the tray icon and second-process IPC activation.
    @QtCore.Slot()
    def show_overlay(self):
        if self.isMinimized():
            self.showNormal()
        else:
            self.show()
        self.raise_()
        self.activateWindow()
        if self.windowHandle():
            self.windowHandle().requestActivate()

    def closeEvent(self, e):
        self.timer.stop()
        if hasattr(self, "tray"):
            self.tray.hide()
        QtWidgets.QApplication.instance().quit()

    def _on_graph_closed(self):
        self.graph_visible = False
        self.config.data["graph_visible"] = False
        self.config.save()


def main():
    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName("TinyNetUse")
    app.setApplicationVersion(__version__)

    command = "quit" if "--quit" in sys.argv[1:] else "show"
    single_instance = SingleInstance()
    if not single_instance.start(command):
        return 0
    if command == "quit":
        return 0

    w = TinyNetUseWidget()
    single_instance.show_requested.connect(w.show_overlay)
    single_instance.quit_requested.connect(w.close)
    w.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
