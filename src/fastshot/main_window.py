from __future__ import annotations

from pathlib import Path

from PIL import Image
from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtGui import QAction, QActionGroup, QColor, QKeySequence
from PySide6.QtWidgets import (
    QColorDialog,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSlider,
    QSpinBox,
    QTabWidget,
    QToolButton,
    QToolBar,
    QVBoxLayout,
    QWidget,
    QWidgetAction,
)

from fastshot.canvas import ImageCanvas
from fastshot.document import ShotDocument, make_tab_title
from fastshot.icons import camera_icon, tool_icon
from fastshot.i18n import LanguageManager, LanguageMode
from fastshot.qt_image import pil_to_qimage
from fastshot.settings import CaptureSettings, DrawingSettings, Tool
from fastshot.theme import ThemeManager, ThemeMode


class ArrowSpinBox(QSpinBox):
    BUTTON_WIDTH = 20

    def __init__(self) -> None:
        super().__init__()
        self.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)
        self.lineEdit().setTextMargins(0, 0, self.BUTTON_WIDTH, 0)
        self.up_button = self._arrow_button(Qt.ArrowType.UpArrow, self.stepUp)
        self.down_button = self._arrow_button(Qt.ArrowType.DownArrow, self.stepDown)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        half = self.height() // 2
        left = self.width() - self.BUTTON_WIDTH
        self.up_button.setGeometry(left, 0, self.BUTTON_WIDTH, half)
        self.down_button.setGeometry(left, half, self.BUTTON_WIDTH, self.height() - half)

    def _arrow_button(self, arrow: Qt.ArrowType, callback) -> QToolButton:
        button = QToolButton(self)
        button.setProperty("spinArrow", True)
        button.setArrowType(arrow)
        button.setAutoRepeat(True)
        button.setAutoRepeatDelay(350)
        button.setAutoRepeatInterval(80)
        button.clicked.connect(callback)
        return button


class EditorWindow(QMainWindow):
    hiddenByMinimize = Signal()

    def __init__(
        self,
        theme_manager: ThemeManager | None = None,
        language_manager: LanguageManager | None = None,
    ) -> None:
        super().__init__()
        from PySide6.QtWidgets import QApplication

        self.theme_manager = theme_manager or ThemeManager(QApplication.instance())
        self.language_manager = language_manager or LanguageManager()
        self.setWindowIcon(camera_icon())
        self.settings = DrawingSettings.default()
        self.capture_settings = CaptureSettings()
        self.active_tool = Tool.PEN
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.setUsesScrollButtons(True)
        self.tabs.tabBar().setExpanding(False)
        self.tabs.currentChanged.connect(self._current_changed)
        self.tabs.tabCloseRequested.connect(self._close_tab)
        self.setCentralWidget(self.tabs)
        self.documents: dict[int, ShotDocument] = {}
        self.tab_menu_button = QToolButton()
        self.tab_menu_button.setArrowType(Qt.ArrowType.DownArrow)
        self.tab_menu_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.tab_menu_button.setAutoRaise(True)
        self.tab_menu_button.setToolTip("Open tabs")
        self.tab_menu = QMenu(self)
        self.tab_menu_button.setMenu(self.tab_menu)
        self.tab_menu_button.hide()
        self.tabs.setCornerWidget(self.tab_menu_button, Qt.Corner.TopRightCorner)
        self._build_toolbar()
        self.theme_manager.changed.connect(self._theme_changed)
        self.language_manager.changed.connect(self._language_changed)
        self._retranslate_ui()
        self._update_title()
        self._update_actions()
        self.resize(1100, 760)

    def add_shot(self, image: Image.Image) -> None:
        title = make_tab_title()
        qimage = pil_to_qimage(image)
        canvas = ImageCanvas(qimage, self.settings)
        canvas.set_tool(self.active_tool)
        canvas.changed.connect(self._mark_current_dirty)
        area = QScrollArea()
        area.setWidget(canvas)
        area.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        index = self.tabs.addTab(area, title + "*")
        self.documents[index] = ShotDocument(title=title, image=canvas)
        self.tabs.setCurrentIndex(index)
        self.showNormal()
        self.raise_()
        self.activateWindow()
        self._refresh_tabs()

    def set_active_tool(self, tool: Tool) -> None:
        self.active_tool = tool
        canvas = self._current_canvas()
        if canvas:
            canvas.set_tool(tool)

    def copy_current(self) -> None:
        canvas = self._current_canvas()
        if canvas is None:
            return
        from PySide6.QtWidgets import QApplication

        QApplication.clipboard().setImage(canvas.export_image())

    def save_current(self) -> None:
        doc = self._current_doc()
        if doc is None or not doc.can_save:
            return
        if doc.path is None:
            self.save_current_as()
            return
        self._save_to_path(doc, doc.path)

    def save_current_as(self) -> None:
        doc = self._current_doc()
        canvas = self._current_canvas()
        if doc is None or canvas is None:
            return
        default_path = doc.path or Path.cwd() / f"{doc.title}.png"
        path, selected = QFileDialog.getSaveFileName(
            self,
            self._tr("save_screenshot"),
            str(default_path),
            "PNG Image (*.png);;JPEG Image (*.jpg *.jpeg)",
            "PNG Image (*.png)" if default_path.suffix.lower() != ".jpg" else "JPEG Image (*.jpg *.jpeg)",
        )
        if not path:
            return
        target = Path(path)
        if not target.suffix:
            target = target.with_suffix(".jpg" if "JPEG" in selected else ".png")
        self._save_to_path(doc, target)

    def zoom_in(self) -> None:
        canvas = self._current_canvas()
        if canvas:
            canvas.zoom_in()

    def zoom_out(self) -> None:
        canvas = self._current_canvas()
        if canvas:
            canvas.zoom_out()

    def zoom_reset(self) -> None:
        canvas = self._current_canvas()
        if canvas:
            canvas.set_zoom(1.0)

    def closeEvent(self, event) -> None:
        if self._has_dirty_documents():
            reply = QMessageBox.question(
                self,
                "FastShot",
                self._tr("close_discard_all"),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                event.ignore()
                return
        self._discard_all_tabs()
        self.hide()
        event.ignore()

    def changeEvent(self, event) -> None:
        if event.type() == event.Type.WindowStateChange and self.isMinimized():
            self.hide()
            self.hiddenByMinimize.emit()
        super().changeEvent(event)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._update_tab_overflow()

    def _build_toolbar(self) -> None:
        toolbar = QToolBar("Tools")
        toolbar.setMovable(False)
        toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        toolbar.setIconSize(toolbar.iconSize() * 1.25)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, toolbar)
        self.tool_group = QActionGroup(self)
        self.tool_group.setExclusive(True)

        self.pen_action = self._tool_action("Pen", "Alt+P", Tool.PEN, "pen")
        self.line_action = self._tool_action("Line", "Alt+L", Tool.LINE, "line")
        self.arrow_action = self._tool_action("Arrow", "Alt+A", Tool.ARROW, "arrow")
        self.rect_action = self._tool_action("Rectangle", "Alt+R", Tool.RECTANGLE, "rectangle")
        self.text_action = self._tool_action("Text", "Alt+T", Tool.TEXT, "text")
        self.mosaic_action = self._tool_action("Mosaic", "Alt+M", Tool.MOSAIC, "mosaic")
        for action in [
            self.pen_action,
            self.line_action,
            self.arrow_action,
            self.rect_action,
            self.text_action,
            self.mosaic_action,
        ]:
            self.tool_group.addAction(action)
            toolbar.addAction(action)
        self.pen_action.setChecked(True)

        self.style_action = QAction(self._style_icon(), "Line and color", self)
        self.style_action.setShortcut("Alt+C")
        self.style_action.triggered.connect(self._show_style_panel)
        toolbar.addAction(self.style_action)
        toolbar.addSeparator()

        self.undo_action = QAction(tool_icon("undo"), "Undo", self)
        self.undo_action.setShortcut(QKeySequence.StandardKey.Undo)
        self.undo_action.triggered.connect(lambda: self._current_canvas() and self._current_canvas().undo())
        toolbar.addAction(self.undo_action)

        self.copy_action = QAction(tool_icon("copy"), "Copy", self)
        self.copy_action.setShortcut(QKeySequence.StandardKey.Copy)
        self.copy_action.triggered.connect(self.copy_current)
        toolbar.addAction(self.copy_action)

        self.save_action = QAction(tool_icon("save"), "Save", self)
        self.save_action.setShortcut(QKeySequence.StandardKey.Save)
        self.save_action.triggered.connect(self.save_current)
        toolbar.addAction(self.save_action)

        self.save_as_action = QAction(tool_icon("save_as"), "Save As", self)
        self.save_as_action.setShortcut(QKeySequence.StandardKey.SaveAs)
        self.save_as_action.triggered.connect(self.save_current_as)
        toolbar.addAction(self.save_as_action)
        toolbar.addSeparator()

        self.zoom_in_action = QAction(tool_icon("zoom_in"), "Zoom in", self)
        self.zoom_in_action.setShortcuts([QKeySequence("Ctrl++"), QKeySequence("Ctrl+=")])
        self.zoom_in_action.triggered.connect(self.zoom_in)
        toolbar.addAction(self.zoom_in_action)

        self.zoom_out_action = QAction(tool_icon("zoom_out"), "Zoom out", self)
        self.zoom_out_action.setShortcuts([QKeySequence("Ctrl+-")])
        self.zoom_out_action.triggered.connect(self.zoom_out)
        toolbar.addAction(self.zoom_out_action)

        self.zoom_reset_action = QAction("Reset zoom", self)
        self.zoom_reset_action.setShortcut(QKeySequence("Ctrl+0"))
        self.zoom_reset_action.triggered.connect(self.zoom_reset)
        self.addAction(self.zoom_reset_action)

        self.cursor_action = QAction(tool_icon("cursor", checked=False), "Include cursor", self)
        self.cursor_action.setCheckable(True)
        self.cursor_action.toggled.connect(self._set_include_cursor)
        toolbar.addAction(self.cursor_action)

        self.delay_action = QAction(self._delay_icon(), "Delay", self)
        self.delay_action.triggered.connect(self._show_delay_panel)
        toolbar.addAction(self.delay_action)

        toolbar.addSeparator()
        self.theme_action = QAction(self._theme_icon(), "Theme: follow system", self)
        self.theme_action.triggered.connect(self._cycle_theme)
        toolbar.addAction(self.theme_action)

        self.language_action = QAction(tool_icon("language", badge="system"), "Language", self)
        self.language_action.triggered.connect(self._cycle_language)
        toolbar.addAction(self.language_action)
        self._refresh_toolbar_icons()

    def _tool_action(self, text: str, shortcut: str, tool: Tool, icon_name: str) -> QAction:
        action = QAction(tool_icon(icon_name), text, self)
        action.setCheckable(True)
        action.setShortcut(shortcut)
        action.triggered.connect(lambda: self.set_active_tool(tool))
        return action

    def _show_style_panel(self) -> None:
        menu = QMenu(self)
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)

        width_row = QHBoxLayout()
        width_row.addWidget(QLabel(self._tr("width")))
        width_slider = QSlider(Qt.Orientation.Horizontal)
        width_slider.setRange(1, 48)
        width_slider.setValue(self.settings.line_width)
        width_spin = ArrowSpinBox()
        width_spin.setRange(1, 48)
        width_spin.setValue(self.settings.line_width)
        width_slider.valueChanged.connect(width_spin.setValue)
        width_spin.valueChanged.connect(width_slider.setValue)
        width_spin.valueChanged.connect(self._set_line_width)
        width_row.addWidget(width_slider)
        width_row.addWidget(width_spin)
        layout.addLayout(width_row)

        swatches = QGridLayout()
        colors = [
            "#000000",
            "#212529",
            "#343a40",
            "#495057",
            "#868e96",
            "#adb5bd",
            "#ced4da",
            "#ffffff",
            "#fff5f5",
            "#ffe3e3",
            "#ffc9c9",
            "#ff8787",
            "#fa5252",
            "#e03131",
            "#c92a2a",
            "#fff4e6",
            "#ffe8cc",
            "#ffc078",
            "#ff922b",
            "#f76707",
            "#e8590c",
            "#fff9db",
            "#fff3bf",
            "#ffe066",
            "#ffd43b",
            "#fab005",
            "#f08c00",
            "#ebfbee",
            "#d3f9d8",
            "#8ce99a",
            "#51cf66",
            "#37b24d",
            "#2b8a3e",
            "#e6fcf5",
            "#c3fae8",
            "#63e6be",
            "#20c997",
            "#0ca678",
            "#087f5b",
            "#e3fafc",
            "#c5f6fa",
            "#66d9e8",
            "#22b8cf",
            "#15aabf",
            "#0b7285",
            "#e7f5ff",
            "#d0ebff",
            "#74c0fc",
            "#339af0",
            "#228be6",
            "#1971c2",
            "#edf2ff",
            "#dbe4ff",
            "#91a7ff",
            "#5c7cfa",
            "#4263eb",
            "#364fc7",
            "#f3f0ff",
            "#e5dbff",
            "#b197fc",
            "#845ef7",
            "#7048e8",
            "#5f3dc4",
            "#f8f0fc",
            "#eebefa",
            "#da77f2",
            "#be4bdb",
            "#ae3ec9",
            "#862e9c",
            "#fff0f6",
            "#fcc2d7",
            "#f783ac",
            "#f06595",
            "#d6336c",
            "#a61e4d",
        ]
        for index, value in enumerate(colors):
            button = QPushButton()
            button.setFixedSize(18, 18)
            button.setStyleSheet(f"background: {value}; border: 0; border-radius: 2px;")
            button.clicked.connect(lambda _checked=False, color=value: self._set_line_color(QColor(color)))
            swatches.addWidget(button, index // 12, index % 12)
        layout.addLayout(swatches)

        custom_button = QPushButton(self._tr("custom_color"))
        custom_button.clicked.connect(self._choose_custom_line_color)
        layout.addWidget(custom_button)

        action = QWidgetAction(menu)
        action.setDefaultWidget(panel)
        menu.addAction(action)
        menu.exec(self.mapToGlobal(self._toolbar_anchor(self.style_action)))

    def _show_delay_panel(self) -> None:
        menu = QMenu(self)
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)
        row = QHBoxLayout()
        for seconds in (0, 1, 3, 5):
            button = QPushButton(self._tr("off") if seconds == 0 else f"{seconds}s")
            button.setCheckable(True)
            button.setChecked(self.capture_settings.delay_seconds == seconds)
            button.clicked.connect(lambda _checked=False, value=seconds, popup=menu: self._set_delay(value, popup))
            row.addWidget(button)
        layout.addLayout(row)
        custom_row = QHBoxLayout()
        custom_row.addWidget(QLabel(self._tr("custom")))
        custom = ArrowSpinBox()
        custom.setRange(0, 60)
        custom.setSuffix(" s")
        custom.setValue(round(self.capture_settings.delay_seconds))
        custom.valueChanged.connect(lambda value: self._set_delay(float(value), None))
        custom_row.addWidget(custom)
        layout.addLayout(custom_row)
        action = QWidgetAction(menu)
        action.setDefaultWidget(panel)
        menu.addAction(action)
        menu.exec(self.mapToGlobal(self._toolbar_anchor(self.delay_action)))

    def _cycle_theme(self) -> None:
        modes = (ThemeMode.SYSTEM, ThemeMode.LIGHT, ThemeMode.DARK)
        index = modes.index(self.theme_manager.mode)
        self.theme_manager.set_mode(modes[(index + 1) % len(modes)])

    def _cycle_language(self) -> None:
        modes = (LanguageMode.SYSTEM, LanguageMode.ZH_TW, LanguageMode.EN)
        index = modes.index(self.language_manager.mode)
        self.language_manager.set_mode(modes[(index + 1) % len(modes)])

    def _set_line_width(self, width: int) -> None:
        self.settings.line_width = width
        self.style_action.setIcon(self._style_icon())

    def _set_line_color(self, color: QColor) -> None:
        self.settings.color = color
        self.style_action.setIcon(self._style_icon())

    def _choose_custom_line_color(self) -> None:
        color = QColorDialog.getColor(self.settings.color, self, self._tr("line_color_dialog"))
        if color.isValid():
            self._set_line_color(color)

    def _set_delay(self, seconds: float, popup: QMenu | None) -> None:
        self.capture_settings.delay_seconds = seconds
        self.delay_action.setToolTip(self._tr("delay_value", seconds=seconds))
        self.delay_action.setIcon(self._delay_icon())
        if popup is not None:
            popup.close()

    def _set_include_cursor(self, checked: bool) -> None:
        self.capture_settings.include_cursor = checked
        self.cursor_action.setIcon(tool_icon("cursor", checked=checked, dark=self._is_dark_theme()))
        self.cursor_action.setToolTip(
            self._tr("include_cursor_on") if checked else self._tr("include_cursor_off")
        )

    def _save_to_path(self, doc: ShotDocument, path: Path) -> None:
        canvas = self._current_canvas()
        if canvas is None:
            return
        suffix = path.suffix.lower()
        image = canvas.export_image()
        fmt = "JPG" if suffix in {".jpg", ".jpeg"} else "PNG"
        if not image.save(str(path), fmt):
            QMessageBox.warning(self, "FastShot", self._tr("save_failed", path=path))
            return
        doc.mark_saved(path)
        self._refresh_tabs()

    def _current_area(self) -> QScrollArea | None:
        widget = self.tabs.currentWidget()
        return widget if isinstance(widget, QScrollArea) else None

    def _current_canvas(self) -> ImageCanvas | None:
        area = self._current_area()
        if area is None:
            return None
        widget = area.widget()
        return widget if isinstance(widget, ImageCanvas) else None

    def _current_doc(self) -> ShotDocument | None:
        return self.documents.get(self.tabs.currentIndex())

    def _mark_current_dirty(self) -> None:
        doc = self._current_doc()
        if doc:
            doc.mark_dirty()
        self._refresh_tabs()

    def _current_changed(self, _index: int) -> None:
        self._update_title()
        self._update_actions()

    def _close_tab(self, index: int) -> None:
        doc = self.documents.get(index)
        if doc and doc.is_dirty:
            reply = QMessageBox.question(
                self,
                "FastShot",
                self._tr("close_discard_tab", title=doc.title),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
        self.tabs.removeTab(index)
        self._reindex_documents(index)
        self._refresh_tabs()

    def _pick_tab(self, picker_index: int) -> None:
        if picker_index >= 0 and picker_index != self.tabs.currentIndex():
            self.tabs.setCurrentIndex(picker_index)

    def _reindex_documents(self, closed_index: int) -> None:
        new_docs: dict[int, ShotDocument] = {}
        for index, doc in self.documents.items():
            if index < closed_index:
                new_docs[index] = doc
            elif index > closed_index:
                new_docs[index - 1] = doc
        self.documents = new_docs

    def _discard_all_tabs(self) -> None:
        self.tabs.clear()
        self.documents.clear()
        self._refresh_tabs()

    def _refresh_tabs(self) -> None:
        current = self.tabs.currentIndex()
        for i in range(self.tabs.count()):
            doc = self.documents.get(i)
            if doc:
                self.tabs.setTabText(i, doc.display_title)
        self.tab_menu.clear()
        for i in range(self.tabs.count()):
            action = self.tab_menu.addAction(self.tabs.tabText(i))
            action.setCheckable(True)
            action.setChecked(i == current)
            action.triggered.connect(lambda _checked=False, index=i: self.tabs.setCurrentIndex(index))
        self._update_title()
        self._update_actions()
        self._update_tab_overflow()

    def _update_title(self) -> None:
        doc = self._current_doc()
        self.setWindowTitle(f"FastShot-{doc.title}" if doc else "FastShot")

    def _update_actions(self) -> None:
        has_doc = self._current_doc() is not None
        doc = self._current_doc()
        canvas = self._current_canvas()
        for action in [
            self.pen_action,
            self.line_action,
            self.arrow_action,
            self.rect_action,
            self.text_action,
            self.mosaic_action,
        ]:
            action.setEnabled(has_doc)
        self.style_action.setEnabled(has_doc)
        self.copy_action.setEnabled(has_doc)
        self.save_action.setEnabled(bool(doc and doc.can_save))
        self.save_as_action.setEnabled(has_doc)
        self.undo_action.setEnabled(bool(canvas and canvas.can_undo))
        self.zoom_in_action.setEnabled(has_doc)
        self.zoom_out_action.setEnabled(has_doc)
        self.zoom_reset_action.setEnabled(has_doc)

    def _has_dirty_documents(self) -> bool:
        return any(doc.is_dirty for doc in self.documents.values())

    def _style_icon(self) -> QIcon:
        return tool_icon("style", self.settings.color, self.settings.line_width, dark=self._is_dark_theme())

    def _delay_icon(self) -> QIcon:
        seconds = self.capture_settings.delay_seconds
        if seconds <= 0:
            return tool_icon("delay", badge="off", dark=self._is_dark_theme())
        return tool_icon("delay", badge=f"{seconds:g}", dark=self._is_dark_theme())

    def _theme_icon(self) -> QIcon:
        badge = (
            "system"
            if self.theme_manager.mode == ThemeMode.SYSTEM
            else self.theme_manager.effective_mode.value
        )
        return tool_icon("theme", badge=badge, dark=self._is_dark_theme())

    def _theme_changed(self, mode: ThemeMode, effective: ThemeMode) -> None:
        self._refresh_toolbar_icons()
        self._retranslate_ui()

    def _language_changed(self, _mode: LanguageMode, _effective: LanguageMode) -> None:
        self._retranslate_ui()
        self._refresh_toolbar_icons()

    def _tr(self, key: str, **values) -> str:
        return self.language_manager.text(key, **values)

    def _tooltip_with_shortcuts(self, label: str, action: QAction) -> str:
        shortcuts = [
            shortcut.toString(QKeySequence.SequenceFormat.NativeText)
            for shortcut in action.shortcuts()
            if not shortcut.isEmpty()
        ]
        if not shortcuts:
            return label
        return self._tr("tooltip_shortcut", label=label, shortcut=" / ".join(shortcuts))

    def _retranslate_ui(self) -> None:
        labels = (
            (self.pen_action, "pen"),
            (self.line_action, "line"),
            (self.arrow_action, "arrow"),
            (self.rect_action, "rectangle"),
            (self.text_action, "text"),
            (self.mosaic_action, "mosaic"),
            (self.style_action, "line_color"),
            (self.undo_action, "undo"),
            (self.copy_action, "copy"),
            (self.save_action, "save"),
            (self.save_as_action, "save_as"),
            (self.zoom_in_action, "zoom_in"),
            (self.zoom_out_action, "zoom_out"),
            (self.zoom_reset_action, "reset_zoom"),
            (self.delay_action, "delay"),
        )
        for action, key in labels:
            label = self._tr(key)
            action.setText(label)
            action.setToolTip(self._tooltip_with_shortcuts(label, action))
        self.tab_menu_button.setToolTip(self._tr("open_tabs"))
        self.cursor_action.setText(self._tr("include_cursor"))
        self._set_include_cursor(self.capture_settings.include_cursor)
        self._set_delay(self.capture_settings.delay_seconds, None)
        mode = self.theme_manager.mode.value
        effective = self.theme_manager.effective_mode.value
        self.theme_action.setToolTip(
            self._tr(
                "theme",
                mode=self._tr(f"theme_{mode}"),
                effective=self._tr(f"theme_{effective}"),
            )
        )
        language_mode = self.language_manager.mode.value
        language_effective = self.language_manager.effective_mode.value
        self.language_action.setToolTip(
            self._tr(
                "language",
                mode=self._tr(f"language_{language_mode}"),
                effective=self._tr(f"language_{language_effective}"),
            )
        )

    def _is_dark_theme(self) -> bool:
        return self.theme_manager.effective_mode == ThemeMode.DARK

    def _refresh_toolbar_icons(self) -> None:
        dark = self._is_dark_theme()
        for action, name in (
            (self.pen_action, "pen"),
            (self.line_action, "line"),
            (self.arrow_action, "arrow"),
            (self.rect_action, "rectangle"),
            (self.text_action, "text"),
            (self.mosaic_action, "mosaic"),
            (self.undo_action, "undo"),
            (self.copy_action, "copy"),
            (self.save_action, "save"),
            (self.save_as_action, "save_as"),
            (self.zoom_in_action, "zoom_in"),
            (self.zoom_out_action, "zoom_out"),
        ):
            action.setIcon(tool_icon(name, dark=dark))
        self.style_action.setIcon(self._style_icon())
        self.cursor_action.setIcon(tool_icon("cursor", checked=self.capture_settings.include_cursor, dark=dark))
        self.delay_action.setIcon(self._delay_icon())
        self.theme_action.setIcon(self._theme_icon())
        self.language_action.setIcon(
            tool_icon("language", badge=self.language_manager.mode.value, dark=dark)
        )

    def _toolbar_anchor(self, action: QAction) -> QPoint:
        for toolbar in self.findChildren(QToolBar):
            widget = toolbar.widgetForAction(action)
            if widget:
                point = widget.mapTo(self, widget.rect().bottomLeft())
                return point
        return QPoint(0, 0)

    def _update_tab_overflow(self) -> None:
        tab_bar = self.tabs.tabBar()
        total_width = sum(tab_bar.tabRect(i).width() for i in range(tab_bar.count()))
        available = max(0, self.tabs.width() - 8)
        self.tab_menu_button.setVisible(total_width > available and self.tabs.count() > 0)
