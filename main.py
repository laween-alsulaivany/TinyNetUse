# main.py

import sys
import psutil
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import Qt, QRectF
from config import Config
from settings_dialog import SettingsDialog
def set_always_on_top(widget, base_flags, on_top):
    flags = base_flags
    if on_top:
        flags |= QtCore.Qt.WindowStaysOnTopHint
    widget.setWindowFlags(flags)
    widget.show()
    widget.raise_()
class TinyNetUseWidget(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        QtWidgets.QApplication.setFont(QtGui.QFont("Segoe UI", 10))
        # ── Load Config & State ──
        self.config = Config()
        self.locked = False
        self._settings = QtCore.QSettings("TinyNetUse", "Widget")
        
        # ── Window Setup ──
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.resize(140, 60)
        self._base_flags = Qt.FramelessWindowHint | Qt.Tool
        self.setWindowFlags(self._base_flags)
        self.always_on_top = True 
        # ── Labels ──
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(2)
        self.dl_label = QtWidgets.QLabel()
        self.ul_label = QtWidgets.QLabel()
        for lbl in (self.dl_label, self.ul_label):
            lbl.setStyleSheet("color: white; font: bold 11px 'Segoe UI';")
            layout.addWidget(lbl)


        # ── Psutil Counters ──
        cnt = psutil.net_io_counters()
        self.last_sent, self.last_recv = cnt.bytes_sent, cnt.bytes_recv

        # ── Update Timer ──
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self._update_speeds)

        # ── Restore Position ──
        geom = self.config.data.get("widget_geometry")
        if (
            isinstance(geom, (list, tuple))
            and len(geom) == 4
            and all(isinstance(v, (int, float)) or (isinstance(v, str) and v.isdigit()) for v in geom)
        ):
            x, y, w, h = [int(float(v)) for v in geom]
            self.setGeometry(x, y, w, h)
        else:
            self.resize(140, 60)  # Only if no geometry saved yet
        if "locked" in self.config.data:
            self.locked = self.config.data["locked"]
        if "net_always_on_top" in self.config.data:
            self.always_on_top = self.config.data["net_always_on_top"]
            set_always_on_top(self, self._base_flags, self.always_on_top)

        # ── Apply current settings ──
        self.apply_settings()

        # ── Drag support ──
        self._drag_offset = None

        # ── Resizing support ──
        self._resizing = False
        self._resize_start_pos = None
        self._resize_start_geom = None


    def contextMenuEvent(self, event):
        menu = QtWidgets.QMenu(self)

        # Always on top with checkmark
        atop_action = QtWidgets.QAction("Always On Top", self)
        atop_action.setCheckable(True)
        atop_action.setChecked(self.windowFlags() & Qt.WindowStaysOnTopHint)
        atop_action.triggered.connect(self.toggle_always_on_top)
        menu.addAction(atop_action)

        # Lock position with checkmark
        lock_action = QtWidgets.QAction("Lock Position", self)
        lock_action.setCheckable(True)
        lock_action.setChecked(self.locked)
        lock_action.triggered.connect(self.toggle_lock)
        menu.addAction(lock_action)

        menu.addSeparator()
        menu.addAction("Settings", self.open_settings)
        menu.addAction("Close", self.close)
        menu.exec_(event.globalPos())

    def toggle_always_on_top(self):
        # self.always_on_top = not getattr(self, "net_always_on_top", True)
        self.always_on_top = not self.always_on_top
        flags = self._base_flags
        if self.always_on_top:
            flags |= Qt.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        self.show()
        self.raise_()
        self.activateWindow()
        self.config.data["net_always_on_top"] = self.always_on_top
        self.config.save()

    def toggle_lock(self):
        self.locked = not self.locked
        self.config.data["locked"] = self.locked
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
        self.unit      = d["unit"]
        self.precision = d["precision"]
        self.threshold = d["notify_threshold"].get("download")

        # Always‑on‑top flag from config
        flags = self._base_flags
        if d.get("net_always_on_top", False):
            flags |= Qt.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        self.show()
        self.raise_()
        self.activateWindow()

        # Immediately refresh speeds/labels
        self._update_speeds()

    def _dock_bottom_right(self):
        ag = QtWidgets.QApplication.primaryScreen().availableGeometry()
        w, h = self.width(), self.height()
        x = ag.right()  - w - 10
        y = ag.bottom() - h - 10
        self.setGeometry(x, y, w, h)

    def _update_speeds(self):
        cnt = psutil.net_io_counters()
        sent_b = cnt.bytes_sent - self.last_sent
        recv_b = cnt.bytes_recv - self.last_recv
        self.last_sent, self.last_recv = cnt.bytes_sent, cnt.bytes_recv

        mb_sent = sent_b / (1 << 20)
        mb_recv = recv_b / (1 << 20)

        def fmt(mb):
            if self.unit == "B/s":
                return f"{mb*1024*1024:.{self.precision}f} B/s"
            if self.unit == "KB/s":
                return f"{mb*1024:.{self.precision}f} KB/s"
            if self.unit == "MB/s":
                return f"{mb:.{self.precision}f} MB/s"
            if self.unit == "b/s":
                return f"{mb*1024*1024*8:.{self.precision}f} b/s"
            if self.unit == "Kib/s":
                return f"{mb*1024*8:.{self.precision}f} Kib/s"
            if self.unit == "Mib/s":
                return f"{mb*8:.{self.precision}f} Mib/s"
            # auto
            if mb >= 1:
                return f"{mb:.{self.precision}f} MB/s"
            return f"{mb*1024:.{self.precision}f} KB/s"

        self.dl_label.setText("↓ " + fmt(mb_recv))
        self.ul_label.setText("↑ " + fmt(mb_sent))

        # Alert logic
        self._alert_active = False
        if self.threshold and mb_recv > self.threshold:
            self._alert_active = True

        self.update()  # trigger repaint

    def paintEvent(self, event):
        path = QtGui.QPainterPath()
        path.addRoundedRect(QRectF(self.rect()), 8.0, 8.0)
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        if getattr(self, "_alert_active", False):
            bg_color = QtGui.QColor(self.alert_color)
        else:
            bg_color = QtGui.QColor(0, 0, 0, 160)
        p.fillPath(path, bg_color)
        p.setPen(QtGui.QPen(QtGui.QColor("#aaa")))
        size = 16
        for i in range(4, size, 4):
            p.drawLine(self.width()-i, self.height(), self.width(), self.height()-i)

  # --- Movable & Lockable ---
    def mousePressEvent(self, e):
        if not self.locked and e.button() == QtCore.Qt.LeftButton:
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
            new_w = max(self.minimumWidth(), self._resize_start_geom.width() + dx)
            new_h = max(self.minimumHeight(), self._resize_start_geom.height() + dy)
            self.resize(new_w, new_h)
        elif in_grip_area:
            self.setCursor(QtCore.Qt.SizeFDiagCursor)  # Resize diagonal cursor
            self._resizing = True
            self._resize_start_pos = e.globalPos()
            self._resize_start_geom = self.geometry()
        else:
            self.setCursor(QtCore.Qt.ArrowCursor)  # Default cursor
            if not self.locked and self._drag_offset and (e.buttons() & QtCore.Qt.LeftButton):
                self.move(e.globalPos() - self._drag_offset)


    def mouseReleaseEvent(self, e):
        self._resizing = False
        self.setCursor(QtCore.Qt.ArrowCursor)
        self._resize_start_pos = None
        self._resize_start_geom = None
        if not self.locked:
            self._drag_offset = None
        g = self.geometry()
        self.config.data["widget_geometry"] = [g.x(), g.y(), g.width(), g.height()]
        self.config.save()

    def closeEvent(self, e):
        self.timer.stop()
        QtWidgets.qApp.quit()


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    app.setFont(QtGui.QFont("Segoe UI", 10))
    w = TinyNetUseWidget()
    w.show()
    sys.exit(app.exec_())
