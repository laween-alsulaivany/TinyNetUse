from pathlib import Path
from unittest.mock import Mock

import pytest

import tinynetuse.startup as startup_module


ROOT = Path(__file__).parents[1]


def set_startup_folder(tmp_path, monkeypatch):
    folder = tmp_path / "Startup"
    monkeypatch.setattr(startup_module, "STARTUP_FOLDER", folder)
    return folder


def test_no_shortcut_is_disabled(tmp_path, monkeypatch):
    set_startup_folder(tmp_path, monkeypatch)
    read_shortcut = Mock()
    monkeypatch.setattr(startup_module, "_read_shortcut", read_shortcut)

    assert not startup_module.is_startup_enabled()
    read_shortcut.assert_not_called()


def test_valid_shortcut_is_enabled(tmp_path, monkeypatch):
    folder = set_startup_folder(tmp_path, monkeypatch)
    folder.mkdir()
    link = folder / startup_module.SHORTCUT_NAME
    link.touch()
    target = tmp_path / "TinyNetUse.exe"
    target.touch()
    monkeypatch.setattr(
        startup_module, "_read_shortcut", lambda path: (str(target), "")
    )

    assert startup_module.is_startup_enabled()


@pytest.mark.parametrize(
    ("target_name", "create_target"),
    [
        ("TinyNetUse.exe", False),
        ("NotTinyNetUse.exe", True),
    ],
)
def test_stale_or_unrelated_shortcut_is_disabled(
    tmp_path, monkeypatch, target_name, create_target
):
    folder = set_startup_folder(tmp_path, monkeypatch)
    folder.mkdir()
    (folder / startup_module.SHORTCUT_NAME).touch()
    target = tmp_path / target_name
    if create_target:
        target.touch()
    monkeypatch.setattr(
        startup_module, "_read_shortcut", lambda path: (str(target), "")
    )

    assert not startup_module.is_startup_enabled()


def test_enable_startup_creates_a_valid_frozen_shortcut(tmp_path, monkeypatch):
    folder = set_startup_folder(tmp_path, monkeypatch)
    executable = tmp_path / "App" / "TinyNetUse.exe"
    executable.parent.mkdir()
    executable.touch()
    monkeypatch.setattr(startup_module.sys, "frozen", True, raising=False)
    monkeypatch.setattr(startup_module.sys, "executable", str(executable))
    saved = {}

    def write_shortcut(path, target, arguments, work_dir, icon):
        path.touch()
        saved.update(
            target=target,
            arguments=arguments,
            work_dir=work_dir,
            icon=icon,
        )

    monkeypatch.setattr(startup_module, "_write_shortcut", write_shortcut)
    monkeypatch.setattr(
        startup_module,
        "_read_shortcut",
        lambda path: (str(saved["target"]), saved["arguments"]),
    )

    link = startup_module.enable_startup()

    assert link == folder / startup_module.SHORTCUT_NAME
    assert saved["target"] == executable.resolve()
    assert saved["arguments"] == ""
    assert saved["work_dir"] == executable.parent.resolve()
    assert saved["icon"] == executable.resolve()
    assert startup_module.is_startup_enabled()


def test_repeated_enable_is_safe(tmp_path, monkeypatch):
    folder = set_startup_folder(tmp_path, monkeypatch)
    executable = tmp_path / "TinyNetUse.exe"
    executable.touch()
    monkeypatch.setattr(startup_module.sys, "frozen", True, raising=False)
    monkeypatch.setattr(startup_module.sys, "executable", str(executable))
    write_shortcut = Mock(
        side_effect=lambda path, *args: path.touch()
    )
    monkeypatch.setattr(startup_module, "_write_shortcut", write_shortcut)
    monkeypatch.setattr(
        startup_module, "_read_shortcut", lambda path: (str(executable), "")
    )

    startup_module.enable_startup()
    startup_module.enable_startup()

    assert (folder / startup_module.SHORTCUT_NAME).exists()
    assert write_shortcut.call_count == 2


def test_disable_and_repeated_disable_are_safe(tmp_path, monkeypatch):
    folder = set_startup_folder(tmp_path, monkeypatch)
    folder.mkdir()
    link = folder / startup_module.SHORTCUT_NAME
    link.touch()

    startup_module.disable_startup()
    startup_module.disable_startup()

    assert not link.exists()


def test_installer_shortcut_uses_the_same_entry_and_is_valid(
    tmp_path, monkeypatch
):
    folder = set_startup_folder(tmp_path, monkeypatch)
    folder.mkdir()
    (folder / startup_module.SHORTCUT_NAME).touch()
    installed_exe = tmp_path / "Programs" / "TinyNetUse" / "TinyNetUse.exe"
    installed_exe.parent.mkdir(parents=True)
    installed_exe.touch()
    monkeypatch.setattr(
        startup_module,
        "_read_shortcut",
        lambda path: (str(installed_exe), ""),
    )
    installer = (ROOT / "packaging" / "installer.iss").read_text(
        encoding="utf-8"
    )

    assert 'Name: "{userstartup}\\{#AppName}"' in installer
    assert startup_module.startup_shortcut_path().name == "TinyNetUse.lnk"
    assert startup_module.is_startup_enabled()


def test_frozen_command_never_uses_pyinstaller_temp_path(tmp_path, monkeypatch):
    executable = tmp_path / "Installed" / "TinyNetUse.exe"
    executable.parent.mkdir()
    executable.touch()
    monkeypatch.setattr(startup_module.sys, "frozen", True, raising=False)
    monkeypatch.setattr(startup_module.sys, "executable", str(executable))
    monkeypatch.setattr(
        startup_module.sys,
        "_MEIPASS",
        str(tmp_path / "PyInstallerTemp"),
        raising=False,
    )

    target, arguments, work_dir, icon = startup_module._startup_command()

    assert target == executable.resolve()
    assert arguments == ""
    assert work_dir == executable.parent.resolve()
    assert icon == executable.resolve()


def test_portable_command_targets_the_persistent_executable(
    tmp_path, monkeypatch
):
    executable = tmp_path / "Portable" / "TinyNetUse.exe"
    executable.parent.mkdir()
    executable.touch()
    (executable.parent / "portable.flag").touch()
    monkeypatch.setattr(startup_module.sys, "frozen", True, raising=False)
    monkeypatch.setattr(startup_module.sys, "executable", str(executable))
    monkeypatch.setattr(
        startup_module.sys,
        "_MEIPASS",
        str(tmp_path / "TemporaryExtraction"),
        raising=False,
    )

    target, arguments, work_dir, _ = startup_module._startup_command()

    assert target == executable.resolve()
    assert arguments == ""
    assert work_dir == executable.parent.resolve()


def test_source_command_targets_python_and_main(tmp_path, monkeypatch):
    python = tmp_path / "python.exe"
    python.touch()
    monkeypatch.delattr(startup_module.sys, "frozen", raising=False)
    monkeypatch.setattr(startup_module.sys, "executable", str(python))

    target, arguments, work_dir, _ = startup_module._startup_command()

    main_script = Path(startup_module.__file__).parents[2] / "main.py"
    assert target == python.resolve()
    assert arguments == f'"{main_script}"'
    assert work_dir == main_script.parent


def test_com_is_initialized_and_uninitialized_when_reading(
    tmp_path, monkeypatch
):
    shortcut = Mock(TargetPath="C:\\TinyNetUse.exe", Arguments="")
    shell = Mock()
    shell.CreateShortcut.return_value = shortcut
    co_initialize = Mock()
    co_uninitialize = Mock()
    monkeypatch.setattr(startup_module.pythoncom, "CoInitialize", co_initialize)
    monkeypatch.setattr(
        startup_module.pythoncom, "CoUninitialize", co_uninitialize
    )
    monkeypatch.setattr(
        startup_module.win32com.client, "Dispatch", Mock(return_value=shell)
    )

    result = startup_module._read_shortcut(tmp_path / "TinyNetUse.lnk")

    assert result == ("C:\\TinyNetUse.exe", "")
    co_initialize.assert_called_once()
    co_uninitialize.assert_called_once()


def test_com_is_uninitialized_when_shortcut_creation_fails(
    tmp_path, monkeypatch
):
    co_initialize = Mock()
    co_uninitialize = Mock()
    monkeypatch.setattr(startup_module.pythoncom, "CoInitialize", co_initialize)
    monkeypatch.setattr(
        startup_module.pythoncom, "CoUninitialize", co_uninitialize
    )
    monkeypatch.setattr(
        startup_module.win32com.client,
        "Dispatch",
        Mock(side_effect=OSError("COM failed")),
    )

    with pytest.raises(OSError, match="COM failed"):
        startup_module._write_shortcut(
            tmp_path / "TinyNetUse.lnk",
            tmp_path / "TinyNetUse.exe",
            "",
            tmp_path,
            tmp_path / "TinyNetUse.exe",
        )

    co_initialize.assert_called_once()
    co_uninitialize.assert_called_once()


def test_enable_failure_is_reported(tmp_path, monkeypatch):
    set_startup_folder(tmp_path, monkeypatch)
    monkeypatch.setattr(
        startup_module,
        "_write_shortcut",
        Mock(side_effect=OSError("shortcut failed")),
    )

    with pytest.raises(OSError, match="shortcut failed"):
        startup_module.enable_startup()
