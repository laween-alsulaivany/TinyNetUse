import customtkinter as ctk
from config import Config
from startup import install_startup, remove_startup


class SettingsDialog(ctk.CTkToplevel):
    def __init__(self, parent, config: Config, apply_callback):
        super().__init__(parent)
        self.config_obj = config
        self.apply_callback = apply_callback

        self.title("Settings")
        self.geometry("600x550")
        self.resizable(False, False)
        self.center_window()

        self.build_ui()

    def center_window(self):
        self.update_idletasks()
        w = self.winfo_width()
        h = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (w // 2)
        y = (self.winfo_screenheight() // 2) - (h // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")

    def build_ui(self):
        cfg = self.config_obj.data

        frame = ctk.CTkScrollableFrame(self)
        frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Update Interval
        ctk.CTkLabel(frame, text="Update Interval (s)").pack(pady=(10, 0))
        self.interval_var = ctk.DoubleVar(value=cfg["update_interval"])
        steps = int((5.0 - 0.5) / 0.1)
        ctk.CTkSlider(
            frame,
            from_=0.5,
            to=5.0,
            number_of_steps=steps,
            variable=self.interval_var
        ).pack(fill="x", padx=10, pady=(0, 10))

        # Decimal Precision
        ctk.CTkLabel(frame, text="Decimal Precision").pack(pady=(10, 0))
        self.prec_var = ctk.IntVar(value=cfg["precision"])
        precision_frame = ctk.CTkFrame(frame)
        precision_frame.pack(pady=(0, 10))
        for p in (0, 1, 2):
            ctk.CTkRadioButton(
                precision_frame,
                text=str(p),
                variable=self.prec_var,
                value=p
            ).pack(side="left", padx=10)

        # Unit Selection
        ctk.CTkLabel(frame, text="Speed Unit").pack(pady=(10, 0))
        self.unit_var = ctk.StringVar(value=cfg["unit"])
        ctk.CTkOptionMenu(
            frame,
            variable=self.unit_var,
            values=["auto", "KB/s", "MB/s"],
        ).pack(pady=(0, 10))

        # Theme
        ctk.CTkLabel(frame, text="Theme").pack(pady=(10, 0))
        self.theme_var = ctk.StringVar(value=cfg["theme"])
        theme_frame = ctk.CTkFrame(frame)
        theme_frame.pack(pady=(0, 10))
        for t in ("light", "dark"):
            ctk.CTkRadioButton(
                theme_frame,
                text=t.capitalize(),
                variable=self.theme_var,
                value=t
            ).pack(side="left", padx=10)

        # Always‑on‑top
        self.top_var = ctk.BooleanVar(value=cfg["always_on_top"])
        ctk.CTkCheckBox(
            frame,
            text="Always on Top",
            variable=self.top_var
        ).pack(pady=(10, 0))

        # Opacity
        ctk.CTkLabel(frame, text="Window Opacity (%)").pack(pady=(10, 0))
        self.opacity_var = ctk.IntVar(value=int(cfg["opacity"] * 100))
        ctk.CTkSlider(
            frame,
            from_=50,
            to=100,
            number_of_steps=50,
            variable=self.opacity_var
        ).pack(fill="x", padx=10, pady=(0, 10))

        # Download threshold
        ctk.CTkLabel(
            frame, text="Alert if Download > (MB/s)").pack(pady=(10, 0))
        init_dl = cfg["notify_threshold"].get("download")
        self.nt_dl_var = ctk.StringVar(
            value=str(init_dl) if init_dl is not None else ""
        )
        ctk.CTkEntry(frame, textvariable=self.nt_dl_var).pack(pady=(0, 10))

        # Start Minimized
        self.min_var = ctk.BooleanVar(value=cfg.get("start_minimized", False))
        ctk.CTkCheckBox(
            frame,
            text="Start Minimized",
            variable=self.min_var
        ).pack(pady=(10, 0))

        # Launch at Startup
        self.boot_var = ctk.BooleanVar(value=cfg.get("start_on_boot", False))
        ctk.CTkCheckBox(
            frame,
            text="Launch at Windows Startup",
            variable=self.boot_var
        ).pack(pady=(0, 20))

        # Save button
        ctk.CTkButton(frame, text="Save",
                      command=self.on_save).pack(pady=(0, 30))

    def on_save(self):
        d = self.config_obj.data
        d["update_interval"] = self.interval_var.get()
        d["precision"] = self.prec_var.get()
        d["unit"] = self.unit_var.get()
        d["theme"] = self.theme_var.get()
        d["always_on_top"] = self.top_var.get()
        d["opacity"] = self.opacity_var.get() / 100.0

        # parse download threshold
        raw = self.nt_dl_var.get().strip()
        try:
            d["notify_threshold"]["download"] = float(raw) if raw else None
        except ValueError:
            d["notify_threshold"]["download"] = None

        # Start‑minimized & startup
        d["start_minimized"] = self.min_var.get()
        d["start_on_boot"] = self.boot_var.get()
        self.config_obj.save()

        # COM-based startup shortcut
        if d["start_on_boot"]:
            install_startup()
        else:
            remove_startup()

        self.apply_callback()
        self.destroy()
