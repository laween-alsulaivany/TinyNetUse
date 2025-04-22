# main.py

import time
import sys
import psutil
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import Qt, QRectF
from config import Config
from settings_dialog import SettingsDialog
from graph_window import GraphWindow


class TinyNetUseWidget(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()

        # ── Load Config & State ──
        self.config = Config()
        self.locked = False
        self._settings = QtCore.QSettings("TinyNetUse", "Widget")

        # ── Window Setup ──
        d = self.config.data
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.resize(140, 60)
        base_flags = Qt.FramelessWindowHint | Qt.Tool
        self.setWindowFlags(base_flags | (
            Qt.WindowStaysOnTopHint if d.get("widget_always_on_top") else 0))
        self.setWindowOpacity(d.get("opacity", 1.0))
        self.always_on_top = d.get("widget_always_on_top", True)

        # ── Font ──
        font_name = d.get("font", "Segoe UI")
        font = QtGui.QFont(font_name, d.get("font_size", 10))
        if not font.exactMatch():
            font = QtGui.QFont("Segoe UI", d.get("font_size", 10))
            self.config.data["font"] = "Segoe UI"
            self.config.save()
        font.setBold(d.get("font_bold", False))
        QtWidgets.QApplication.setFont(font)

        # ── Labels ──
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(2)
        self.dl_label = QtWidgets.QLabel()
        self.ul_label = QtWidgets.QLabel()
        for lbl in (self.dl_label, self.ul_label):
            # Dynamic initial color
            lbl.setStyleSheet(f"color: {d.get('font_color', 'white')}")
            layout.addWidget(lbl)

        # ── Psutil Counters ──
        cnt = psutil.net_io_counters()
        self._last_sent, self._last_recv = cnt.bytes_sent, cnt.bytes_recv

        # ── Update Timer ──
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self._update_speeds)

        geom = d.get("widget_geometry")
        if isinstance(geom, (list, tuple)) and len(geom) == 4:
            x, y, w, h = map(int, geom)
            self.setGeometry(x, y, w, h)
        else:
            self._dock_bottom_right()

        # ── Locked? ──
        self.locked = bool(d.get("widget_locked", False))

        if "net_always_on_top" in self.config.data:
            self.always_on_top = self.config.data["net_always_on_top"]

        # ── Drag support ──
        self._drag_offset = None

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

    def contextMenuEvent(self, event):
        menu = QtWidgets.QMenu(self)

        # Always on Top
        atop = QtWidgets.QAction("Always On Top", self, checkable=True)
        atop.setChecked(self.always_on_top)
        atop.triggered.connect(self.toggle_always_on_top)
        menu.addAction(atop)

        # Lock Position
        lock = QtWidgets.QAction("Lock Position", self, checkable=True)
        lock.setChecked(self.locked)
        lock.triggered.connect(self.toggle_lock)
        menu.addAction(lock)

        # Show Graph
        settings_action = QtWidgets.QAction("Settings", self)
        settings_action.triggered.connect(self.open_settings)
        menu.addAction(settings_action)

        graph = QtWidgets.QAction("Show Graph", self, checkable=True)
        graph.setChecked(self.graph_visible)
        graph.triggered.connect(self.toggle_graph)
        menu.addAction(graph)

        menu.addSeparator()
        menu.addAction("Quit", QtWidgets.QApplication.quit)

        menu.exec_(event.globalPos())

    def toggle_graph(self, visible):
        self.graph_visible = visible
        self.config.data["graph_visible"] = visible
        self.config.save()

        if visible:
            if self.graph_window is None or not self.graph_window.isVisible():
                self.graph_window = GraphWindow(
                    parent=self, config=self.config)
                self.graph_window.closed.connect(self._on_graph_closed)
            self.graph_window.show()
            self.graph_window.raise_()
            self.graph_window.activateWindow()
        else:
            if self.graph_window:
                self.graph_window.close()

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

    def open_settings(self):
        dlg = SettingsDialog(self)
        if dlg.exec_() == QtWidgets.QDialog.Accepted:
            self.apply_settings()

    def apply_settings(self):
        d = self.config.data

        # Alert color
        self.alert_color = d.get("alert_color", "#FF5555")
        self._alert_active = False

        # Interval
        self.timer.setInterval(int(d["update_interval"] * 1000))
        self.timer.start()

        # Formatting
        self.unit = d["unit"]
        self.precision = d["precision"]
        self.threshold = d["notify_threshold"].get("download")
        self.opacity = d["opacity"]

        # Font settings
        self.font = d.get("font", "Segoe UI")
        self.font_size = d.get("font_size", 10)
        self.font_color = d.get("font_color", "white")
        self.font_bold = d.get("font_bold", True)

        # Update labels' color
        for lbl in (self.dl_label, self.ul_label):
            lbl.setStyleSheet(f"color: {self.font_color}")

        # Apply global font
        font = QtGui.QFont(self.font, self.font_size)
        font.setBold(self.font_bold)
        QtWidgets.QApplication.setFont(font)

        # Opacity
        self.setWindowOpacity(d.get("opacity", 1.0))

        # Update graph window settings
        if self.graph_window:
            self.graph_window.apply_settings()
        # Immediately refresh
        self._update_speeds()

    def _dock_bottom_right(self):
        ag = QtWidgets.QApplication.primaryScreen().availableGeometry()
        w, h = self.width(), self.height()
        x = ag.right() - w - 10
        y = ag.bottom() - h - 10
        self.setGeometry(x, y, w, h)

    def _update_speeds(self):
        now = time.time()
        elapsed = now - getattr(self, "_last_time", now)
        self._last_time = now

        if elapsed == 0:
            return

        cnt = psutil.net_io_counters()
        raw_sent = cnt.bytes_sent - self._last_sent
        raw_recv = cnt.bytes_recv - self._last_recv
        self._last_sent, self._last_recv = cnt.bytes_sent, cnt.bytes_recv

        sent_per_sec = raw_sent / elapsed
        recv_per_sec = raw_recv / elapsed

        def fmt(raw, mb):
            u = self.unit
            if u == "B/s":
                return f"{raw:.{self.precision}f} B/s"
            if u == "KB/s":
                return f"{raw/1024:.{self.precision}f} KB/s"
            if u == "MB/s":
                return f"{mb:.{self.precision}f} MB/s"
            if u == "b/s":
                return f"{raw*8:.{self.precision}f} b/s"
            if u == "Kib/s":
                return f"{raw*8/1024:.{self.precision}f} Kib/s"
            if u == "Mib/s":
                return f"{raw*8/(1<<20):.{self.precision}f} Mib/s"
            # auto
            if mb >= 1:
                return f"{mb:.{self.precision}f} MB/s"
            return f"{raw/1024:.{self.precision}f} KB/s"

        mb_recv = recv_per_sec / (1 << 20)
        mb_sent = sent_per_sec / (1 << 20)

        self.dl_label.setText("↓ " + fmt(recv_per_sec, mb_recv))
        self.ul_label.setText("↑ " + fmt(sent_per_sec, mb_sent))

        self._alert_active = False
        if self.threshold and mb_recv > self.threshold:
            self._alert_active = True

        self.update()  # for trigger repaint

    def paintEvent(self, event):
        path = QtGui.QPainterPath()
        path.addRoundedRect(QRectF(self.rect()), 8.0, 8.0)
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)

        # Change background color based on alert state
        if getattr(self, "_alert_active", False):
            bg_color = QtGui.QColor(self.alert_color)
        else:
            bg_color = QtGui.QColor(0, 0, 0, 160)
        p.fillPath(path, bg_color)

        # For Drag Handle
        p.setPen(QtGui.QPen(QtGui.QColor("#aaa")))
        size = 16
        for i in range(4, size, 4):
            p.drawLine(self.width()-i, self.height(),
                       self.width(), self.height()-i)

    def mousePressEvent(self, e):
        if not self.locked and e.button() == Qt.LeftButton:
            self._drag_offset = e.globalPos() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, e):
        grip_size = 16
        in_grip_area = (
            self.width() - grip_size < e.x() < self.width() and
            self.height() - grip_size < e.y() < self.height()
        )

        if self._resizing:
            dx = e.globalX() - self._resize_start_pos.x()
            dy = e.globalY() - self._resize_start_pos.y()
            new_w = max(self.minimumWidth(),
                        self._resize_start_geom.width() + dx)
            new_h = max(self.minimumHeight(),
                        self._resize_start_geom.height() + dy)
            self.resize(new_w, new_h)
        elif in_grip_area:
            self.setCursor(Qt.SizeFDiagCursor)  # Resize diagonal cursor
            self._resizing = True
            self._resize_start_pos = e.globalPos()
            self._resize_start_geom = self.geometry()
        else:
            self.setCursor(Qt.ArrowCursor)  # Default cursor
            if not self.locked and self._drag_offset and (e.buttons() & Qt.LeftButton):
                self.move(e.globalPos() - self._drag_offset)

    def mouseReleaseEvent(self, e):

        # release the resizing flag and reset cursor
        self._resizing = False
        self.setCursor(QtCore.Qt.ArrowCursor)
        self._resize_start_pos = None
        self._resize_start_geom = None

        if not self.locked:
            self._drag_offset = None
        g = self.geometry()
        self.config.data["widget_geometry"] = [
            g.x(), g.y(), g.width(), g.height()]
        self.config.save()

    def closeEvent(self, e):
        self.timer.stop()
        QtWidgets.qApp.quit()

    def _on_graph_closed(self):
        self.graph_visible = False
        self.config.data["graph_visible"] = False
        self.config.save()


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    w = TinyNetUseWidget()
    w.show()
    sys.exit(app.exec_())
