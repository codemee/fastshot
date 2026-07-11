from __future__ import annotations

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
        "tooltip_shortcut": "{label} ({shortcut})",
    },
}


class LanguageManager(QObject):
    changed = Signal(LanguageMode, LanguageMode)

    def __init__(self, settings: QSettings | None = None, system_locale: QLocale | None = None) -> None:
        super().__init__()
        self.settings = settings or QSettings()
        self.system_locale = system_locale or QLocale.system()
        self.mode = self._stored_mode()

    @property
    def effective_mode(self) -> LanguageMode:
        if self.mode != LanguageMode.SYSTEM:
            return self.mode
        locale_name = self.system_locale.name().replace("-", "_").lower()
        traditional_regions = ("zh_tw", "zh_hk", "zh_mo", "zh_hant")
        return LanguageMode.ZH_TW if locale_name.startswith(traditional_regions) else LanguageMode.EN

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
