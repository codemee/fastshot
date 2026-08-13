from PySide6.QtCore import QSettings

from fshot.theme import ThemeManager, ThemeMode


def test_theme_defaults_to_system(qt_app, tmp_path):
    settings = QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)
    manager = ThemeManager(qt_app, settings)

    assert manager.mode == ThemeMode.SYSTEM
    assert manager.effective_mode in {ThemeMode.LIGHT, ThemeMode.DARK}


def test_theme_selection_is_persisted(qt_app, tmp_path):
    settings = QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)
    manager = ThemeManager(qt_app, settings)

    manager.set_mode(ThemeMode.DARK)
    settings.sync()

    restored = ThemeManager(
        qt_app,
        QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat),
    )
    assert restored.mode == ThemeMode.DARK
    assert restored.effective_mode == ThemeMode.DARK


def test_invalid_stored_theme_falls_back_to_system(qt_app, tmp_path):
    settings = QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)
    settings.setValue("appearance/theme", "unknown")

    manager = ThemeManager(qt_app, settings)

    assert manager.mode == ThemeMode.SYSTEM


def test_explicit_theme_cycles_in_expected_order(qt_app, tmp_path):
    from fshot.main_window import EditorWindow

    settings = QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)
    manager = ThemeManager(qt_app, settings)
    window = EditorWindow(manager)

    window._cycle_theme()
    assert manager.mode == ThemeMode.LIGHT
    window._cycle_theme()
    assert manager.mode == ThemeMode.DARK
    window._cycle_theme()
    assert manager.mode == ThemeMode.SYSTEM


def test_arrow_spinbox_buttons_change_value(qt_app):
    from fshot.main_window import ArrowSpinBox

    spinbox = ArrowSpinBox()
    spinbox.setRange(0, 10)
    spinbox.setValue(5)

    spinbox.up_button.click()
    assert spinbox.value() == 6
    spinbox.down_button.click()
    assert spinbox.value() == 5
