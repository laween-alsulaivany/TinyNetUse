"""Current-user Windows Startup shortcut handling."""

import os
from pathlib import Path
import sys

import pythoncom  # Required for COM initialization when handling Windows shortcuts
import win32com.client  # Required for creating and reading Windows shortcuts


SHORTCUT_NAME = "TinyNetUse.lnk"
STARTUP_FOLDER = (
    Path(os.environ["APPDATA"])
    / "Microsoft"
    / "Windows"
    / "Start Menu"
    / "Programs"
    / "Startup"
)


def startup_shortcut_path() -> Path:
    return STARTUP_FOLDER / SHORTCUT_NAME


def startup_shortcut_exists() -> bool:
    return startup_shortcut_path().is_file()


# Frozen apps always point at sys.executable, and not the PyInstaller's temp folder.
def _startup_command():
    executable = Path(sys.executable).resolve()
    if getattr(sys, "frozen", False):
        return executable, "", executable.parent, executable

    # Non-frozen apps point at the Python interpreter and the script location.
    project_root = Path(__file__).resolve().parents[2]
    script = project_root / "main.py"
    icon = project_root / "assets" / "windows-classic" / "TinyNetUse.ico"
    return executable, f'"{script}"', script.parent, icon


def _read_shortcut(path: Path):
    pythoncom.CoInitialize()
    try:
        shell = win32com.client.Dispatch("WScript.Shell")
        shortcut = shell.CreateShortcut(str(path))
        return shortcut.TargetPath, shortcut.Arguments
    finally:
        pythoncom.CoUninitialize()


def _write_shortcut(path, target, arguments, work_dir, icon):
    pythoncom.CoInitialize()
    try:
        shell = win32com.client.Dispatch("WScript.Shell")
        shortcut = shell.CreateShortcut(str(path))
        shortcut.TargetPath = str(target)
        shortcut.Arguments = arguments
        shortcut.WorkingDirectory = str(work_dir)
        if icon.is_file():
            shortcut.IconLocation = str(icon)
        shortcut.Save()
    finally:
        pythoncom.CoUninitialize()


def _same_path(first, second) -> bool:
    return os.path.normcase(os.path.abspath(first)) == os.path.normcase(
        os.path.abspath(second)
    )


def _valid_shortcut_target(target, arguments) -> bool:
    if not target:
        return False

    target = Path(target)
    arguments = arguments or ""
    if not target.is_file():
        return False

    # This also accepts the shortcut created by the installer.
    if target.name.casefold() == "tinynetuse.exe":
        return not arguments.strip()

    expected_target, expected_args, _, _ = _startup_command()
    return _same_path(target, expected_target) and arguments.strip() == expected_args


def is_startup_enabled() -> bool:
    path = startup_shortcut_path()
    if not path.is_file():
        return False

    try:
        target, arguments = _read_shortcut(path)
        return _valid_shortcut_target(target, arguments)
    except Exception:
        return False


def enable_startup() -> Path:
    path = startup_shortcut_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    target, arguments, work_dir, icon = _startup_command()
    _write_shortcut(path, target, arguments, work_dir, icon)

    if not is_startup_enabled():
        raise OSError("Windows did not create a valid TinyNetUse Startup shortcut.")
    return path


def disable_startup() -> None:
    startup_shortcut_path().unlink(missing_ok=True)
