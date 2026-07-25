; installer.iss — Inno Setup script for TinyNetUse
;
; Prerequisites:
;   1. Build the app with PyInstaller in --onedir mode first (see README.md).
;      The dist\TinyNetUse\ folder must exist before compiling this script.
;   2. Install Inno Setup 6: https://jrsoftware.org/isdl.php
;   3. Compile: right-click installer.iss → Compile, or run:
;      "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer.iss
;   Output: installer\TinyNetUse-Setup-1.0.0.exe

#define AppName      "TinyNetUse"
#define AppVersion   "1.0.0"
#define AppPublisher "Laween Al-Sulaivany"
#define AppExeName   "TinyNetUse.exe"

[Setup]
AppId={{A3F1B2C4-9E87-4D56-BF12-7C3A05E91D28}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
AppCopyright=Copyright (C) 2025-2026 {#AppPublisher}

; Install to per-user AppData\Local so no admin rights are needed.
; Users can change this during install.
DefaultDirName={localappdata}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes

; Prevent downgrade without uninstalling first.
AppMutex={#AppName}Mutex

; Installer appearance
SetupIconFile=assets\windows-classic\TinyNetUse.ico
WizardStyle=modern
WizardSizePercent=100

; License shown on the second screen of the installer.
LicenseFile=LICENSE

; Output
OutputDir=installer
OutputBaseFilename={#AppName}-Setup-{#AppVersion}
Compression=lzma2/ultra64
SolidCompression=yes

; Architecture — 64-bit only
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64

; After install, launch the app.
RestartIfNeededByRun=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
; Desktop shortcut — checked by default.
Name: "desktopicon"; Description: "Create a &Desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: checkedonce

; Windows Startup — unchecked by default; user decides.
Name: "startupicon"; Description: "Launch {#AppName} when Windows starts"; GroupDescription: "Additional shortcuts:"

[Files]
; Include everything from the --onedir PyInstaller build recursively.
; This handles both PyInstaller 5.x (flat layout) and 6.x (_internal/ subfolder).
Source: "dist\{#AppName}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
; Start Menu entry
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"; IconFilename: "{app}\{#AppExeName}"; WorkingDir: "{app}"

; Desktop shortcut (only if task selected)
Name: "{commondesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; IconFilename: "{app}\{#AppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

; Startup folder shortcut (only if task selected)
; This is the same location that the in-app Settings toggle manages, so they
; work together: enabling in the installer and then disabling in Settings (or
; vice versa) correctly creates or removes the same shortcut file.
Name: "{userstartup}\{#AppName}"; Filename: "{app}\{#AppExeName}"; WorkingDir: "{app}"; Tasks: startupicon

[Run]
; Offer to launch after install finishes.
Filename: "{app}\{#AppExeName}"; Description: "Launch {#AppName}"; Flags: nowait postinstall skipifsilent

[UninstallRun]
; Stop the running instance before uninstalling so the exe isn't locked.
Filename: "taskkill.exe"; Parameters: "/f /im {#AppExeName}"; Flags: runhidden; RunOnceId: "StopApp"
