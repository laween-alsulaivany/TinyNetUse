@echo off
:: build.bat — Full release build for TinyNetUse.
::
:: Step 1: PyInstaller folder build (produces dist\TinyNetUse\)
:: Step 2: Inno Setup compile
::
:: Prerequisites:
::   pip install -r requirements.lock
::   pip install --no-build-isolation --no-deps --editable .
::   UPX (optional): https://github.com/upx/upx/releases
::   Inno Setup 6:   https://jrsoftware.org/isdl.php

setlocal enabledelayedexpansion

:: Set UPX_DIR before running this script if you want compression.

for /f "usebackq delims=" %%V in (`.venv\Scripts\python.exe build_version_info.py --print-version`) do set "APP_VERSION=%%V"
if not defined APP_VERSION (
    echo ERROR: Could not read the application version.
    exit /b 1
)

.venv\Scripts\python.exe build_version_info.py build\windows-version-info.txt
if errorlevel 1 (
    echo ERROR: Could not generate Windows version metadata.
    exit /b 1
)

:: ── PyInstaller ───────────────────────────────────────────────────────────────

set PYINSTALLER_ARGS=--noconfirm --clean --onedir --windowed ^
  --icon=assets\windows-classic\TinyNetUse.ico ^
  --version-file=build\windows-version-info.txt ^
  --name TinyNetUse ^
  --add-data "assets;assets" ^
  --hidden-import win32com.client ^
  --hidden-import win32com.shell ^
  --hidden-import pythoncom

if defined UPX_DIR (
    set PYINSTALLER_ARGS=!PYINSTALLER_ARGS! --upx-dir "%UPX_DIR%"
)

echo.
echo [1/2] Building with PyInstaller...
.venv\Scripts\python.exe -m PyInstaller !PYINSTALLER_ARGS! main.py
if errorlevel 1 (
    echo.
    echo ERROR: PyInstaller build failed.
    exit /b 1
)

:: ── Inno Setup ────────────────────────────────────────────────────────────────

set ISCC="C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if not exist %ISCC% (
    echo.
    echo ERROR: Inno Setup not found at %ISCC%.
    echo Install it from https://jrsoftware.org/isdl.php and try again.
    exit /b 1
)

echo.
echo [2/2] Compiling installer with Inno Setup...
%ISCC% /DAppVersion=%APP_VERSION% packaging\installer.iss
if errorlevel 1 (
    echo.
    echo ERROR: Inno Setup compile failed.
    exit /b 1
)

echo.
echo Done. Output: installer\TinyNetUse-Setup-%APP_VERSION%.exe
