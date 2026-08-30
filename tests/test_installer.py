from pathlib import Path


INSTALLER = (
    Path(__file__).parents[1] / "packaging" / "installer.iss"
).read_text(encoding="utf-8")


def test_installer_stays_per_user_with_a_stable_app_id():
    assert "AppId={{A3F1B2C4-9E87-4D56-BF12-7C3A05E91D28}" in INSTALLER
    assert "PrivilegesRequired=lowest" in INSTALLER
    assert "DefaultDirName={localappdata}\\Programs\\{#AppName}" in INSTALLER
    assert "{commondesktop}" not in INSTALLER
    assert "AppMutex=" not in INSTALLER


def test_uninstaller_offers_to_remove_settings_but_silent_mode_keeps_them():
    assert "function InitializeUninstall(): Boolean" in INSTALLER
    assert "not UninstallSilent" in INSTALLER
    assert "Keep your TinyNetUse settings?" in INSTALLER
    assert "MB_YESNOCANCEL" in INSTALLER
    assert "IDNO: RemoveUserData := True;" in INSTALLER
    assert "IDCANCEL: Result := False;" in INSTALLER
    assert "RemoveUserData := False" in INSTALLER
    assert "(CurUninstallStep = usPostUninstall) and RemoveUserData" in INSTALLER
    assert "DelTree(ExpandConstant('{localappdata}\\{#AppName}')" in INSTALLER


def test_installer_identifies_update_reinstall_and_downgrade_operations():
    assert "DisableWelcomePage=no" in INSTALLER
    assert "CurrentUninstallKey" in INSTALLER
    assert "RegQueryStringValue(HKCU64, CurrentUninstallKey" in INSTALLER
    assert "RegQueryStringValue(HKLM64, LegacyUninstallKey" in INSTALLER
    assert "'DisplayVersion', InstalledVersion" in INSTALLER
    assert "PackVersionComponents(Major, Minor, Revision, 0)" in INSTALLER
    assert "ComparePackedVersion(InstalledPackedVersion, CurrentPackedVersion)" in INSTALLER
    assert "This setup will update it to version {#AppVersion}." in INSTALLER
    assert "This setup will reinstall or repair it." in INSTALLER
    assert "This setup will downgrade it to version {#AppVersion}." in INSTALLER
    assert "WizardForm.WelcomeLabel2.Caption" in INSTALLER


def test_installer_version_messaging_does_not_prompt_in_silent_mode():
    wizard_code = INSTALLER.split("procedure InitializeWizard;", 1)[1].split(
        "function PrepareToInstall", 1
    )[0]

    assert "MsgBox" not in wizard_code
    assert "SuppressibleMsgBox" not in wizard_code
