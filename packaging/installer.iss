; Build dist\TinyNetUse with PyInstaller before compiling this script.

#ifndef AppVersion
  #error "Pass AppVersion from src/tinynetuse/version.py when compiling the installer"
#endif

#define AppName      "TinyNetUse"
#define AppPublisher "Laween Al-Sulaivany"
#define AppExeName   "TinyNetUse.exe"
#define AppURL       "https://github.com/laween-alsulaivany/TinyNetUse"
#define AppUpdatesURL AppURL + "/releases"
#define AppCopyright "Copyright (C) 2025-2026 " + AppPublisher

[Setup]
AppId={{A3F1B2C4-9E87-4D56-BF12-7C3A05E91D28}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
AppCopyright={#AppCopyright}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}
AppUpdatesURL={#AppUpdatesURL}
UninstallDisplayIcon={app}\{#AppExeName}
VersionInfoCompany={#AppPublisher}
VersionInfoCopyright={#AppCopyright}
VersionInfoDescription={#AppName} Setup
VersionInfoProductName={#AppName}
VersionInfoProductTextVersion={#AppVersion}
VersionInfoProductVersion={#AppVersion}
VersionInfoTextVersion={#AppVersion}
VersionInfoVersion={#AppVersion}

PrivilegesRequired=lowest
DefaultDirName={localappdata}\Programs\{#AppName}
DisableDirPage=yes
CloseApplications=yes
CloseApplicationsFilter={#AppExeName}
RestartApplications=no

SetupIconFile=..\assets\windows-classic\TinyNetUse.ico
WizardStyle=modern
WizardSizePercent=100
LicenseFile=..\LICENSE

OutputDir=..\installer
OutputBaseFilename={#AppName}-Setup-{#AppVersion}
Compression=lzma2/ultra64
SolidCompression=yes

; TinyNetUse ships as a 64-bit application.
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
RestartIfNeededByRun=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &Desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: checkedonce
Name: "startupicon"; Description: "Launch {#AppName} when Windows starts"; GroupDescription: "Additional shortcuts:"

[Files]
; Settings and the portable marker do not belong in an installed build.
Source: "..\dist\{#AppName}\*"; DestDir: "{app}"; Excludes: "\config.json,\portable.flag"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{userprograms}\{#AppName}\{#AppName}"; Filename: "{app}\{#AppExeName}"; IconFilename: "{app}\{#AppExeName}"; WorkingDir: "{app}"
Name: "{userdesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; IconFilename: "{app}\{#AppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon
Name: "{userstartup}\{#AppName}"; Filename: "{app}\{#AppExeName}"; WorkingDir: "{app}"; Tasks: startupicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "Launch {#AppName}"; Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "{app}\{#AppExeName}"; Parameters: "--quit"; Flags: runhidden skipifdoesntexist; RunOnceId: "StopAppGracefully"
; Keep this fallback for a frozen or older process that cannot answer IPC.
Filename: "{sys}\taskkill.exe"; Parameters: "/f /im ""{#AppExeName}"""; Flags: runhidden; RunOnceId: "StopApp"

[UninstallDelete]
; Settings can create this shortcut after installation.
Type: files; Name: "{userstartup}\{#AppName}.lnk"

[Code]
const
  LegacyUninstallKey = 'Software\Microsoft\Windows\CurrentVersion\Uninstall\{A3F1B2C4-9E87-4D56-BF12-7C3A05E91D28}_is1';

var
  LegacyConfigBackup: String;
  RemoveUserData: Boolean;

procedure StopRunningApp;
var
  ResultCode: Integer;
begin
  if FileExists(ExpandConstant('{app}\{#AppExeName}')) then
    Exec(ExpandConstant('{app}\{#AppExeName}'), '--quit', '', SW_HIDE,
      ewWaitUntilTerminated, ResultCode);
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  LegacyUninstaller: String;
  ResultCode: Integer;
begin
  Result := '';
  StopRunningApp;

  { Version 1.0.0 was registered as an admin install. }
  if not RegQueryStringValue(HKLM64, LegacyUninstallKey,
    'UninstallString', LegacyUninstaller) then
    Exit;

  if FileExists(ExpandConstant('{localappdata}\{#AppName}\config.json')) then
  begin
    LegacyConfigBackup := ExpandConstant('{tmp}\{#AppName}-config.json');
    CopyFile(ExpandConstant('{localappdata}\{#AppName}\config.json'),
      LegacyConfigBackup, False);
  end;

  LegacyUninstaller := RemoveQuotes(LegacyUninstaller);
  if not ShellExec('runas', LegacyUninstaller,
    '/VERYSILENT /SUPPRESSMSGBOXES /NORESTART', '', SW_HIDE,
    ewWaitUntilTerminated, ResultCode) or (ResultCode <> 0) then
    Result := 'TinyNetUse 1.0.0 must be removed before this per-user version can be installed.';
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  ConfigDir: String;
begin
  if (CurStep <> ssPostInstall) or not FileExists(LegacyConfigBackup) then
    Exit;

  ConfigDir := ExpandConstant('{localappdata}\{#AppName}');
  ForceDirectories(ConfigDir);
  if not FileExists(AddBackslash(ConfigDir) + 'config.json') then
    CopyFile(LegacyConfigBackup,
      AddBackslash(ConfigDir) + 'config.json', False);
end;

function InitializeUninstall(): Boolean;
var
  Choice: Integer;
begin
  Result := True;
  { Silent package-manager uninstalls keep settings by default. }
  RemoveUserData := False;
  if (not UninstallSilent) and
    DirExists(ExpandConstant('{localappdata}\{#AppName}')) then
  begin
    Choice := SuppressibleMsgBox(
      'Keep your TinyNetUse settings?' + #13#10 + #13#10 +
      'Choose Yes to keep them for a future installation.' + #13#10 +
      'Choose No to remove saved preferences and window positions.' + #13#10 +
      'Choose Cancel to abort the uninstall.',
      mbConfirmation, MB_YESNOCANCEL, IDYES);

    case Choice of
      IDNO: RemoveUserData := True;
      IDCANCEL: Result := False;
    end;
  end;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if (CurUninstallStep = usPostUninstall) and RemoveUserData then
    DelTree(ExpandConstant('{localappdata}\{#AppName}'), True, True, True);
end;
