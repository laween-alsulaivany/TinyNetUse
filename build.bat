@echo off
:: build.bat — Full release build for TinyNetUse.
::
:: Step 1: PyInstaller folder build (produces dist\TinyNetUse\)
:: Step 2: Inno Setup compile    (produces installer\TinyNetUse-Setup-1.0.0.exe)
::
:: Prerequisites:
::   pip install -r requirements.txt
::   UPX (optional): https://github.com/upx/upx/releases
::   Inno Setup 6:   https://jrsoftware.org/isdl.php

:: Set your UPX folder here, or leave empty to skip compression.
set UPX_DIR=C:\tools\upx

setlocal enabledelayedexpansion

:: ── PyInstaller ───────────────────────────────────────────────────────────────

set PYINSTALLER_ARGS=--noconfirm --onedir --windowed ^
  --icon=assets\windows-classic\TinyNetUse.ico ^
  --name TinyNetUse ^
  --add-data "assets;assets" ^
  --hidden-import win32com.client ^
  --hidden-import win32com.shell ^
  --hidden-import pythoncom

if not "%UPX_DIR%"=="" (
    set PYINSTALLER_ARGS=!PYINSTALLER_ARGS! --upx-dir "%UPX_DIR%"
)

echo.
echo [1/2] Building with PyInstaller...
pyinstaller !PYINSTALLER_ARGS! main.py
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
%ISCC% installer.iss
if errorlevel 1 (
    echo.
    echo ERROR: Inno Setup compile failed.
    exit /b 1
)

echo.
echo Done. Output: installer\TinyNetUse-Setup-1.0.0.exe
