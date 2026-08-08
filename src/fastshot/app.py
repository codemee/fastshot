from __future__ import annotations

import ctypes
import sys
import traceback
from ctypes import wintypes

from PySide6.QtCore import QAbstractNativeEventFilter, QObject, QTimer, Signal
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QApplication, QMenu, QMessageBox, QSystemTrayIcon

from fastshot.capture import CaptureService
from fastshot.icons import tray_icon
from fastshot.hotkeys import HotkeyAction, HotkeyCombination, HotkeyStore, validate_hotkeys
from fastshot.i18n import LanguageManager
from fastshot.main_window import EditorWindow
from fastshot.settings import CaptureMode
from fastshot.theme import ThemeManager

if sys.platform == "win32":
    import win32con
    import win32gui
else:  # pragma: no cover - platform branch
    win32con = None
    win32gui = None


class MSG(ctypes.Structure):
    _fields_ = [
        ("hwnd", wintypes.HWND),
        ("message", wintypes.UINT),
        ("wParam", wintypes.WPARAM),
        ("lParam", wintypes.LPARAM),
        ("time", wintypes.DWORD),
        ("pt", wintypes.POINT),
    ]


class HotkeyBridge(QObject):
    captureRequested = Signal(CaptureMode)
    repeatRequested = Signal()


def _activate_window(window) -> None:
    window.showNormal()
    window.raise_()
    window.activateWindow()
    QApplication.processEvents()
    if sys.platform == "win32":
        hwnd = int(window.winId())
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        win32gui.BringWindowToTop(hwnd)
        win32gui.SetForegroundWindow(hwnd)
        if win32gui.GetForegroundWindow() == hwnd:
            return
        flags = win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_SHOWWINDOW
        win32gui.SetWindowPos(hwnd, win32con.HWND_TOPMOST, 0, 0, 0, 0, flags)
        win32gui.SetWindowPos(hwnd, win32con.HWND_NOTOPMOST, 0, 0, 0, 0, flags)
        win32gui.SetForegroundWindow(hwnd)


class WindowsHotkeyFilter(QAbstractNativeEventFilter):
    WM_HOTKEY = 0x0312
    MOD_ALT = 0x0001
    MOD_CONTROL = 0x0002
    MOD_SHIFT = 0x0004
    MOD_NOREPEAT = 0x4000

    def __init__(self, hwnd: int | None, bridge: HotkeyBridge, bindings) -> None:
        super().__init__()
        self.hwnd = hwnd
        self.bridge = bridge
        self.bindings = {
            1001 + index: (combination, mode)
            for index, (mode, combination) in enumerate(bindings.items())
        }
        self.registered_ids: list[int] = []

    def register(self) -> None:
        ctypes.windll.user32.RegisterHotKey.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_uint, ctypes.c_uint]
        ctypes.windll.user32.UnregisterHotKey.argtypes = [ctypes.c_void_p, ctypes.c_int]
        for hotkey_id, (combination, _mode) in self.bindings.items():
            modifiers = self.modifiers(combination) | self.MOD_NOREPEAT
            ok = ctypes.windll.user32.RegisterHotKey(
                ctypes.c_void_p(self.hwnd or 0),
                hotkey_id,
                modifiers,
                ord(combination.letter),
            )
            if not ok:
                self.unregister()
                raise ctypes.WinError()
            self.registered_ids.append(hotkey_id)

    def unregister(self) -> None:
        for hotkey_id in self.registered_ids:
            ctypes.windll.user32.UnregisterHotKey(ctypes.c_void_p(self.hwnd or 0), hotkey_id)
        self.registered_ids.clear()

    def nativeEventFilter(self, event_type, message):
        event_name = bytes(event_type).decode(errors="ignore") if not isinstance(event_type, str) else event_type
        if event_name not in {"windows_generic_MSG", "windows_dispatcher_MSG"}:
            return False, 0
        msg = MSG.from_address(int(message))
        if msg.message != self.WM_HOTKEY:
            return False, 0
        binding = self.bindings.get(int(msg.wParam))
        if binding is None:
            return False, 0
        _combination, mode = binding
        if mode == HotkeyAction.REPEAT:
            self.bridge.repeatRequested.emit()
        else:
            self.bridge.captureRequested.emit(mode)
        return True, 0

    @classmethod
    def modifiers(cls, combination: HotkeyCombination) -> int:
        return (
            (cls.MOD_CONTROL if combination.ctrl else 0)
            | (cls.MOD_SHIFT if combination.shift else 0)
            | (cls.MOD_ALT if combination.alt else 0)
        )


class FastShotApplication(QObject):
    def __init__(self, app: QApplication) -> None:
        super().__init__()
        self.app = app
        self.app.setApplicationName("FastShot")
        self.app.setOrganizationName("FastShot")
        self.app.setQuitOnLastWindowClosed(False)
        self.theme_manager = ThemeManager(self.app)
        self.language_manager = LanguageManager()
        self.capture = CaptureService()
        self.window = EditorWindow(self.theme_manager, self.language_manager)
        self.hotkey_store = HotkeyStore()
        self.hotkeys = self.hotkey_store.load()
        self.bridge = HotkeyBridge()
        self.bridge.captureRequested.connect(self.capture_mode)
        self.bridge.repeatRequested.connect(self.repeat_capture)
        self.tray = self._build_tray()
        self.language_manager.changed.connect(self._language_changed)
        self._hotkey_handles: list[object] = []
        self._native_hotkey_filter: WindowsHotkeyFilter | None = None
        self._mac_hotkey_listener = None
        self._capture_in_progress = False
        self.window.configure_hotkeys(self.hotkeys, self._validate_hotkeys, self._apply_hotkeys)
        self._register_hotkeys()

    def run(self) -> int:
        self.tray.show()
        self.window.hide()
        return self.app.exec()

    def show_window(self) -> None:
        _activate_window(self.window)

    def quit(self) -> None:
        self._unregister_hotkeys()
        self.tray.hide()
        self.app.quit()

    def capture_mode(self, mode: CaptureMode) -> None:
        settings = self.window.capture_settings
        frozen_selection = None

        def freeze_before_hotkey_returns() -> None:
            nonlocal frozen_selection
            frozen_selection = self.capture.prepare_frozen_selection(mode, settings)

        self._start_capture(
            lambda: self.capture.capture(mode, settings, frozen_selection),
            before_event_flush=freeze_before_hotkey_returns,
        )

    def repeat_capture(self) -> None:
        self._start_capture(lambda: self.capture.repeat(self.window.capture_settings))

    def _start_capture(self, capture, before_event_flush=None) -> None:
        if self._capture_in_progress:
            return
        self._capture_in_progress = True
        self.window.hide()
        if before_event_flush is not None:
            try:
                before_event_flush()
            except Exception as exc:  # pragma: no cover - UI guard
                traceback.print_exc()
                QMessageBox.warning(
                    self.window,
                    "FastShot",
                    self.language_manager.text("capture_failed", error=exc),
                )
                self._capture_in_progress = False
                return
        QApplication.processEvents()

        def do_capture() -> None:
            try:
                image = capture()
            except Exception as exc:  # pragma: no cover - UI guard
                traceback.print_exc()
                QMessageBox.warning(
                    self.window,
                    "FastShot",
                    self.language_manager.text("capture_failed", error=exc),
                )
                self._capture_in_progress = False
                return
            if image is None:
                self._capture_in_progress = False
                return
            self.window.add_shot(image)
            self.show_window()
            # Selection completion can post a delayed activation restore after
            # SetForegroundWindow initially succeeds. Reassert the editor once
            # that input transaction has fully settled.
            QTimer.singleShot(200, self.show_window)
            self.window.copy_current()
            self._capture_in_progress = False

        QTimer.singleShot(120, do_capture)

    def _build_tray(self) -> QSystemTrayIcon:
        tray = QSystemTrayIcon(tray_icon(macos=sys.platform == "darwin"), self.app)
        tray.setToolTip("FastShot")
        menu = QMenu()
        self.exit_action = QAction(self.language_manager.text("exit"), menu)
        self.exit_action.triggered.connect(self.quit)
        menu.addAction(self.exit_action)
        tray.setContextMenu(menu)
        tray.activated.connect(self._tray_activated)
        return tray

    def _language_changed(self, _mode, _effective) -> None:
        self.exit_action.setText(self.language_manager.text("exit"))

    def _tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show_window()

    def _register_hotkeys(self, bindings=None, show_warning: bool = True) -> bool:
        bindings = bindings or self.hotkeys
        if sys.platform == "win32":
            try:
                self._native_hotkey_filter = WindowsHotkeyFilter(None, self.bridge, bindings)
                self._native_hotkey_filter.register()
                self.app.installNativeEventFilter(self._native_hotkey_filter)
                return True
            except Exception as exc:
                self._native_hotkey_filter = None
                if show_warning:
                    QMessageBox.warning(self.window, "FastShot", f"Native global hotkeys unavailable: {exc}")
                return False

        if sys.platform == "darwin":
            try:
                from fastshot.platforms.macos import MacHotkeyListener, accessibility_allowed

                accessibility_allowed(request=True)
                actions = {combination: action for action, combination in bindings.items()}

                def dispatch(combination) -> None:
                    action = actions[combination]
                    if action == HotkeyAction.REPEAT:
                        self.bridge.repeatRequested.emit()
                    else:
                        self.bridge.captureRequested.emit(action)

                self._mac_hotkey_listener = MacHotkeyListener(
                    dispatch,
                    tuple(actions),
                )
                self._mac_hotkey_listener.start()
                return True
            except Exception as exc:
                if show_warning:
                    QMessageBox.warning(self.window, "FastShot", f"macOS global hotkeys unavailable: {exc}")
                return False

        try:
            import keyboard
        except Exception as exc:  # pragma: no cover - optional dependency guard
            if show_warning:
                QMessageBox.warning(self.window, "FastShot", f"Global hotkeys unavailable: {exc}")
            return False

        for action, combination in bindings.items():
            shortcut = combination.display().lower()
            try:
                if action == HotkeyAction.REPEAT:
                    callback = lambda: self.bridge.repeatRequested.emit()
                else:
                    callback = lambda capture_mode=action: self.bridge.captureRequested.emit(capture_mode)
                handle = keyboard.add_hotkey(shortcut, callback, suppress=True)
                self._hotkey_handles.append(handle)
            except Exception as exc:
                self._unregister_hotkeys()
                if show_warning:
                    QMessageBox.warning(self.window, "FastShot", f"Could not register {shortcut}: {exc}")
                return False
        return True

    def _validate_hotkeys(self, bindings) -> tuple[bool, str]:
        problem = validate_hotkeys(bindings)
        if problem:
            return False, self.language_manager.text(f"hotkey_{problem}")
        if sys.platform != "win32" or self._native_hotkey_filter is None:
            return True, ""
        owned = {combination for combination, _mode in self._native_hotkey_filter.bindings.values()}
        registered: list[int] = []
        try:
            for index, combination in enumerate(bindings.values()):
                if combination in owned:
                    continue
                hotkey_id = 2101 + index
                ok = ctypes.windll.user32.RegisterHotKey(
                    ctypes.c_void_p(0),
                    hotkey_id,
                    WindowsHotkeyFilter.modifiers(combination)
                    | WindowsHotkeyFilter.MOD_NOREPEAT,
                    ord(combination.letter),
                )
                if not ok:
                    return False, self.language_manager.text(
                        "hotkey_conflict", shortcut=combination.display()
                    )
                registered.append(hotkey_id)
        finally:
            for hotkey_id in registered:
                ctypes.windll.user32.UnregisterHotKey(ctypes.c_void_p(0), hotkey_id)
        return True, ""

    def _apply_hotkeys(self, bindings) -> tuple[bool, str]:
        valid, message = self._validate_hotkeys(bindings)
        if not valid:
            return valid, message
        previous = self.hotkeys
        self._unregister_hotkeys()
        if not self._register_hotkeys(bindings, show_warning=False):
            self._register_hotkeys(previous, show_warning=False)
            return False, self.language_manager.text("hotkey_registration_failed")
        self.hotkeys = dict(bindings)
        self.hotkey_store.save(self.hotkeys)
        self.window.configure_hotkeys(self.hotkeys, self._validate_hotkeys, self._apply_hotkeys)
        return True, ""

    def _unregister_hotkeys(self) -> None:
        if self._mac_hotkey_listener is not None:
            self._mac_hotkey_listener.stop()
            self._mac_hotkey_listener = None
        if self._native_hotkey_filter is not None:
            self.app.removeNativeEventFilter(self._native_hotkey_filter)
            self._native_hotkey_filter.unregister()
            self._native_hotkey_filter = None
        try:
            import keyboard
        except Exception:
            return
        for handle in self._hotkey_handles:
            try:
                keyboard.remove_hotkey(handle)
            except Exception:
                pass
        self._hotkey_handles.clear()


def main() -> int:
    app = QApplication(sys.argv)
    controller = FastShotApplication(app)
    return controller.run()
