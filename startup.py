# startup.py — Creates and removes the Windows Startup folder shortcut via COM/WScript.Shell.

import os
import sys
import pythoncom
import win32com.client
from pathlib import Path

# The Startup folder path is user-scoped (%APPDATA%), so no admin rights are required.
startup = (
    Path(os.getenv("APPDATA"))
    / "Microsoft"
    / "Windows"
    / "Start Menu"
    / "Programs"
    / "Startup"
)


def _make_shortcut(target, link_path, args="", work_dir=None, icon=None):
    shell = win32com.client.Dispatch("WScript.Shell")
    shortcut = shell.CreateShortcut(str(link_path))
    shortcut.TargetPath = str(target)
    shortcut.Arguments = args
    shortcut.WorkingDirectory = str(work_dir or target.parent)
    if icon and icon.exists():
        shortcut.IconLocation = str(icon)
    shortcut.Save()


def install_startup():
    pythoncom.CoInitialize()
    startup.mkdir(parents=True, exist_ok=True)
    link = startup / "TinyNetUse.lnk"
    exe = Path(sys.executable)
    icon = Path(__file__).parent / "assets" / "windows-classic" / "TinyNetUse.ico"

    if getattr(sys, "frozen", False):
        # Frozen exe: target is the app itself, cwd is the exe's own folder.
        args = ""
        work_dir = exe.parent
    else:
        # Script mode: pass main.py as the argument, and use the project folder
        # as cwd — NOT the Python interpreter's folder.
        script = Path(__file__).parent / "main.py"
        args = f'"{script}"'
        work_dir = Path(__file__).parent

    _make_shortcut(exe, link, args=args, work_dir=work_dir, icon=icon)
    return link


def remove_startup():
    pythoncom.CoInitialize()
    target = startup / "TinyNetUse.lnk"
    if target.exists():
        target.unlink()
