# graph_window.py — Floating dialog that draws a rolling network speed history graph.

from collections import deque

from PySide6 import QtWidgets, QtCore, QtGui
from PySide6.QtCore import QRectF, Qt, Signal
from PySide6.QtGui import QAction

from tinynetuse.config import Config
from tinynetuse.geometry import (
    dock_window,
    geometry_values,
    restore_window_geometry,
)
from tinynetuse.units import convert_rate, format_rate, select_auto_unit


GRAPH_DEFAULT_SIZE = QtCore.QSize(600, 320)
GRAPH_MINIMUM_SIZE = QtCore.QSize(200, 100)


class GraphWindow(QtWidgets.QDialog):
    closed = Signal()

    def __init__(self, parent=None, config=None):
        super().__init__(parent)
        self.config = config or Config()
        d = self.config.data

        # ── Window Setup ──
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowTitle("Network Usage Graph")
        self.setMinimumSize(GRAPH_MINIMUM_SIZE)
        self.resize(GRAPH_DEFAULT_SIZE)
        base = Qt.FramelessWindowHint | Qt.Dialog
        flags = base | (Qt.WindowStaysOnTopHint if d.get("graph_always_on_top") else 0)

        # Match main widget opacity
        self.setWindowOpacity(d.get("opacity", 1.0))
        self.setWindowFlags(flags)
        self.always_on_top = d.get("graph_always_on_top", False)
        self.locked = d.get("graph_locked", False)

        # ── Load Geometry ──
        restored = restore_window_geometry(
            self,
            d.get("graph_geometry"),
            GRAPH_DEFAULT_SIZE,
            GRAPH_MINIMUM_SIZE,
        )
        restored_values = geometry_values(restored)
        if d.get("graph_geometry") != restored_values:
            d["graph_geometry"] = restored_values
            self.config.save()

        # ── Data & State ──
        self.max_history = d.get("graph_history", 60)
        self.unit = d.get("unit", "MB/s")
        self.auto_minimum_unit = d.get("auto_unit_minimum", "B/s")
        self.precision = d.get("precision", 2)
        self.bg_color = QtGui.QColor(0, 0, 0, 220)
        self.line_dl = QtGui.QColor(d.get("download_color", "#4FC3F7"))
        self.line_ul = QtGui.QColor(d.get("upload_color", "#FF8A65"))
        self.sent_hist = deque([0.0] * self.max_history, maxlen=self.max_history)
        self.recv_hist = deque([0.0] * self.max_history, maxlen=self.max_history)
        self.last_dl = 0.0
        self.last_ul = 0.0
        self.auto_scale = True
        self.has_samples = False
        self.paused = False

        # ── Drag & Resize State ──
        self._drag_offset = None
        self._resizing = False
        self._resize_start = None

        # ── Apply Settings ──
        self.apply_settings()

    # Used by the shared Reset Window Positions action.
    def reset_position(self):
        return dock_window(self, self.size(), GRAPH_MINIMUM_SIZE)

    def _swap_colors(self):
        self.line_dl, self.line_ul = self.line_ul, self.line_dl
        self.config.data["download_color"] = self.line_dl.name()
        self.config.data["upload_color"] = self.line_ul.name()
        self.config.save()
        self.update()

    # The main widget passes in the one shared sampler result.
    def add_sample(self, sent_bps, recv_bps):
        if self.paused:
            return
        self.last_ul = sent_bps
        self.last_dl = recv_bps
        self.sent_hist.append(sent_bps)
        self.recv_hist.append(recv_bps)
        self.has_samples = True
        self.update()

    # Old samples belong to the previous adapter and should not be mixed in.
    def clear_history(self):
        self.sent_hist = deque([0.0] * self.max_history, maxlen=self.max_history)
        self.recv_hist = deque([0.0] * self.max_history, maxlen=self.max_history)
        self.last_dl = 0.0
        self.last_ul = 0.0
        self.has_samples = False
        self.update()

    def reset_for_reopen(self):
        self.paused = False
        self.clear_history()

    def _toggle_pause(self, paused):
        self.paused = bool(paused)
        self.update()

    def _label_font(self):
        font_size = max(6, min(12, self.width() * 0.02))
        font = QtWidgets.QApplication.font()
        font.setPointSize(int(font_size))
        return font

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        rect = self.rect()

        # Background
        path = QtGui.QPainterPath()
        path.addRoundedRect(QRectF(rect), 12, 12)
        painter.fillPath(path, self.bg_color)

        display_unit = self._display_unit()
        painter.setFont(self._label_font())
        metrics = painter.fontMetrics()
        base_margin = max(8, min(rect.width(), rect.height()) * 0.02)
        legend_height = metrics.height() + 6
        scale_min = f"{0:.{self.precision}f} {display_unit}"

        if not self.has_samples:
            painter.setPen(QtGui.QPen(QtGui.QColor("#B8C0CC")))
            painter.drawText(
                QRectF(rect), Qt.AlignCenter, "Waiting for network samples..."
            )
            self._draw_border_and_resize_grip(painter, rect)
            return

        sent_values = [
            convert_rate(rate, display_unit) for rate in self.sent_hist
        ]
        recv_values = [
            convert_rate(rate, display_unit) for rate in self.recv_hist
        ]
        all_vals = sent_values + recv_values
        maxv = max(max(all_vals, default=0.0), 0.001) * 1.2
        scale_max = f"{maxv:.{self.precision}f} {display_unit}"
        scale_width = max(
            metrics.horizontalAdvance(scale_min),
            metrics.horizontalAdvance(scale_max),
        )
        ox = base_margin + scale_width + 6
        oy = base_margin + legend_height
        w = rect.width() - ox - base_margin
        h = rect.height() - oy - base_margin - metrics.height()

        legend_gap = 8
        legend_width = max(1, int((w - legend_gap) / 2))
        dl_label = f"↓ {format_rate(self.last_dl, display_unit, self.precision)}"
        ul_label = f"↑ {format_rate(self.last_ul, display_unit, self.precision)}"
        dl_label = metrics.elidedText(dl_label, Qt.ElideRight, legend_width)
        ul_label = metrics.elidedText(ul_label, Qt.ElideRight, legend_width)
        painter.setPen(QtGui.QPen(self.line_dl))
        painter.drawText(
            QRectF(ox, base_margin, legend_width, legend_height),
            Qt.AlignLeft | Qt.AlignVCenter,
            dl_label,
        )
        painter.setPen(QtGui.QPen(self.line_ul))
        painter.drawText(
            QRectF(ox + legend_width + legend_gap, base_margin, legend_width, legend_height),
            Qt.AlignRight | Qt.AlignVCenter,
            ul_label,
        )

        for index in range(5):
            y = oy + h * index / 4
            painter.setPen(QtGui.QPen(QtGui.QColor(255, 255, 255, 38), 1))
            painter.drawLine(QtCore.QPointF(ox, y), QtCore.QPointF(ox + w, y))

        painter.setPen(QtGui.QPen(QtGui.QColor("#B8C0CC")))
        painter.drawText(
            QRectF(base_margin, oy - metrics.height() / 2, scale_width, metrics.height()),
            Qt.AlignRight | Qt.AlignVCenter,
            scale_max,
        )
        painter.drawText(
            QRectF(base_margin, oy + h - metrics.height() / 2, scale_width, metrics.height()),
            Qt.AlignRight | Qt.AlignVCenter,
            scale_min,
        )

        # Dynamic line thickness (1 to 3 pixels)
        line_thickness = max(1, min(3, rect.width() * 0.005))  # 0.5% of width

        # Draw graph lines
        def draw_series(data, color):
            painter.setPen(QtGui.QPen(color, line_thickness))
            points = []
            for i, v in enumerate(data):
                x = ox + i * (w / (len(data) - 1))
                y = oy + h - (v / maxv) * h
                points.append(QtCore.QPointF(x, y))
            if len(points) > 1:
                painter.drawPolyline(points)

        draw_series(recv_values, self.line_dl)
        draw_series(sent_values, self.line_ul)

        self._draw_border_and_resize_grip(painter, rect)

    def _draw_border_and_resize_grip(self, painter, rect):
        painter.setPen(QtGui.QPen(QtGui.QColor("#444"), 2))
        painter.drawRoundedRect(QRectF(rect).adjusted(1, 1, -1, -1), 12, 12)

        painter.setPen(QtGui.QPen(QtGui.QColor("#aaa")))
        grip_size = max(8, min(16, rect.width() * 0.03))
        for i in range(4, int(grip_size), 4):
            painter.drawLine(
                self.width() - i, self.height(), self.width(), self.height() - i
            )

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton and not self.locked:
            pos = e.position().toPoint()
            grip = 16
            if pos.x() > self.width() - grip and pos.y() > self.height() - grip:
                self._resizing = True
                self._resize_start = (e.globalPosition().toPoint(), self.geometry())
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
            start_pos, geom = self._resize_start
            global_pos = e.globalPosition().toPoint()
            dx = global_pos.x() - start_pos.x()
            dy = global_pos.y() - start_pos.y()
            self.resize(max(200, geom.width() + dx), max(100, geom.height() + dy))
        elif in_grip_area:
            self.setCursor(Qt.SizeFDiagCursor)
        elif self._drag_offset and not self.locked:
            self.move(e.globalPosition().toPoint() - self._drag_offset)
            self.setCursor(Qt.ClosedHandCursor)
        else:
            self.setCursor(Qt.ArrowCursor)

    def mouseReleaseEvent(self, e):
        if self._resizing:
            self._resizing = False
        if self._drag_offset:
            self._drag_offset = None
        # save geometry
        g = self.geometry()
        self.config.data["graph_geometry"] = [g.x(), g.y(), g.width(), g.height()]
        self.config.save()

    def contextMenuEvent(self, event):
        menu = QtWidgets.QMenu(self)
        atop = QAction("Always On Top", self, checkable=True)
        atop.setChecked(self.always_on_top)
        atop.triggered.connect(self._toggle_always_on_top)
        menu.addAction(atop)
        lock = QAction("Lock Position", self, checkable=True)
        lock.setChecked(self.locked)
        lock.triggered.connect(self._toggle_lock)
        menu.addAction(lock)
        pause = QAction("Pause Graph", self, checkable=True)
        pause.setChecked(self.paused)
        pause.triggered.connect(self._toggle_pause)
        menu.addAction(pause)
        clear_history = QAction("Clear History", self)
        clear_history.triggered.connect(self.clear_history)
        menu.addAction(clear_history)
        swap_colors = QAction("Swap Colors", self)
        swap_colors.triggered.connect(self._swap_colors)
        menu.addAction(swap_colors)
        menu.addSeparator()
        menu.addAction("Close", self.close)
        menu.exec(event.globalPos())

    def _toggle_always_on_top(self, on):
        self.always_on_top = bool(on)
        f = self.windowFlags() & ~Qt.WindowStaysOnTopHint
        if on:
            f |= Qt.WindowStaysOnTopHint
        self.setWindowFlags(f)
        self.show()
        self.raise_()
        self.config.data["graph_always_on_top"] = self.always_on_top
        self.config.save()

    def _toggle_lock(self, l):
        self.locked = bool(l)
        self.config.data["graph_locked"] = self.locked
        self.config.save()

    def _display_unit(self):
        if self.unit != "auto":
            return self.unit
        largest = max(
            max(self.sent_hist, default=0.0),
            max(self.recv_hist, default=0.0),
        )
        return select_auto_unit(largest, self.auto_minimum_unit)

    def apply_settings(self):
        d = self.config.data
        new_max = d.get("graph_history", 60)
        if new_max != self.max_history:
            # Rebuild deques at the new size, keeping the most recent samples.
            sent = list(self.sent_hist)[-new_max:]
            recv = list(self.recv_hist)[-new_max:]
            while len(sent) < new_max:
                sent.insert(0, 0.0)
                recv.insert(0, 0.0)
            self.max_history = new_max
            self.sent_hist = deque(sent, maxlen=new_max)
            self.recv_hist = deque(recv, maxlen=new_max)
        self.unit = d.get("unit", "MB/s")
        self.auto_minimum_unit = d.get("auto_unit_minimum", "B/s")
        self.precision = d.get("precision", 2)
        self.setWindowOpacity(d.get("opacity", 1.0))
        self.line_dl = QtGui.QColor(d.get("download_color", "#4FC3F7"))
        self.line_ul = QtGui.QColor(d.get("upload_color", "#FF8A65"))
        self.update()

    def closeEvent(self, event):
        self.closed.emit()
        event.accept()
