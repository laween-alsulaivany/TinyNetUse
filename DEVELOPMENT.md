# TinyNetUse development

This document covers local development, tests, Windows builds, and releases. Normal users should use the downloads described in [README.md](README.md).

## Prerequisites

- 64-bit Windows 11, the currently verified development and release platform
- 64-bit Python 3.14.7, the version currently used for development and tests
- Git
- Inno Setup 6, only when building the installer
- UPX, optional

The commands below keep all Python packages inside the repository's virtual environment.

## Create the virtual environment

From the repository root in PowerShell:

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

The normal editable install gets runtime dependencies from `pyproject.toml` and adds pytest, pytest-qt, and PyInstaller through the `dev` extra.

For a release environment, install the exact tested dependency set instead:

```powershell
.\.venv\Scripts\python.exe -m pip install --requirement requirements.lock
.\.venv\Scripts\python.exe -m pip install --no-build-isolation --no-deps --editable .
```

`requirements.lock` is pinned for 64-bit Windows and Python 3.14.7. The second command installs TinyNetUse itself without changing the locked dependency versions.

## Run from source

```powershell
.\.venv\Scripts\python.exe -m tinynetuse
```

Source mode stores its settings in `%LOCALAPPDATA%\TinyNetUse\dev\config.json`, so running the app does not create or update repository files.

## Run tests

Run the full test suite in one command:

```powershell
.\.venv\Scripts\python.exe -m pytest
```

To run one test file:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_units.py
```

The suite is designed for Windows because TinyNetUse and its single-instance code use Windows APIs. Network counters, Startup shortcuts, monitor layouts, and user config paths are mocked or redirected to temporary folders. Only the settings dialog tests use pytest-qt.

## Continuous integration

`.github/workflows/ci.yml` runs on every pull request and every push to `main`. It uses a Windows x64 runner with Python 3.14.7, installs the exact dependencies in `requirements.lock`, checks the tracked Python files for syntax errors, and runs the full pytest suite.

The CI job only has read access to repository contents. It does not build or publish a release.

## Configuration storage

- Installed and folder builds use `%LOCALAPPDATA%\TinyNetUse\config.json`.
- Portable builds use `config.json` beside `TinyNetUse.exe` when `portable.flag` is beside the executable.
- Source mode uses `%LOCALAPPDATA%\TinyNetUse\dev\config.json`.

When an installed build finds an older `config.json` beside its executable and the AppData config does not exist yet, it validates and moves those settings to AppData once. An interactive uninstall asks whether to keep or remove AppData settings. Silent uninstalls keep them.

## Project structure

| Path | Purpose |
| --- | --- |
| `src/tinynetuse/app.py` | Overlay, tray icon, shared sample timer, and application startup |
| `src/tinynetuse/network.py` | Adapter discovery and canonical bytes-per-second sampling |
| `src/tinynetuse/units.py` | Network rate conversion and formatting |
| `src/tinynetuse/config.py` | Defaults and `config.json` loading and saving |
| `src/tinynetuse/geometry.py` | Shared saved-window visibility and recovery logic |
| `src/tinynetuse/startup.py` | Current-user Windows Startup shortcut |
| `src/tinynetuse/settings_dialog.py` | Transactional Settings window |
| `src/tinynetuse/graph_window.py` | Rolling graph rendered from shared samples |
| `src/tinynetuse/about_dialog.py` | Version, license, and project information |
| `src/tinynetuse/single_instance.py` | Per-session ownership and local commands |
| `src/tinynetuse/version.py` | Canonical application version |
| `main.py` | Small compatibility and PyInstaller launcher |
| `tests/` | pytest test suite |
| `assets/` | Application and tray icons |
| `docs/` | README branding and screenshot assets |
| `.github/workflows/` | Windows CI and tagged release automation |
| `.github/ISSUE_TEMPLATE/` | Bug and feature request forms |
| `pyproject.toml` | Project metadata and runtime/dev dependency groups |
| `requirements.lock` | Exact Windows release dependency versions |
| `build_version_info.py` | Generates Windows executable version metadata |
| `build.bat` | Folder build followed by installer compilation |
| `packaging/installer.iss` | Inno Setup installer definition |

## Build with PyInstaller

Builds must use the virtual environment so PyInstaller packages the same dependencies used by the app and tests.

Generate the Windows executable metadata before either build type:

```powershell
.\.venv\Scripts\python.exe .\build_version_info.py .\build\windows-version-info.txt
```

### Folder build

The installer uses the folder build. It creates `dist\TinyNetUse\TinyNetUse.exe` and its supporting files.

```powershell
.\.venv\Scripts\python.exe -m PyInstaller `
  --noconfirm `
  --clean `
  --onedir `
  --windowed `
  --icon=assets\windows-classic\TinyNetUse.ico `
  --version-file=build\windows-version-info.txt `
  --name TinyNetUse `
  --add-data "assets;assets" `
  --hidden-import win32com.client `
  --hidden-import win32com.shell `
  --hidden-import pythoncom `
  main.py
```

The hidden imports are needed because PyInstaller does not detect the Windows COM imports in `startup.py` automatically.

### Portable build

The portable build creates `dist\TinyNetUse.exe`. Add an empty `portable.flag` beside it so the app intentionally stores `config.json` in that folder.

```powershell
.\.venv\Scripts\python.exe -m PyInstaller `
  --noconfirm `
  --clean `
  --onefile `
  --windowed `
  --icon=assets\windows-classic\TinyNetUse.ico `
  --version-file=build\windows-version-info.txt `
  --name TinyNetUse `
  --add-data "assets;assets" `
  --hidden-import win32com.client `
  --hidden-import win32com.shell `
  --hidden-import pythoncom `
  main.py
```

Create the marker after the build:

```powershell
New-Item -ItemType File -Path .\dist\portable.flag -Force
```

Distribute `TinyNetUse.exe` and `portable.flag` together. If the marker is missing, the executable behaves like an installed build and uses AppData.

Both build types use the same single-instance behavior. Starting one build while another is running shows the existing instance instead of creating a second tray icon or monitor.

## Build the installer

Install [Inno Setup 6](https://jrsoftware.org/isdl.php), then create the folder build before compiling `packaging\installer.iss`.

Compile from PowerShell:

```powershell
$version = & .\.venv\Scripts\python.exe .\build_version_info.py --print-version
& "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe" "/DAppVersion=$version" ".\packaging\installer.iss"
```

The output is `installer\TinyNetUse-Setup-<version>.exe`. Inno Setup receives `<version>` from `src\tinynetuse\version.py` through the command above.

For a normal release build, `build.bat` runs the folder build and installer compile in sequence:

```powershell
.\build.bat
```

The script expects Inno Setup at its standard 64-bit Windows location.

## Optional UPX compression

UPX can reduce the size of PyInstaller output, but it is not required for development or releases. Download it from the [official UPX releases](https://github.com/upx/upx/releases), extract it, and either:

- set `UPX_DIR` in your terminal before running `build.bat`, or
- add `--upx-dir C:\path\to\upx` to a manual PyInstaller command.

Leave `UPX_DIR` undefined and omit `--upx-dir` to build without compression.

## Versioning and releases

`src\tinynetuse\version.py` is the one application version source. Use three numeric parts such as `1.2.0`. PyInstaller metadata, Qt application metadata, package metadata, the installer version, and the installer filename all derive from it.

Prepare a release like this:

1. Update `__version__` in `src\tinynetuse\version.py`.
2. Update `requirements.lock` if dependencies changed.
3. Run the full pytest suite and the manual Windows checks below.
4. Commit and push the release changes to `main`, then wait for CI to pass.
5. Create and push a matching tag:

```powershell
git tag -a v1.2.0 -m "TinyNetUse 1.2.0"
git push origin v1.2.0
```

Pushing the tag starts `.github/workflows/release.yml`. The workflow:

1. Rejects tags that are not exactly `v<major>.<minor>.<patch>` or do not match `src\tinynetuse\version.py`.
2. Creates a clean Python 3.14.7 virtual environment from `requirements.lock` and runs syntax checks and pytest again.
3. Builds the Windows x64 folder application, installer, and one-file portable executable from that tag.
4. Checks the application and installer version metadata.
5. Packages the portable executable with `portable.flag`, creates SHA-256 hashes, and publishes a GitHub Release with generated notes.

The release contains:

- `TinyNetUse-Setup-<version>.exe`
- `TinyNetUse-Portable-<version>.zip`
- `SHA256SUMS.txt`

The generated release notes can be edited on GitHub when a release needs hand-written details. Nothing is published by CI or by an untagged build.

Before tagging, manually test the installer and portable package on 64-bit Windows 11. Check first install, upgrade over the previous version, startup behavior, repeated launches, overlay recovery, and uninstall.

### Future SignPath signing

The release workflow currently names its intermediate artifact `unsigned-build-<version>`. SignPath belongs between the `build` and `package` jobs. The future signing job should sign both candidate EXE files and give the `package` job a new signed artifact. Packaging and SHA-256 generation stay after signing, so unsigned files cannot be mistaken for final signed assets.

Do not rename the unsigned artifact to imply that it is signed until the SignPath job and credentials are actually configured.

## Updating dependency pins

Dependency ranges belong in `pyproject.toml`. `requirements.lock` records the complete tested release environment, including transitive dependencies.

To update it intentionally:

1. Create a clean 64-bit Python 3.14.7 virtual environment.
2. Install the project with `pip install -e ".[dev]"`.
3. Run the full tests and both Windows builds.
4. Run `python -m pip freeze --exclude-editable` and replace the package lines in `requirements.lock`, keeping its two-line header.

Commit `pyproject.toml` and `requirements.lock` together whenever dependency ranges or pins change.

## Troubleshooting

### The Python launcher cannot find Python 3.14

Run `py --list` to check registered installations. Repair or reinstall 64-bit Python 3.14.7 with the Python launcher enabled if it is missing.

### Python reports a missing package

Make sure commands use `.\.venv\Scripts\python.exe`, then reinstall the project dependencies:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

### PyInstaller cannot replace files in `dist`

Quit TinyNetUse from its tray menu before rebuilding. If the overlay is hidden, launching an existing build with `--quit` asks the running instance to close:

```powershell
.\dist\TinyNetUse\TinyNetUse.exe --quit
```

### Inno Setup cannot find the application files

Run the PyInstaller folder build first and confirm that `dist\TinyNetUse\TinyNetUse.exe` exists. The portable one-file build is not the installer input.

### UPX is missing or fails

Remove the `--upx-dir` argument, or leave `UPX_DIR` empty in `build.bat`. UPX is optional and does not affect app behavior.

### Windows SmartScreen warns about a build

TinyNetUse builds are not currently code-signed. SmartScreen warnings can appear until a signing process is added.
