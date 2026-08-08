from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QCheckBox, QComboBox, QLabel, QPushButton

from fastshot.hotkeys import (
    HotkeyAction,
    HotkeyCombination,
    HotkeyStore,
    default_hotkeys,
    validate_hotkeys,
)
from fastshot.app import HotkeyBridge, WindowsHotkeyFilter
from fastshot.main_window import EditorWindow
from fastshot.settings import CaptureMode


def test_shift_cannot_be_used_by_itself():
    combination = HotkeyCombination("A", shift=True)

    assert not combination.is_valid()


def test_duplicate_hotkeys_are_rejected():
    bindings = default_hotkeys()
    bindings[CaptureMode.REGION] = bindings[CaptureMode.ACTIVE_WINDOW]

    assert validate_hotkeys(bindings) == "duplicate"


def test_repeat_hotkey_defaults_to_ctrl_shift_q_and_can_be_customized():
    bindings = default_hotkeys()
    assert bindings[HotkeyAction.REPEAT].display() == "Ctrl+Shift+Q"

    bindings[HotkeyAction.REPEAT] = HotkeyCombination("Y", ctrl=True, shift=True)
    assert validate_hotkeys(bindings) is None


def test_windows_filter_registers_configured_repeat_hotkey():
    native_filter = WindowsHotkeyFilter(None, HotkeyBridge(), default_hotkeys())

    assert (HotkeyCombination("Q", ctrl=True, shift=True), HotkeyAction.REPEAT) in (
        native_filter.bindings.values()
    )


def test_hotkey_panel_includes_customizable_repeat_action(qt_app):
    window = EditorWindow()
    window.configure_hotkeys(
        default_hotkeys(),
        lambda _bindings: (True, ""),
        lambda _bindings: (True, ""),
    )
    menu = window._create_hotkey_menu()

    assert menu.findChild(QComboBox, "repeatLetter").currentText() == "Q"
    assert menu.findChild(QCheckBox, "repeatCtrl").isChecked()
    assert menu.findChild(QCheckBox, "repeatShift").isChecked()
    assert not menu.findChild(QCheckBox, "repeatAlt").isChecked()


def test_hotkey_store_round_trip(tmp_path):
    settings = QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)
    store = HotkeyStore(settings)
    bindings = default_hotkeys()
    bindings[CaptureMode.FULLSCREEN] = HotkeyCombination("Z", ctrl=True)

    store.save(bindings)

    assert HotkeyStore(settings).load() == bindings


def test_hotkey_panel_uses_current_settings_and_disables_shift_alone(qt_app):
    window = EditorWindow()
    bindings = default_hotkeys()
    bindings[CaptureMode.ACTIVE_WINDOW] = HotkeyCombination("Z", ctrl=True, shift=True)
    applied = []
    window.configure_hotkeys(bindings, lambda _bindings: (True, ""), lambda value: (applied.append(value) is None, ""))
    menu = window._create_hotkey_menu()

    letter = menu.findChild(QComboBox, "active_windowLetter")
    ctrl = menu.findChild(QCheckBox, "active_windowCtrl")
    shift = menu.findChild(QCheckBox, "active_windowShift")
    alt = menu.findChild(QCheckBox, "active_windowAlt")
    assert letter.currentText() == "Z"
    assert ctrl.isChecked() and shift.isChecked() and not alt.isChecked()

    ctrl.setChecked(False)
    assert not shift.isChecked()
    assert not shift.isEnabled()


def test_conflict_warning_disables_ok(qt_app):
    window = EditorWindow()
    window.configure_hotkeys(
        default_hotkeys(),
        lambda _bindings: (False, "Already registered"),
        lambda _bindings: (True, ""),
    )
    menu = window._create_hotkey_menu()

    assert not menu.findChild(QPushButton, "hotkeyOkButton").isEnabled()
    assert menu.findChild(QLabel, "hotkeyWarning").text() == "Already registered"
    assert menu.findChild(QPushButton, "hotkeyCancelButton").isEnabled()


def test_use_defaults_only_resets_pending_panel_values(qt_app):
    window = EditorWindow()
    custom = default_hotkeys()
    custom[CaptureMode.ACTIVE_WINDOW] = HotkeyCombination("Z", ctrl=True)
    applied = []
    window.configure_hotkeys(
        custom,
        lambda _bindings: (True, ""),
        lambda bindings: (applied.append(bindings) is None, ""),
    )
    menu = window._create_hotkey_menu()

    menu.findChild(QPushButton, "hotkeyDefaultButton").click()

    assert menu.findChild(QComboBox, "active_windowLetter").currentText() == "A"
    assert menu.findChild(QCheckBox, "active_windowCtrl").isChecked()
    assert menu.findChild(QCheckBox, "active_windowShift").isChecked()
    assert not menu.findChild(QCheckBox, "active_windowAlt").isChecked()
    assert applied == []
    assert window.hotkey_bindings == custom
