# ui/tray.py

import threading
import os
import pystray
from PIL import Image, ImageDraw


class TrayIcon:
    def __init__(self, app, icon_path=None):
        self.app = app

        # load your .ico if it exists, else generate a fallback
        if icon_path and os.path.exists(icon_path):
            try:
                self.image = Image.open(icon_path)
            except Exception:
                self.image = self._make_image()
        else:
            self.image = self._make_image()

        # build tray menu
        self.icon = pystray.Icon(
            "TinyNetUse",
            self.image,
            menu=pystray.Menu(
                pystray.MenuItem("Open", self._on_open),
                pystray.MenuItem("Exit", self._on_exit),
            )
        )

    def _make_image(self):
        size = (64, 64)
        img = Image.new("RGBA", size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.ellipse((8, 8, 56, 56), fill=(255, 255, 255, 255))
        return img

    def _on_open(self, icon, item):
        # stop tray loop, then restore & resume
        self.icon.stop()
        self.app.after(0, self.app.deiconify)
        self.app.after(0, self.app.resume)

    def _on_exit(self, icon, item):
        self.icon.stop()
        self.app.after(0, self.app.quit)

    def run(self):
        # new thread for the tray icon
        threading.Thread(target=self.icon.run, daemon=True).start()
