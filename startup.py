import os
import sys
from pathlib import Path
import pythoncom
import win32com.client


def install_startup():
    """Create a COM-based Windows shortcut in the user’s Startup folder."""
    pythoncom.CoInitialize()

    # Correctly build the Startup folder path
    startup_dir = (
        Path(os.getenv("APPDATA"))
        / "Microsoft"
        / "Windows"
        / "Start Menu"
        / "Programs"
        / "Startup"
    )
    startup_dir.mkdir(parents=True, exist_ok=True)

    # Shortcut file
    shortcut_path = startup_dir / "TinyNetUse.lnk"

    # Use WScript.Shell to create the .lnk
    shell = win32com.client.Dispatch("WScript.Shell")
    shortcut = shell.CreateShortcut(str(shortcut_path))

    exe_path = Path(sys.executable)
    if exe_path.suffix.lower() == ".exe":
        # Running as a bundled .exe
        shortcut.TargetPath = str(exe_path)
        shortcut.Arguments = ""
    else:
        # Running via python interpreter
        shortcut.TargetPath = str(exe_path)
        script = Path(__file__).parent / "main.py"
        shortcut.Arguments = f'"{script}"'

    # Working directory and icon
    shortcut.WorkingDirectory = str(Path(__file__).parent)
    icon_file = Path(__file__).parent / "ui" / "assets" / "icon.ico"
    if icon_file.exists():
        shortcut.IconLocation = str(icon_file)

    shortcut.Save()


def remove_startup():
    """Remove the TinyNetUse shortcut from the Windows Startup folder."""
    startup_dir = (
        Path(os.getenv("APPDATA"))
        / "Microsoft"
        / "Windows"
        / "Start Menu"
        / "Programs"
        / "Startup"
    )
    shortcut_path = startup_dir / "TinyNetUse.lnk"
    try:
        if shortcut_path.exists():
            shortcut_path.unlink()
    except Exception:
        pass
