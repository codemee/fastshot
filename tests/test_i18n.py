from PySide6.QtCore import QLocale, QSettings
from PySide6.QtGui import QKeySequence

from fastshot.i18n import LanguageManager, LanguageMode, _is_traditional_chinese


def test_language_defaults_to_system_and_uses_traditional_chinese(tmp_path):
    settings = QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)
    manager = LanguageManager(settings, QLocale("zh_TW"))

    assert manager.mode == LanguageMode.SYSTEM
    assert manager.effective_mode == LanguageMode.ZH_TW
    assert manager.text("save") == "儲存"


def test_non_traditional_system_locale_uses_english(tmp_path):
    settings = QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)
    manager = LanguageManager(settings, QLocale("ja_JP"))

    assert manager.effective_mode == LanguageMode.EN
    assert manager.text("save") == "Save"


def test_macos_traditional_chinese_language_tag_is_recognized():
    assert _is_traditional_chinese("zh-Hant-TW")
    assert _is_traditional_chinese("zh-TW")
    assert not _is_traditional_chinese("zh-Hans-CN")


def test_language_selection_is_persisted(tmp_path):
    path = tmp_path / "settings.ini"
    settings = QSettings(str(path), QSettings.Format.IniFormat)
    manager = LanguageManager(settings, QLocale("en_US"))

    manager.set_mode(LanguageMode.ZH_TW)
    settings.sync()

    restored = LanguageManager(
        QSettings(str(path), QSettings.Format.IniFormat),
        QLocale("en_US"),
    )
    assert restored.mode == LanguageMode.ZH_TW
    assert restored.effective_mode == LanguageMode.ZH_TW


def test_language_cycles_in_expected_order(qt_app, tmp_path):
    from fastshot.main_window import EditorWindow

    settings = QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)
    manager = LanguageManager(settings, QLocale("en_US"))
    window = EditorWindow(language_manager=manager)

    window._cycle_language()
    assert manager.mode == LanguageMode.ZH_TW
    window._cycle_language()
    assert manager.mode == LanguageMode.EN
    window._cycle_language()
    assert manager.mode == LanguageMode.SYSTEM


def test_language_change_retranslates_toolbar(qt_app, tmp_path):
    from fastshot.main_window import EditorWindow

    settings = QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)
    manager = LanguageManager(settings, QLocale("en_US"))
    window = EditorWindow(language_manager=manager)

    assert window.save_action.toolTip().startswith("Save (")
    manager.set_mode(LanguageMode.ZH_TW)

    assert window.save_action.toolTip().startswith("儲存 (")
    assert "繁體中文" in window.language_action.toolTip()


def test_toolbar_tooltips_include_shortcuts(qt_app, tmp_path):
    from fastshot.main_window import EditorWindow

    settings = QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)
    manager = LanguageManager(settings, QLocale("en_US"))
    window = EditorWindow(language_manager=manager)

    native_pen = QKeySequence("Alt+P").toString(QKeySequence.SequenceFormat.NativeText)
    native_save = QKeySequence.StandardKey.Save
    assert native_pen in window.pen_action.toolTip()
    native_save_text = QKeySequence(native_save).toString(QKeySequence.SequenceFormat.NativeText)
    native_zoom = window.zoom_in_action.shortcuts()[0].toString(
        QKeySequence.SequenceFormat.NativeText
    )
    assert native_save_text in window.save_action.toolTip()
    assert native_zoom in window.zoom_in_action.toolTip()
