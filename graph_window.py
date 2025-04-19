# graph_window.py


from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtCore import QRectF, Qt
import psutil

def set_always_on_top(widget, base_flags, on_top):
    flags = base_flags
    if on_top:
        flags |= QtCore.Qt.WindowStaysOnTopHint
    widget.setWindowFlags(flags)
    widget.show()
    widget.raise_()

class GraphWindow(QtWidgets.QDialog):
    def __init__(self, parent=None, config=None):
        super().__init__(parent)
        self._base_flags = QtCore.Qt.FramelessWindowHint | QtCore.Qt.Window | QtCore.Qt.WindowStaysOnTopHint
        self.setWindowFlags(self._base_flags)
        self.always_on_top = False  
        self.minimal_mode = False
        self.setWindowTitle("Network Usage Graph")
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.resize(600, 320)

        self.config = config if config else getattr(parent, "config", None)
        d = self.config.data if self.config else {}
        self.max_history = 60
        self.interval = d.get("update_interval", 1.0)
        self.bg_color = QtGui.QColor(0, 0, 0, 220)
        self.line_dl = QtGui.QColor(d.get("download_color", "#4FC3F7"))
        self.line_ul = QtGui.QColor(d.get("upload_color", "#FF8A65"))
        self.locked = False
        self._drag_offset = None

        # Graph scale
        self.auto_scale = True
        self.manual_scale = 10.0  # MB/s

        # Data
        self.sent_hist = [0.0] * self.max_history
        self.recv_hist = [0.0] * self.max_history
        cnt = psutil.net_io_counters()
        self.last_sent, self.last_recv = cnt.bytes_sent, cnt.bytes_recv
        self.last_dl = 0.0
        self.last_ul = 0.0

        # Controls
        self._build_controls()

        # Timer
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self._update)
        self.timer.start(int(self.interval * 1000))

        # Movable & Resizable
        self._resizing = False
        self._resize_start_pos = None
        self._resize_start_geom = None
        # self.setMinimumSize(600, 300)  # Prevent too small

        # ── Restore Position ──
        geom = self.config.data.get("graph_geometry")
        if (
            isinstance(geom, (list, tuple))
            and len(geom) == 4
            and all(isinstance(v, (int, float)) or (isinstance(v, str) and v.isdigit()) for v in geom)
        ):
            x, y, w, h = [int(float(v)) for v in geom]
            self.setGeometry(x, y, w, h)
        else:
            self.config.data["graph_geometry"] = None
            self.config.save()
        if "locked" in self.config.data:
            self.locked = self.config.data["locked"]
        if "graph_always_on_top" in self.config.data:
            self.always_on_top = self.config.data["graph_always_on_top"]
            set_always_on_top(self, self._base_flags, self.always_on_top)

    def _build_controls(self):
        # Layouts
        self.main_layout = QtWidgets.QVBoxLayout(self)
        self.main_layout.setContentsMargins(8, 8, 8, 8)
        self.main_layout.setSpacing(0)

        self.controls_widget = QtWidgets.QWidget(self)
        self.controls_layout = QtWidgets.QHBoxLayout(self.controls_widget)
        self.controls_layout.setContentsMargins(8, 0, 8, 0)
        self.controls_layout.setSpacing(8)

        # Color swap
        self.btn_color = QtWidgets.QPushButton("Swap Colors", self)
        self.btn_color.setFixedWidth(100)
        self.btn_color.setStyleSheet("background: #222; color: #fff; border: 1px solid #444; border-radius: 6px;")
        self.btn_color.clicked.connect(self._swap_colors)
        self.controls_layout.addWidget(self.btn_color, alignment=QtCore.Qt.AlignTop)

        # Spacer
        self.controls_layout.addStretch()

        # Scale label
        self.scale_label = QtWidgets.QLabel(self)
        self.scale_label.setStyleSheet("color: #aaa; background: transparent;")
        self.scale_label.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        self.controls_layout.addWidget(self.scale_label, alignment=QtCore.Qt.AlignTop)

        self._update_scale_label()
        # Scale controls
        self.auto_scale_chk = QtWidgets.QCheckBox("Auto Scale", self)
        self.auto_scale_chk.setChecked(True)
        self.auto_scale_chk.setStyleSheet("color: #fff;")
        self.auto_scale_chk.stateChanged.connect(self._toggle_scale)
        self.controls_layout.addWidget(self.auto_scale_chk, alignment=QtCore.Qt.AlignTop)
        self.controls_layout.setContentsMargins(10, 10, 200, 0)


        self.scale_spin = QtWidgets.QDoubleSpinBox(self)
        self.scale_spin.setRange(1.0, 1000.0)
        self.scale_spin.setSingleStep(1.0)
        self.scale_spin.setValue(self.manual_scale)
        self.scale_spin.setSuffix(" MB/s")
        self.scale_spin.setStyleSheet("background: #222; color: #fff; border: 1px solid #444; border-radius: 6px;")
        self.scale_spin.valueChanged.connect(self._manual_scale_changed)
        self.controls_layout.addWidget(self.scale_spin)
        self.scale_spin.setEnabled(False)
        self.scale_spin.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)



        self.main_layout.addWidget(self.controls_widget, alignment=QtCore.Qt.AlignTop)

    def _toggle_scale(self):
        self.auto_scale = self.auto_scale_chk.isChecked()
        self.scale_spin.setEnabled(not self.auto_scale)
        if self.auto_scale:
            self.scale_spin.setStyleSheet("background: #222; color: #888; border: 1px solid #444; border-radius: 6px;")
        else:
            self.scale_spin.setStyleSheet("background: #222; color: #fff; border: 1px solid #444; border-radius: 6px;")
        self._update_scale_label()
        self.update()

    def _manual_scale_changed(self, val):
        self.manual_scale = val
        self._update_scale_label()
        self.update()

    def _scale_up(self):
        if not self.auto_scale:
            self.manual_scale = min(self.manual_scale + 2, 100)
            self._update_scale_label()
            self.update()

    def _scale_down(self):
        if not self.auto_scale:
            self.manual_scale = max(self.manual_scale - 2, 2)
            self._update_scale_label()
            self.update()

    def _swap_colors(self):
        self.line_dl, self.line_ul = self.line_ul, self.line_dl
        self.update()

    def _update_scale_label(self):
        if self.auto_scale:
            self.scale_label.setText("Scale: Auto")
        else:
            self.scale_label.setText(f"Scale: {self.manual_scale:.1f} MB/s")

    def _update(self):
        cnt = psutil.net_io_counters()
        sent = cnt.bytes_sent - self.last_sent
        recv = cnt.bytes_recv - self.last_recv
        self.last_sent, self.last_recv = cnt.bytes_sent, cnt.bytes_recv

        mb_sent = sent / (1 << 20)
        mb_recv = recv / (1 << 20)
        self.last_ul = mb_sent
        self.last_dl = mb_recv

        self.sent_hist.append(mb_sent)
        self.recv_hist.append(mb_recv)
        if len(self.sent_hist) > self.max_history:
            self.sent_hist.pop(0)
            self.recv_hist.pop(0)
        self.update()

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        rect = self.rect()
        path = QtGui.QPainterPath()
        path.addRoundedRect(QRectF(rect), 12, 12)
        painter.fillPath(path, self.bg_color)

        # Find max for scaling
        all_vals = self.sent_hist + self.recv_hist
        if self.auto_scale:
            max_val = max(max(all_vals), 1e-3)
            max_val = max(1.0, max_val * 1.2)  # pad a bit
        else:
            max_val = self.manual_scale

        if self.minimal_mode:
            ox, oy = 4, 4
            w, h = rect.width() - 8, rect.height() - 8
        else:
            ox, oy = 16, 64
            w, h = rect.width() - 32, rect.height() - 88

        # Draw Download (blue)
        painter.setPen(QtGui.QPen(self.line_dl, 2))
        points = [
            QtCore.QPointF(
                ox + i * w / (self.max_history - 1),
                oy + h - (v / max_val) * h
            )
            for i, v in enumerate(self.recv_hist)
        ]
        if len(points) > 1:
            painter.drawPolyline(*points)

        # Draw Upload (orange)
        painter.setPen(QtGui.QPen(self.line_ul, 2))
        points = [
            QtCore.QPointF(
                ox + i * w / (self.max_history - 1),
                oy + h - (v / max_val) * h
            )
            for i, v in enumerate(self.sent_hist)
        ]
        if len(points) > 1:
            painter.drawPolyline(*points)

        # Draw border
        painter.setPen(QtGui.QPen(QtGui.QColor("#444"), 2))
        painter.drawRoundedRect(QRectF(rect).adjusted(1, 1, -2, -2), 12, 12)

        # Draw current download speed line and label
        y_dl = oy + h - (self.last_dl / max_val) * h
        painter.setPen(QtGui.QPen(self.line_dl, 1, QtCore.Qt.DashLine))
        painter.drawLine(QtCore.QPointF(ox, y_dl), QtCore.QPointF(ox + w, y_dl))
        painter.setPen(QtGui.QPen(self.line_dl))
        painter.setFont(QtGui.QFont("Segoe UI", 10, QtGui.QFont.Bold))
        painter.drawText(int(ox + 2), int(y_dl - 6), f"↓ {self.last_dl:.2f} MB/s")

        # Draw current upload speed line and label 
        y_ul = oy + h - (self.last_ul / max_val) * h
        painter.setPen(QtGui.QPen(self.line_ul, 1, QtCore.Qt.DashLine))
        painter.drawLine(QtCore.QPointF(ox, y_ul), QtCore.QPointF(ox + w, y_ul))
        painter.setPen(QtGui.QPen(self.line_ul))
        painter.setFont(QtGui.QFont("Segoe UI", 10, QtGui.QFont.Bold))
        painter.drawText(int(ox + 2), int(y_ul - 6), f"↑ {self.last_ul:.2f} MB/s")
        # Draw scale label (top right)
        painter.setPen(QtGui.QPen(QtGui.QColor("#aaa")))
        painter.setFont(QtGui.QFont("Segoe UI", 9))
        painter.drawText(rect.width() - 120, oy - 30, f"Scale: {max_val:.2f} MB/s")
        # Draw resize grip (bottom-right)
        painter.setPen(QtGui.QPen(QtGui.QColor("#aaa")))
        size = 16
        for i in range(4, size, 4):
            painter.drawLine(self.width()-i, self.height(), self.width(), self.height()-i)


    def mousePressEvent(self, e):
        grip_size = 16
        in_grip_area = (
            self.width() - grip_size < e.x() < self.width() and
            self.height() - grip_size < e.y() < self.height()
        )
        if in_grip_area and e.button() == QtCore.Qt.LeftButton:
            self._resizing = True
            self._resize_start_pos = e.globalPos()
            self._resize_start_geom = self.geometry()
            self.setCursor(QtCore.Qt.SizeFDiagCursor)
        elif not self.locked and e.button() == QtCore.Qt.LeftButton:
            self._drag_offset = e.globalPos() - self.frameGeometry().topLeft()
            self.setCursor(QtCore.Qt.OpenHandCursor)

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
            self.setCursor(QtCore.Qt.SizeFDiagCursor)
        elif not self.locked and self._drag_offset and (e.buttons() & QtCore.Qt.LeftButton):
            self.move(e.globalPos() - self._drag_offset)
            self.setCursor(QtCore.Qt.ClosedHandCursor)
        else:
            self.setCursor(QtCore.Qt.ArrowCursor)

    def mouseReleaseEvent(self, e):
        self._resizing = False
        self._resize_start_pos = None
        self._resize_start_geom = None
        self.setCursor(QtCore.Qt.ArrowCursor)
        if not self.locked:
            self._drag_offset = None
        g = self.geometry()
        self.config.data["graph_geometry"] = [g.x(), g.y(), g.width(), g.height()]
        self.config.save()


    # --- Context Menu ---
    def contextMenuEvent(self, event):
        menu = QtWidgets.QMenu(self)

        # Always on top
        atop_action = QtWidgets.QAction("Always On Top", self)
        atop_action.setCheckable(True)
        atop_action.setChecked(self.windowFlags() & Qt.WindowStaysOnTopHint)
        atop_action.triggered.connect(self.toggle_always_on_top)
        menu.addAction(atop_action)

        # Lock position
        lock_action = QtWidgets.QAction("Lock Position", self)
        lock_action.setCheckable(True)
        lock_action.setChecked(self.locked)
        lock_action.triggered.connect(self.toggle_lock)
        menu.addAction(lock_action)

        # Minimal mode
        minimal_action = QtWidgets.QAction("Minimal Graph Mode", self)
        minimal_action.setCheckable(True)
        minimal_action.setChecked(self.minimal_mode)
        minimal_action.triggered.connect(self.toggle_minimal_mode)
        menu.addAction(minimal_action)

        # Hide graph
        hide_action = QtWidgets.QAction("Hide Graph", self)
        hide_action.triggered.connect(self.hide)
        menu.addAction(hide_action)

        menu.exec_(event.globalPos())

    def toggle_always_on_top(self):
        self.always_on_top = not self.always_on_top
        flags = self._base_flags
        if self.always_on_top:
            flags |= Qt.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        self.show()
        self.raise_()
        self.activateWindow()
        self.config.data["graph_always_on_top"] = self.always_on_top
        self.config.save()


    def toggle_lock(self):
        self.locked = not self.locked
        self.config.data["locked"] = self.locked
        self.config.save()

    def toggle_minimal_mode(self):
        self.minimal_mode = not getattr(self, "minimal_mode", False)
        self.controls_widget.setVisible(not self.minimal_mode)
        if self.minimal_mode:
            self.setMinimumSize(120, 32)  # Allow much smaller size in minimal mode
        else:
            self.setMinimumSize(500, 250)  # Restore default minimum
        self.update()

    # def hide_graph(self):
    #     self.hide()

    # def closeEvent(self, event):
    #     self.timer.stop()
    #     event.accept()