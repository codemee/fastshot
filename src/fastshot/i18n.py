from __future__ import annotations

import re
import subprocess
import sys
from enum import Enum

from PySide6.QtCore import QLocale, QObject, QSettings, Signal


class LanguageMode(str, Enum):
    SYSTEM = "system"
    ZH_TW = "zh_TW"
    EN = "en"


TRANSLATIONS = {
    "en": {
        "open_tabs": "Open tabs",
        "tools": "Tools",
        "pen": "Pen",
        "line": "Line",
        "arrow": "Arrow",
        "rectangle": "Rectangle",
        "text": "Text",
        "mosaic": "Mosaic",
        "line_color": "Line and color",
        "undo": "Undo",
        "copy": "Copy",
        "paste": "Paste image",
        "save": "Save",
        "save_as": "Save As",
        "zoom_in": "Zoom in",
        "zoom_out": "Zoom out",
        "reset_zoom": "Reset zoom",
        "include_cursor": "Include cursor",
        "include_cursor_on": "Include cursor: on",
        "include_cursor_off": "Include cursor: off",
        "delay": "Delay",
        "delay_value": "Delay: {seconds:g}s",
        "capture_shortcuts": "Capture shortcuts",
        "capture_type": "Capture type",
        "ctrl": "Ctrl",
        "shift": "Shift",
        "alt": "Alt",
        "letter": "Letter",
        "use_defaults": "Use defaults",
        "capture_active_window": "Active window",
        "capture_region": "Region",
        "capture_fullscreen": "Full screen",
        "capture_window_under_cursor": "Window / control",
        "hotkey_incomplete": "All capture shortcuts must be configured.",
        "hotkey_invalid": "Shift must be combined with Ctrl or Alt.",
        "hotkey_duplicate": "Capture shortcuts cannot be duplicated.",
        "hotkey_conflict": "{shortcut} is already registered by another application.",
        "hotkey_registration_failed": "A shortcut could not be registered. Cancel and choose another combination.",
        "theme": "Theme: {mode} ({effective})",
        "theme_system": "follow system",
        "theme_light": "light",
        "theme_dark": "dark",
        "language": "Language: {mode} ({effective})",
        "language_system": "follow system",
        "language_zh_TW": "Traditional Chinese",
        "language_en": "English",
        "width": "Width",
        "custom": "Custom",
        "custom_color": "Custom...",
        "off": "Off",
        "line_color_dialog": "Line color",
        "save_screenshot": "Save Screenshot",
        "close_discard_all": "Close FastShot and discard unsaved screenshots?",
        "close_discard_tab": "Close {title} and discard changes?",
        "save_failed": "Could not save {path}",
        "exit": "Exit",
        "capture_failed": "Capture failed: {error}",
        "open_image_failed": "Could not open image: {path}",
        "tooltip_shortcut": "{label} ({shortcut})",
    },
    "zh_TW": {
        "open_tabs": "開啟的頁籤",
        "tools": "工具",
        "pen": "畫筆",
        "line": "線條",
        "arrow": "箭頭",
        "rectangle": "矩形",
        "text": "文字",
        "mosaic": "馬賽克",
        "line_color": "線條與顏色",
        "undo": "復原",
        "copy": "複製",
        "paste": "貼上影像",
        "save": "儲存",
        "save_as": "另存新檔",
        "zoom_in": "放大",
        "zoom_out": "縮小",
        "reset_zoom": "重設縮放",
        "include_cursor": "包含滑鼠游標",
        "include_cursor_on": "包含滑鼠游標：開啟",
        "include_cursor_off": "包含滑鼠游標：關閉",
        "delay": "延遲",
        "delay_value": "延遲：{seconds:g} 秒",
        "capture_shortcuts": "設定截圖快捷鍵",
        "capture_type": "截圖方式",
        "ctrl": "Ctrl",
        "shift": "Shift",
        "alt": "Alt",
        "letter": "字母",
        "use_defaults": "使用預設",
        "capture_active_window": "目前焦點視窗",
        "capture_region": "矩形區域",
        "capture_fullscreen": "全螢幕",
        "capture_window_under_cursor": "視窗／控制項",
        "hotkey_incomplete": "必須設定所有截圖快捷鍵。",
        "hotkey_invalid": "Shift 必須搭配 Ctrl 或 Alt 使用。",
        "hotkey_duplicate": "截圖快捷鍵不可重複。",
        "hotkey_conflict": "{shortcut} 已由其他軟體註冊使用。",
        "hotkey_registration_failed": "快捷鍵無法註冊，請取消並選擇其他組合。",
        "theme": "配色主題：{mode}（{effective}）",
        "theme_system": "跟隨系統",
        "theme_light": "淺色",
        "theme_dark": "深色",
        "language": "語言：{mode}（{effective}）",
        "language_system": "跟隨系統",
        "language_zh_TW": "繁體中文",
        "language_en": "英文",
        "width": "粗細",
        "custom": "自訂",
        "custom_color": "自訂顏色...",
        "off": "關閉",
        "line_color_dialog": "線條顏色",
        "save_screenshot": "儲存截圖",
        "close_discard_all": "關閉 FastShot 並捨棄尚未儲存的截圖？",
        "close_discard_tab": "關閉 {title} 並捨棄變更？",
        "save_failed": "無法儲存至 {path}",
        "exit": "結束",
        "capture_failed": "擷取失敗：{error}",
        "open_image_failed": "無法開啟影像：{path}",
        "tooltip_shortcut": "{label} ({shortcut})",
    },
}


class LanguageManager(QObject):
    changed = Signal(LanguageMode, LanguageMode)

    def __init__(self, settings: QSettings | None = None, system_locale: QLocale | None = None) -> None:
        super().__init__()
        self.settings = settings or QSettings()
        self.system_locale = system_locale or QLocale.system()
        self.system_languages = (
            (self.system_locale.uiLanguages() or [self.system_locale.name()])
            if system_locale is not None
            else _system_language_names(self.system_locale)
        )
        self.mode = self._stored_mode()

    @property
    def effective_mode(self) -> LanguageMode:
        if self.mode != LanguageMode.SYSTEM:
            return self.mode
        return (
            LanguageMode.ZH_TW
            if any(_is_traditional_chinese(name) for name in self.system_languages)
            else LanguageMode.EN
        )

    def set_mode(self, mode: LanguageMode) -> None:
        if mode == self.mode:
            return
        self.mode = mode
        self.settings.setValue("appearance/language", mode.value)
        self.changed.emit(mode, self.effective_mode)

    def text(self, key: str, **values) -> str:
        language = self.effective_mode.value
        template = TRANSLATIONS[language].get(key, TRANSLATIONS["en"].get(key, key))
        return template.format(**values)

    def _stored_mode(self) -> LanguageMode:
        value = self.settings.value("appearance/language", LanguageMode.SYSTEM.value)
        try:
            return LanguageMode(str(value))
        except ValueError:
            return LanguageMode.SYSTEM


def _system_language_names(fallback: QLocale) -> list[str]:
    if sys.platform == "darwin":
        languages = _read_macos_user_languages()
        if languages:
            return languages
    return fallback.uiLanguages() or [fallback.name()]


def _read_macos_user_languages() -> list[str]:
    try:
        result = subprocess.run(
            ["defaults", "read", "-g", "AppleLanguages"],
            check=True,
            capture_output=True,
            text=True,
            timeout=2,
        )
    except (OSError, subprocess.SubprocessError):
        return []
    return re.findall(r'"([^\"]+)"', result.stdout)


def _is_traditional_chinese(language: str) -> bool:
    normalized = language.replace("-", "_").lower()
    return normalized.startswith(("zh_tw", "zh_hk", "zh_mo", "zh_hant"))
