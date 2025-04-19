# startup.py

import os
import sys
import pythoncom
import win32com.client
from pathlib import Path

# Correct startup folder
startup = (
    Path(os.getenv("APPDATA"))
    / "Microsoft"
    / "Windows"
    / "Start Menu"
    / "Programs"
    / "Startup"
)

def _make_shortcut(target, link_path, icon=None):
    """Helper: create or overwrite a .lnk at link_path pointing at target."""
    shell = win32com.client.Dispatch("WScript.Shell")
    shortcut = shell.CreateShortcut(str(link_path))
    shortcut.TargetPath = str(target)
    shortcut.Arguments = ""
    shortcut.WorkingDirectory = str(target.parent)
    if icon and icon.exists():
        shortcut.IconLocation = str(icon)
    shortcut.Save()

def install_startup():
    pythoncom.CoInitialize()
    app_dir = Path(__file__).parent
    startup.mkdir(parents=True, exist_ok=True)
    link = startup / "TinyNetUse.lnk"
    exe = Path(sys.executable)
    icon = app_dir / "assets" / "icon.ico"
    _make_shortcut(exe, link, icon)
    return link

def remove_startup():
    target = startup / "TinyNetUse.lnk"
    if target.exists():
        target.unlink()