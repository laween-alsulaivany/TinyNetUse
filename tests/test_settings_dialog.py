from copy import deepcopy
import json
from unittest.mock import Mock

from PySide6 import QtGui, QtWidgets
from PySide6.QtCore import Qt

from tinynetuse.config import Config, default_config
import tinynetuse.settings_dialog as settings_module


def make_dialog(
    tmp_path,
    qtbot,
    monkeypatch,
    startup_enabled=False,
    initial_values=None,
    adapters=None,
):
    config = Config(tmp_path / "config.json")
    if initial_values:
        config.data.update(deepcopy(initial_values))
        config.save()

    parent = QtWidgets.QWidget()
    parent.config = config
    parent.apply_settings = Mock()
    parent.sampler = Mock()
    parent.sampler.available_adapters.return_value = adapters or [
        "Ethernet",
        "VPN",
    ]

    monkeypatch.setattr(
        settings_module, "is_startup_enabled", lambda: startup_enabled
    )
    monkeypatch.setattr(
        settings_module, "startup_shortcut_exists", lambda: startup_enabled
    )
    monkeypatch.setattr(settings_module, "enable_startup", Mock())
    monkeypatch.setattr(settings_module, "disable_startup", Mock())

    dialog = settings_module.SettingsDialog(parent)
    qtbot.addWidget(parent)
    qtbot.addWidget(dialog)
    return dialog, parent, config


def pick_color(dialog, monkeypatch, key, button, color="#123456"):
    monkeypatch.setattr(
        QtWidgets.QColorDialog,
        "getColor",
        lambda *args: QtGui.QColor(color),
    )
    dialog._pick(key, button)


def test_change_color_then_cancel_discards_everything(
    tmp_path, qtbot, monkeypatch
):
    dialog, _, config = make_dialog(tmp_path, qtbot, monkeypatch)
    original_data = deepcopy(config.data)
    original_file = config.path.read_text(encoding="utf-8")

    pick_color(dialog, monkeypatch, "font_color", dialog.btn_font)

    assert dialog.working["font_color"] == "#123456"
    assert config.data == original_data
    dialog.reject()

    assert config.data == original_data
    assert config.path.read_text(encoding="utf-8") == original_file
    settings_module.enable_startup.assert_not_called()
    settings_module.disable_startup.assert_not_called()


def test_change_startup_then_cancel_has_no_side_effect(
    tmp_path, qtbot, monkeypatch
):
    dialog, _, config = make_dialog(tmp_path, qtbot, monkeypatch)
    original_data = deepcopy(config.data)

    dialog.boot_chk.setChecked(True)
    dialog.reject()

    assert config.data == original_data
    settings_module.enable_startup.assert_not_called()
    settings_module.disable_startup.assert_not_called()


def test_reset_then_cancel_keeps_current_settings(tmp_path, qtbot, monkeypatch):
    current = {
        "unit": "Mib/s",
        "opacity": 0.4,
        "font_color": "#123456",
        "widget_geometry": [10, 20, 300, 100],
    }
    dialog, _, config = make_dialog(
        tmp_path,
        qtbot,
        monkeypatch,
        initial_values=current,
    )
    original_data = deepcopy(config.data)

    qtbot.mouseClick(dialog.reset_button, Qt.MouseButton.LeftButton)

    assert dialog.working["unit"] == default_config()["unit"]
    assert dialog.working["opacity"] == default_config()["opacity"]
    assert config.data == original_data
    dialog.reject()

    assert config.data == original_data
    settings_module.enable_startup.assert_not_called()
    settings_module.disable_startup.assert_not_called()


def test_reset_then_ok_commits_defaults_but_keeps_geometry(
    tmp_path, qtbot, monkeypatch
):
    geometry = [10, 20, 300, 100]
    dialog, parent, config = make_dialog(
        tmp_path,
        qtbot,
        monkeypatch,
        startup_enabled=True,
        initial_values={
            "unit": "Mib/s",
            "opacity": 0.4,
            "font_color": "#123456",
            "widget_geometry": geometry,
        },
    )
    real_save = config.save
    config.save = Mock(wraps=real_save)

    qtbot.mouseClick(dialog.reset_button, Qt.MouseButton.LeftButton)
    dialog.accept()

    defaults = default_config()
    assert config.data["unit"] == defaults["unit"]
    assert config.data["opacity"] == defaults["opacity"]
    assert config.data["font_color"] == defaults["font_color"]
    assert "start_on_boot" not in config.data
    assert config.data["widget_geometry"] == geometry
    config.save.assert_called_once()
    settings_module.disable_startup.assert_called_once()
    settings_module.enable_startup.assert_not_called()
    parent.apply_settings.assert_called_once()


def test_normal_ok_validates_saves_once_and_applies(
    tmp_path, qtbot, monkeypatch
):
    dialog, parent, config = make_dialog(tmp_path, qtbot, monkeypatch)
    real_save = config.save
    events = []

    def save():
        real_save()
        events.append("save")

    config.save = Mock(side_effect=save)
    parent.apply_settings.side_effect = lambda: events.append("apply")
    settings_module.enable_startup.side_effect = lambda: events.append("startup")

    dialog.interval.setValue(2.5)
    dialog.adapter_combo.setCurrentIndex(dialog.adapter_combo.findData("VPN"))
    dialog.unit_combo.setCurrentText("Mib/s")
    dialog.prec_spin.setValue(2)
    dialog.download_threshold_spin.setValue(8)
    dialog.upload_threshold_spin.setValue(16)
    dialog.opacity_spin.setValue(60)
    dialog.font_size_spin.setValue(14)
    dialog.bold_check.setChecked(True)
    dialog.boot_chk.setChecked(True)
    pick_color(dialog, monkeypatch, "font_color", dialog.btn_font)
    dialog.accept()

    saved = json.loads(config.path.read_text(encoding="utf-8"))
    assert saved["update_interval"] == 2.5
    assert saved["network_adapter"] == "VPN"
    assert saved["unit"] == "Mib/s"
    assert saved["precision"] == 2
    assert saved["notify_threshold"] == {"download": 1, "upload": 2}
    assert saved["opacity"] == 0.6
    assert saved["font_size"] == 14
    assert saved["font_bold"] is True
    assert saved["font_color"] == "#123456"
    assert "start_on_boot" not in saved
    config.save.assert_called_once()
    settings_module.enable_startup.assert_called_once()
    settings_module.disable_startup.assert_not_called()
    parent.apply_settings.assert_called_once()
    assert events == ["save", "apply", "startup"]


def test_close_button_discards_changes(tmp_path, qtbot, monkeypatch):
    dialog, _, config = make_dialog(tmp_path, qtbot, monkeypatch)
    original_data = deepcopy(config.data)
    original_file = config.path.read_text(encoding="utf-8")

    dialog.unit_combo.setCurrentText("MB/s")
    dialog.boot_chk.setChecked(True)
    pick_color(dialog, monkeypatch, "alert_color", dialog.btn_alert)
    dialog.close()

    assert config.data == original_data
    assert config.path.read_text(encoding="utf-8") == original_file
    settings_module.enable_startup.assert_not_called()
    settings_module.disable_startup.assert_not_called()


def test_startup_checkbox_uses_actual_shortcut_state(
    tmp_path, qtbot, monkeypatch
):
    dialog, _, config = make_dialog(
        tmp_path, qtbot, monkeypatch, startup_enabled=True
    )

    assert "start_on_boot" not in config.data
    assert dialog._working_startup is True
    assert dialog.boot_chk.isChecked()


def test_startup_failure_keeps_other_settings_and_checkbox_truthful(
    tmp_path, qtbot, monkeypatch
):
    dialog, parent, config = make_dialog(tmp_path, qtbot, monkeypatch)
    settings_module.enable_startup.side_effect = OSError("access denied")
    warning = Mock()
    monkeypatch.setattr(QtWidgets.QMessageBox, "warning", warning)

    dialog.boot_chk.setChecked(True)
    dialog.interval.setValue(2.5)
    dialog.accept()

    assert config.data["update_interval"] == 2.5
    assert json.loads(config.path.read_text(encoding="utf-8"))[
        "update_interval"
    ] == 2.5
    assert not dialog.boot_chk.isChecked()
    warning.assert_called_once()
    parent.apply_settings.assert_called_once()


def test_save_failure_does_not_apply_settings_or_startup(
    tmp_path, qtbot, monkeypatch
):
    dialog, parent, config = make_dialog(tmp_path, qtbot, monkeypatch)
    original_data = deepcopy(config.data)
    original_file = config.path.read_text(encoding="utf-8")
    config.save = Mock(side_effect=OSError("disk full"))
    warning = Mock()
    monkeypatch.setattr(QtWidgets.QMessageBox, "warning", warning)

    dialog.interval.setValue(2.5)
    dialog.boot_chk.setChecked(True)
    dialog.accept()

    assert config.data == original_data
    assert config.path.read_text(encoding="utf-8") == original_file
    parent.apply_settings.assert_not_called()
    settings_module.enable_startup.assert_not_called()
    settings_module.disable_startup.assert_not_called()
    warning.assert_called_once()


def test_both_thresholds_keep_the_same_rate_when_units_change(
    tmp_path, qtbot, monkeypatch
):
    dialog, _, _ = make_dialog(
        tmp_path,
        qtbot,
        monkeypatch,
        initial_values={
            "notify_threshold": {"download": 1, "upload": 2},
        },
    )

    dialog.unit_combo.setCurrentText("Mib/s")

    assert dialog.download_threshold_spin.value() == 8
    assert dialog.upload_threshold_spin.value() == 16
    assert dialog.download_threshold_spin.suffix() == " Mib/s"
    assert dialog.upload_threshold_spin.suffix() == " Mib/s"


def test_opacity_control_enforces_safe_range(tmp_path, qtbot, monkeypatch):
    dialog, _, _ = make_dialog(tmp_path, qtbot, monkeypatch)

    dialog.opacity_spin.setValue(0)
    assert dialog.opacity_spin.value() == 20

    dialog.opacity_spin.setValue(150)
    assert dialog.opacity_spin.value() == 100


def test_hover_opacity_setting_and_help_are_accessible(
    tmp_path, qtbot, monkeypatch
):
    dialog, _, config = make_dialog(tmp_path, qtbot, monkeypatch)

    dialog.hover_opacity_check.setChecked(True)
    dialog.accept()

    assert config.data["reduce_opacity_on_hover"] is True
    assert isinstance(dialog.hover_opacity_help_button, QtWidgets.QToolButton)
    assert dialog.hover_opacity_help_button.accessibleName() == "Hover Opacity Help"
    assert "25% opacity" in dialog.hover_opacity_help_button.toolTip()


def test_enabling_second_overlay_option_disables_the_first_with_notice(
    tmp_path, qtbot, monkeypatch
):
    dialog, _, config = make_dialog(tmp_path, qtbot, monkeypatch)
    information = Mock()
    monkeypatch.setattr(QtWidgets.QMessageBox, "information", information)

    dialog.click_through_check.setChecked(True)

    assert information.call_count == 0
    assert dialog.click_through_check.isChecked()

    dialog.hover_opacity_check.setChecked(True)

    assert information.call_count == 1
    assert dialog.hover_opacity_check.isChecked()
    assert not dialog.click_through_check.isChecked()
    assert "Both options cannot be enabled" in information.call_args.args[2]

    dialog.accept()

    assert config.data["reduce_opacity_on_hover"] is True
    assert config.data["click_through_overlay"] is False
    assert isinstance(dialog.click_through_help_button, QtWidgets.QToolButton)
    assert dialog.click_through_help_button.accessibleName() == "Click Through Help"


def test_adapter_list_is_refreshed_and_uses_stable_names(
    tmp_path, qtbot, monkeypatch
):
    dialog, parent, _ = make_dialog(
        tmp_path,
        qtbot,
        monkeypatch,
        adapters=["Ethernet", "My VPN"],
    )

    assert [
        dialog.adapter_combo.itemText(index)
        for index in range(dialog.adapter_combo.count())
    ] == ["Auto (Recommended)", "Ethernet", "My VPN"]
    assert dialog.adapter_combo.itemData(2) == "My VPN"
    parent.sampler.available_adapters.assert_called_once()


def test_adapter_help_uses_a_compact_accessible_info_button(
    tmp_path, qtbot, monkeypatch
):
    dialog, _, _ = make_dialog(tmp_path, qtbot, monkeypatch)

    help_button = dialog.adapter_help_button

    assert isinstance(help_button, QtWidgets.QToolButton)
    assert help_button.autoRaise()
    assert help_button.accessibleName() == "Network Adapter Help"
    assert help_button.accessibleDescription() == (
        "Explains how to select a network adapter."
    )
    assert "width: 320px" in help_button.toolTip()
    assert dialog.adapter_combo.toolTip() == ""


def test_adapter_change_then_cancel_does_not_change_config(
    tmp_path, qtbot, monkeypatch
):
    dialog, _, config = make_dialog(tmp_path, qtbot, monkeypatch)

    dialog.adapter_combo.setCurrentIndex(
        dialog.adapter_combo.findData("Ethernet")
    )
    dialog.reject()

    assert config.data["network_adapter"] == "auto"


def test_missing_saved_adapter_falls_back_to_auto(
    tmp_path, qtbot, monkeypatch
):
    dialog, _, config = make_dialog(
        tmp_path,
        qtbot,
        monkeypatch,
        initial_values={"network_adapter": "Old VPN"},
        adapters=["Ethernet"],
    )

    assert dialog.adapter_combo.currentData() == "auto"
    assert dialog.working["network_adapter"] == "auto"
    assert config.data["network_adapter"] == "Old VPN"
