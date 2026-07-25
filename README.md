<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/TinyNetUse-horizontal-light.png">
  <img alt="TinyNetUse" src="docs/TinyNetUse-horizontal-dark.png" width="380">
</picture>

# TinyNetUse

Lightweight Windows desktop widget that shows real-time network upload/download speeds as a floating overlay. Includes an optional rolling graph window.

---

## Running from source

**Requirements:** Python 3.9+

```bash
pip install -r requirements.txt
python main.py
```

`config.json` is created next to `main.py` on first run and updated automatically.

---

## Building an executable

Install dependencies first if you haven't:

```bash
pip install -r requirements.txt
```

### Optional: UPX compression (recommended)

UPX compresses native binaries and reduces the final exe size by roughly 40-50%. Without it the build still works fine — it's just larger.

1. Download the latest UPX release from https://github.com/upx/upx/releases (e.g. `upx-5.x.x-win64.zip`).
2. Extract the zip to a permanent folder, for example `C:\tools\upx\`.
3. Add `--upx-dir C:\tools\upx` to the PyInstaller command below.

### Folder build (required for the installer)

Produces `dist/TinyNetUse/TinyNetUse.exe`. The config file lives alongside the exe in the same folder. This is the build used by the Inno Setup installer.

```bash
pyinstaller --noconfirm --onedir --windowed ^
  --icon=assets/windows-classic/TinyNetUse.ico ^
  --name TinyNetUse ^
  --add-data "assets;assets" ^
  --hidden-import win32com.client ^
  --hidden-import win32com.shell ^
  --hidden-import pythoncom ^
  --upx-dir C:\tools\upx ^
  main.py
```

Remove `--upx-dir ...` if you skipped the UPX step.

### Single-file build (portable)

Produces a single `dist/TinyNetUse.exe`. Config is saved next to the exe (not inside the archive). Useful for distributing a single file without an installer.

```bash
pyinstaller --noconfirm --onefile --windowed ^
  --icon=assets/windows-classic/TinyNetUse.ico ^
  --name TinyNetUse ^
  --add-data "assets;assets" ^
  --hidden-import win32com.client ^
  --hidden-import win32com.shell ^
  --hidden-import pythoncom ^
  --upx-dir C:\tools\upx ^
  main.py
```

> The `--hidden-import` flags are required because PyInstaller doesn't detect COM imports (`startup.py`) automatically.

Output lands in `dist/`. The `build/` folder and `TinyNetUse.spec` can be deleted after a successful build.

---

## Building the installer

The installer bundles the folder build into a single `TinyNetUse-Setup-1.0.0.exe` that handles installation, Start Menu shortcuts, and optional desktop/startup entries.

**Prerequisites:** Inno Setup 6 — https://jrsoftware.org/isdl.php

1. Run the folder build above so `dist\TinyNetUse\` exists.
2. Compile the installer:

```bash
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer.iss
```

Or open `installer.iss` in the Inno Setup IDE and press **Build → Compile**.

Output: `installer\TinyNetUse-Setup-1.0.0.exe`

For convenience, `build.bat` runs both steps in sequence (see below).

---

## build.bat

`build.bat` automates the full release build: PyInstaller folder build followed by Inno Setup compile.

```bash
build.bat
```

Edit the `UPX_DIR` variable at the top of the file to point to your UPX folder, or leave it empty to skip compression.

---

## Usage

- **Right-click** the widget to access settings, toggle the graph, lock position, and quit.
- **Left-click and drag** to move. Drag the bottom-right corner to resize.
- Settings and window positions are saved to `config.json` automatically.
- "Launch at Startup" in Settings installs a shortcut in the Windows Startup folder.
