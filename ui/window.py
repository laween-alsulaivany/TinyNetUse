# ui/window.py

import customtkinter as ctk
from monitor import NetworkMonitor
from utils import format_speed
from config import Config
from ui.theme import apply_theme
from ui.settings import SettingsDialog
from ui.tray import TrayIcon
from win10toast import ToastNotifier

# Matplotlib imports for the graph
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg


class TinyNetUseApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("TinyNetUse")

        # load config & apply theme
        self.config_obj = Config()
        apply_theme(self.config_obj.data["theme"])

        # monitor + notifier
        self.monitor = NetworkMonitor(self.config_obj.data["interface"])
        self.notifier = ToastNotifier()

        # icon for tray fallback
        self.icon_path = "ui/assets/icon.ico"

        # rolling history buffers
        self.max_history = 60
        self.hist_sent = [0.0] * self.max_history
        self.hist_recv = [0.0] * self.max_history

        # build UI and geometry, then start loop
        self.build_ui()
        self.load_geometry()
        self._after_id = None
        self.update_loop()

    def build_ui(self):
        cfg = self.config_obj.data

        # Interface dropdown
        self.if_var = ctk.StringVar(value=cfg["interface"])
        ctk.CTkOptionMenu(
            self,
            variable=self.if_var,
            values=NetworkMonitor.list_interfaces(),
            command=self.change_interface
        ).pack(pady=(10, 5))

        # Speed labels
        self.dl_label = ctk.CTkLabel(self, text="↓ 0 B/s")
        self.dl_label.pack(pady=2)
        self.ul_label = ctk.CTkLabel(self, text="↑ 0 B/s")
        self.ul_label.pack(pady=2)

        # Graph container
        graph_frame = ctk.CTkFrame(self)
        graph_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.figure = Figure(figsize=(4, 1.5), dpi=100)
        self.ax = self.figure.add_subplot(111)
        self.ax.set_title("Last 60 seconds")
        self.ax.set_xlabel("Samples")
        self.ax.set_ylabel("MB/s")
        self.line_sent, = self.ax.plot([], [], label="Upload")
        self.line_recv, = self.ax.plot([], [], label="Download")
        self.ax.legend(loc="upper right")
        self.figure.tight_layout()

        self.canvas = FigureCanvasTkAgg(self.figure, master=graph_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

        # Settings button
        ctk.CTkButton(self, text="⚙️", width=30, command=self.open_settings)\
            .pack(pady=(0, 10))

        # Always‑on‑top & opacity
        self.attributes("-topmost", cfg["always_on_top"])
        self.attributes("-alpha", cfg["opacity"])

    def change_interface(self, val):
        self.monitor = NetworkMonitor(val)
        self.config_obj.data["interface"] = val
        self.config_obj.save()

    def open_settings(self):
        SettingsDialog(self, self.config_obj,
                       apply_callback=self.apply_settings)

    def apply_settings(self):
        d = self.config_obj.data
        self.attributes("-topmost", d["always_on_top"])
        self.attributes("-alpha", d["opacity"])
        apply_theme(d["theme"])
        self.monitor.interface = d["interface"]

    def load_geometry(self):
        """Restore size/position, and if configured, start minimized into tray."""
        cfg = self.config_obj.data

        # restore previous geometry if present
        geom = cfg.get("geometry")
        if geom:
            self.geometry(geom)

        # handle start-minimized
        if cfg.get("start_minimized"):
            # withdraw from screen and launch tray icon
            self.withdraw()
            TrayIcon(self, icon_path=self.icon_path).run()

        # override close button to send to tray
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def on_close(self):
        """Hide window and show tray icon (cancelling any pending updates)."""
        # cancel pending update to avoid callbacks on destroyed widgets
        if self._after_id is not None:
            self.after_cancel(self._after_id)
            self._after_id = None

        # save geometry
        self.config_obj.data["geometry"] = self.geometry()
        self.config_obj.save()

        # hide and show tray icon
        self.withdraw()
        TrayIcon(self, icon_path=self.icon_path).run()

    def resume(self):
        """Called when restoring from tray—respawn the update loop."""
        # immediately fire off a new loop
        self.update_loop()

    def update_loop(self):
        sent_bps, recv_bps = self.monitor.get_speed()
        cfg = self.config_obj.data

        # update labels
        unit, prec = cfg["unit"], cfg["precision"]
        self.dl_label.configure(text="↓ " + format_speed(recv_bps, unit, prec))
        self.ul_label.configure(text="↑ " + format_speed(sent_bps, unit, prec))

        # alert threshold
        thr = cfg["notify_threshold"].get("download")
        if thr and (recv_bps / (1 << 20)) > thr:
            self.notifier.show_toast(
                "TinyNetUse",
                f"Download > {thr} MB/s!",
                duration=3,
                threaded=True
            )

        # append to history (MB/s)
        self.hist_sent.append(sent_bps / (1 << 20))
        self.hist_recv.append(recv_bps / (1 << 20))
        if len(self.hist_sent) > self.max_history:
            self.hist_sent.pop(0)
            self.hist_recv.pop(0)

        # refresh graph with auto-scaling
        self.line_sent.set_data(range(len(self.hist_sent)), self.hist_sent)
        self.line_recv.set_data(range(len(self.hist_recv)), self.hist_recv)
        self.ax.relim()
        self.ax.autoscale_view(True, True, True)
        self.figure.tight_layout()
        self.canvas.draw_idle()

        # schedule next
        self._after_id = self.after(
            int(cfg["update_interval"] * 1000),
            self.update_loop
        )


if __name__ == "__main__":
    app = TinyNetUseApp()
    app.mainloop()
