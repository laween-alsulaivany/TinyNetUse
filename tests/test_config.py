import json
import os
from pathlib import Path

import pytest

import tinynetuse.config as config_module
from tinynetuse.config import (
    CONFIG_VERSION,
    DEFAULTS,
    Config,
    default_config,
    resolve_config_path,
)


def write_config(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def test_defaults_are_written_for_a_new_config(tmp_path):
    path = tmp_path / "config.json"
    config = Config(path)

    assert config.data == DEFAULTS
    assert json.loads(path.read_text(encoding="utf-8")) == DEFAULTS


def test_nested_defaults_are_independent(tmp_path):
    first = Config(tmp_path / "first.json")
    second = Config(tmp_path / "second.json")

    first.data["notify_threshold"]["download"] = 25
    first.data["notify_threshold"]["upload"] = 10

    assert second.data["notify_threshold"]["download"] is None
    assert second.data["notify_threshold"]["upload"] is None
    assert DEFAULTS["notify_threshold"]["download"] is None
    assert DEFAULTS["notify_threshold"]["upload"] is None
    assert default_config()["notify_threshold"] is not DEFAULTS["notify_threshold"]


def test_normal_save_and_load(tmp_path):
    path = tmp_path / "config.json"
    saved = Config(path)
    saved.data["unit"] = "Mib/s"
    saved.data["precision"] = 2
    saved.data["network_adapter"] = "My VPN"
    saved.data["notify_threshold"]["download"] = 10
    saved.data["notify_threshold"]["upload"] = 5
    saved.save()

    loaded = Config(path)

    assert loaded.data["unit"] == "Mib/s"
    assert loaded.data["precision"] == 2
    assert loaded.data["network_adapter"] == "My VPN"
    assert loaded.data["reduce_opacity_on_hover"] is False
    assert loaded.data["notify_threshold"]["download"] == 10
    assert loaded.data["notify_threshold"]["upload"] == 5


def test_malformed_json_is_preserved_and_replaced(tmp_path):
    path = tmp_path / "config.json"
    path.write_text('{"unit":', encoding="utf-8")

    config = Config(path)

    assert config.data == DEFAULTS
    assert json.loads(path.read_text(encoding="utf-8")) == DEFAULTS
    backups = list(tmp_path.glob("config.json.corrupt-*"))
    assert len(backups) == 1
    assert backups[0].read_text(encoding="utf-8") == '{"unit":'


def test_missing_keys_use_defaults_and_keep_valid_values(tmp_path):
    path = tmp_path / "config.json"
    write_config(path, {"unit": "KB/s"})

    config = Config(path)

    assert config.data["unit"] == "KB/s"
    assert config.data["font"] == DEFAULTS["font"]
    assert config.data["notify_threshold"] == DEFAULTS["notify_threshold"]
    assert config.data["config_version"] == CONFIG_VERSION


def test_migration_removes_the_redundant_startup_boolean(tmp_path):
    path = tmp_path / "config.json"
    write_config(
        path,
        {
            "config_version": 1,
            "unit": "Kib/s",
            "start_on_boot": True,
        },
    )

    config = Config(path)

    assert config.data["config_version"] == CONFIG_VERSION
    assert config.data["unit"] == "Kib/s"
    assert "start_on_boot" not in config.data
    assert "start_on_boot" not in json.loads(path.read_text(encoding="utf-8"))


def test_migration_adds_the_upload_threshold(tmp_path):
    path = tmp_path / "config.json"
    write_config(
        path,
        {
            "config_version": 3,
            "notify_threshold": {"download": 10},
        },
    )

    config = Config(path)

    assert config.data["notify_threshold"] == {
        "download": 10,
        "upload": None,
    }


def test_hover_opacity_preference_is_saved_and_loaded(tmp_path):
    path = tmp_path / "config.json"
    config = Config(path)
    config.data["reduce_opacity_on_hover"] = True
    config.save()

    loaded = Config(path)

    assert loaded.data["reduce_opacity_on_hover"] is True


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("font", ""),
        ("font_size", 5),
        ("font_size", 73),
        ("font_color", "red"),
        ("alert_color", "#12345G"),
        ("widget_locked", 1),
        ("widget_geometry", [1, 2, -3, 4]),
        ("graph_geometry", [1, 2, 3]),
        ("graph_history", 1),
        ("update_interval", 0),
        ("update_interval", 61),
        ("opacity", -0.1),
        ("opacity", 0),
        ("opacity", 0.19),
        ("opacity", 1.1),
        ("unit", "GB/s"),
        ("precision", 3),
        ("network_adapter", ""),
        ("network_adapter", 123),
        ("network_adapter", "x" * 257),
    ],
)
def test_invalid_values_fall_back_to_that_fields_default(tmp_path, key, value):
    path = tmp_path / "config.json"
    data = default_config()
    data[key] = value
    write_config(path, data)

    config = Config(path)

    assert config.data[key] == DEFAULTS[key]


@pytest.mark.parametrize(
    "threshold",
    [
        "fast",
        -1,
        0,
        1001,
        {"download": "fast"},
        {"download": float("inf")},
    ],
)
def test_invalid_thresholds_are_disabled(tmp_path, threshold):
    path = tmp_path / "config.json"
    data = default_config()
    data["notify_threshold"] = threshold
    write_config(path, data)

    config = Config(path)

    assert config.data["notify_threshold"] == {
        "download": None,
        "upload": None,
    }


def test_threshold_directions_are_validated_independently(tmp_path):
    path = tmp_path / "config.json"
    data = default_config()
    data["notify_threshold"] = {"download": "fast", "upload": 5}
    write_config(path, data)

    config = Config(path)

    assert config.data["notify_threshold"] == {
        "download": None,
        "upload": 5,
    }


def test_save_uses_an_atomic_replace(tmp_path, monkeypatch):
    path = tmp_path / "config.json"
    config = Config(path)
    real_replace = os.replace
    replacements = []

    def record_replace(source, destination):
        replacements.append((Path(source), Path(destination)))
        real_replace(source, destination)

    monkeypatch.setattr(config_module.os, "replace", record_replace)
    config.data["precision"] = 2
    config.save()

    assert len(replacements) == 1
    temp_path, destination = replacements[0]
    assert temp_path.parent == path.parent
    assert destination == path
    assert not temp_path.exists()
    assert json.loads(path.read_text(encoding="utf-8"))["precision"] == 2


def test_old_exe_side_config_migrates_to_local_app_data(tmp_path, monkeypatch):
    executable = tmp_path / "Programs" / "TinyNetUse" / "TinyNetUse.exe"
    executable.parent.mkdir(parents=True)
    executable.touch()
    legacy_path = executable.parent / "config.json"
    write_config(legacy_path, {"unit": "Kib/s", "precision": 2})
    local_app_data = tmp_path / "LocalAppData"

    monkeypatch.setattr(config_module.sys, "frozen", True, raising=False)
    monkeypatch.setattr(config_module.sys, "executable", str(executable))
    monkeypatch.setenv("LOCALAPPDATA", str(local_app_data))

    config = Config()
    expected_path = local_app_data / "TinyNetUse" / "config.json"

    assert config.path == expected_path
    assert config.data["unit"] == "Kib/s"
    assert config.data["precision"] == 2
    assert expected_path.exists()
    assert not legacy_path.exists()


def test_portable_marker_keeps_config_beside_executable(tmp_path, monkeypatch):
    executable = tmp_path / "Portable" / "TinyNetUse.exe"
    executable.parent.mkdir(parents=True)
    executable.touch()
    (executable.parent / "portable.flag").touch()
    portable_config = executable.parent / "config.json"
    write_config(portable_config, {"unit": "MB/s"})

    monkeypatch.setattr(config_module.sys, "frozen", True, raising=False)
    monkeypatch.setattr(config_module.sys, "executable", str(executable))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "LocalAppData"))

    config = Config()

    assert config.path == portable_config
    assert config.data["unit"] == "MB/s"
    assert not (tmp_path / "LocalAppData" / "TinyNetUse").exists()


def test_installed_mode_uses_local_app_data(tmp_path):
    path = resolve_config_path(
        frozen=True,
        executable=tmp_path / "Programs" / "TinyNetUse" / "TinyNetUse.exe",
        local_app_data=tmp_path / "LocalAppData",
    )

    assert path == tmp_path / "LocalAppData" / "TinyNetUse" / "config.json"


def test_source_mode_uses_separate_developer_config(tmp_path):
    path = resolve_config_path(
        frozen=False,
        executable=tmp_path / "Python" / "python.exe",
        local_app_data=tmp_path / "LocalAppData",
    )

    assert path == tmp_path / "LocalAppData" / "TinyNetUse" / "dev" / "config.json"
