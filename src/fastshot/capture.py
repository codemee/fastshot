from __future__ import annotations

import sys
import time
import math
from ctypes import POINTER, Structure, byref, c_int, c_uint, c_void_p, memset, sizeof, string_at, windll
from ctypes.wintypes import BOOL, BYTE, DWORD, HBITMAP, HDC, HGDIOBJ, HICON, HWND, LONG, RECT, WORD
from dataclasses import dataclass

import mss
from PIL import Image, ImageGrab
from PySide6.QtCore import QPoint, QRect, Qt
from PySide6.QtGui import QColor, QCursor, QFont, QGuiApplication, QMouseEvent, QPainter, QPen
from PySide6.QtWidgets import QApplication, QWidget

from fastshot.settings import CaptureMode, CaptureSettings

if sys.platform == "win32":
    import win32api
    import win32con
    import win32gui
    DWMWA_EXTENDED_FRAME_BOUNDS = 9
    CURSOR_SHOWING = 1
    DI_NORMAL = 3
    BI_RGB = 0
    DIB_RGB_COLORS = 0
else:  # pragma: no cover - platform branch
    win32api = None
    win32con = None
    win32gui = None
    DWMWA_EXTENDED_FRAME_BOUNDS = None
    CURSOR_SHOWING = None
    DI_NORMAL = None
    BI_RGB = None
    DIB_RGB_COLORS = None


class BITMAPINFOHEADER(Structure):
    _fields_ = [
        ("biSize", DWORD),
        ("biWidth", LONG),
        ("biHeight", LONG),
        ("biPlanes", WORD),
        ("biBitCount", WORD),
        ("biCompression", DWORD),
        ("biSizeImage", DWORD),
        ("biXPelsPerMeter", LONG),
        ("biYPelsPerMeter", LONG),
        ("biClrUsed", DWORD),
        ("biClrImportant", DWORD),
    ]


class RGBQUAD(Structure):
    _fields_ = [
        ("rgbBlue", BYTE),
        ("rgbGreen", BYTE),
        ("rgbRed", BYTE),
        ("rgbReserved", BYTE),
    ]


class BITMAPINFO(Structure):
    _fields_ = [("bmiHeader", BITMAPINFOHEADER), ("bmiColors", RGBQUAD * 1)]


class ICONINFO(Structure):
    _fields_ = [
        ("fIcon", BOOL),
        ("xHotspot", DWORD),
        ("yHotspot", DWORD),
        ("hbmMask", HBITMAP),
        ("hbmColor", HBITMAP),
    ]


_UIA_AUTOMATION = None
_UIA_POINT = None


@dataclass(frozen=True)
class CaptureRect:
    left: int
    top: int
    width: int
    height: int

    @classmethod
    def from_qrect(cls, rect: QRect) -> "CaptureRect":
        normalized = rect.normalized()
        return cls(normalized.x(), normalized.y(), normalized.width(), normalized.height())

    @property
    def is_empty(self) -> bool:
        return self.width <= 0 or self.height <= 0

    def to_mss(self) -> dict[str, int]:
        return {"left": self.left, "top": self.top, "width": self.width, "height": self.height}

    def intersect(self, other: "CaptureRect") -> "CaptureRect | None":
        left = max(self.left, other.left)
        top = max(self.top, other.top)
        right = min(self.left + self.width, other.left + other.width)
        bottom = min(self.top + self.height, other.top + other.height)
        if right <= left or bottom <= top:
            return None
        return CaptureRect(left, top, right - left, bottom - top)


class RegionSelector(QWidget):
    def __init__(self) -> None:
        super().__init__(None)
        self.start: QPoint | None = None
        self.end: QPoint | None = None
        self.selected_rect: QRect | None = None
        self.cancelled = False
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.setMouseTracking(True)
        self.setGeometry(_virtual_screen_rect())

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 80))
        if self.start and self.end:
            rect = QRect(self.mapFromGlobal(self.start), self.mapFromGlobal(self.end)).normalized()
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
            painter.fillRect(rect, QColor(0, 0, 0, 0))
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
            painter.setPen(QPen(QColor("#ff922b"), 2))
            painter.drawRect(rect)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.start = event.globalPosition().toPoint()
            self.end = self.start
            self.update()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self.start:
            self.end = event.globalPosition().toPoint()
            self.update()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self.start:
            self.end = event.globalPosition().toPoint()
            self.selected_rect = QRect(self.start, self.end).normalized().intersected(self.geometry())
            self.close()

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.cancelled = True
            self.close()


class WindowSelector(QWidget):
    def __init__(self) -> None:
        super().__init__(None)
        self.target_rect: CaptureRect | None = None
        self._last_query_at = 0.0
        self._left_was_down = False
        self.cancelled = False
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowTransparentForInput
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMouseTracking(True)
        self.setGeometry(_virtual_screen_rect())

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 40))
        if self.target_rect is not None:
            rect = QRect(
                self.mapFromGlobal(QPoint(self.target_rect.left, self.target_rect.top)),
                self.mapFromGlobal(
                    QPoint(
                        self.target_rect.left + self.target_rect.width,
                        self.target_rect.top + self.target_rect.height,
                    )
                ),
            ).normalized()
            painter.setPen(QPen(QColor("#ff922b"), 3))
            painter.drawRect(rect)
        painter.setPen(QPen(QColor("#f8f9fa"), 2))
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Click a window or control, Esc to cancel")

    def poll(self) -> None:
        if win32api is None:
            return
        if win32api.GetAsyncKeyState(0x1B) & 0x8000:
            self.cancelled = True
            self.close()
            return
        point_tuple = win32api.GetCursorPos()
        point = QPoint(point_tuple[0], point_tuple[1])
        now = time.monotonic()
        if now - self._last_query_at >= 0.04:
            self._last_query_at = now
            rect = self._target_at_point(point, use_uia=True)
            if rect != self.target_rect:
                self.target_rect = rect
                self.update()
        left_is_down = bool(win32api.GetAsyncKeyState(0x01) & 0x8000)
        if self._left_was_down and not left_is_down:
            if self.target_rect is None:
                self.target_rect = self._target_at_point(point, use_uia=True)
            self.close()
        self._left_was_down = left_is_down

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.cancelled = True
            self.close()

    def _target_at_point(self, point: QPoint, use_uia: bool, temporary: bool = False) -> CaptureRect | None:
        if use_uia:
            rect = _window_rect_at_point(point, use_uia=True)
            return rect
        return _window_rect_at_point(point, exclude_hwnd=int(self.winId()), use_uia=False)


class CountdownOverlay(QWidget):
    def __init__(self, seconds: float) -> None:
        super().__init__(None)
        self.remaining = max(0, int(math.ceil(seconds)))
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowTransparentForInput
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.resize(150, 72)
        self._move_to_bottom_right()

    def set_remaining(self, seconds: int) -> None:
        self.remaining = max(0, seconds)
        self.update()

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(20, 20, 20, 185))
        painter.drawRoundedRect(self.rect(), 12, 12)
        painter.setPen(QColor("#ffffff"))
        font = QFont()
        font.setPointSize(26)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, str(self.remaining))

    def _move_to_bottom_right(self) -> None:
        screen = QGuiApplication.screenAt(QCursor.pos())
        if screen is None:
            screen = QGuiApplication.primaryScreen()
        geometry = screen.availableGeometry()
        margin = 24
        self.move(geometry.right() - self.width() - margin, geometry.bottom() - self.height() - margin)


class CaptureService:
    def capture(self, mode: CaptureMode, settings: CaptureSettings) -> Image.Image | None:
        rect = self._rect_for_mode(mode)
        if rect is None or rect.is_empty:
            return None

        if settings.delay_seconds > 0:
            self._countdown(settings.delay_seconds)

        image = self._grab_rect(rect)
        if settings.include_cursor:
            self._draw_cursor(image, rect)
        return image

    def _rect_for_mode(self, mode: CaptureMode) -> CaptureRect | None:
        if mode == CaptureMode.FULLSCREEN:
            return self._fullscreen_rect()
        if mode == CaptureMode.REGION:
            return self._select_region()
        if mode == CaptureMode.ACTIVE_WINDOW:
            return self._active_window_rect() or self._fullscreen_rect()
        if mode == CaptureMode.WINDOW_UNDER_CURSOR:
            return self._window_under_cursor_rect() or self._fullscreen_rect()
        return None

    def _fullscreen_rect(self) -> CaptureRect:
        with mss.mss() as sct:
            monitor = sct.monitors[0]
            return CaptureRect(monitor["left"], monitor["top"], monitor["width"], monitor["height"])

    def _select_region(self) -> CaptureRect | None:
        selector = RegionSelector()
        selector.show()
        QApplication.setActiveWindow(selector)
        while selector.isVisible():
            QApplication.processEvents()
            time.sleep(0.01)
        if selector.cancelled or selector.selected_rect is None:
            return None
        selected = CaptureRect.from_qrect(selector.selected_rect)
        return selected.intersect(self._fullscreen_rect())

    def _active_window_rect(self) -> CaptureRect | None:
        if win32gui is None:
            return None
        hwnd = win32gui.GetForegroundWindow()
        return _window_rect(hwnd)

    def _window_under_cursor_rect(self) -> CaptureRect | None:
        if win32gui is None or win32api is None:
            return None
        return self._select_window_rect()

    def _grab_rect(self, rect: CaptureRect) -> Image.Image:
        clipped = rect.intersect(self._fullscreen_rect())
        if clipped is None or clipped.is_empty:
            raise ValueError(f"Capture rectangle is outside the virtual screen: {rect}")
        try:
            with mss.mss() as sct:
                shot = sct.grab(clipped.to_mss())
                return Image.frombytes("RGB", shot.size, shot.rgb)
        except Exception:
            bbox = (
                clipped.left,
                clipped.top,
                clipped.left + clipped.width,
                clipped.top + clipped.height,
            )
            return ImageGrab.grab(bbox=bbox, all_screens=True).convert("RGB")

    def _draw_cursor(self, image: Image.Image, rect: CaptureRect) -> None:
        if win32gui is None or win32api is None:
            return
        try:
            cursor = _current_cursor_image()
        except Exception:
            return
        if cursor is None:
            return
        cursor_image, hotspot_x, hotspot_y, screen_x, screen_y = cursor
        paste_x = screen_x - rect.left - hotspot_x
        paste_y = screen_y - rect.top - hotspot_y
        image.paste(cursor_image, (paste_x, paste_y), cursor_image)

    def _select_window_rect(self) -> CaptureRect | None:
        selector = WindowSelector()
        selector.show()
        QApplication.setActiveWindow(selector)
        while selector.isVisible():
            selector.poll()
            QApplication.processEvents()
            time.sleep(0.01)
        if selector.cancelled:
            return None
        return selector.target_rect

    def _countdown(self, seconds: float) -> None:
        overlay = CountdownOverlay(seconds)
        overlay.show()
        start = time.monotonic()
        total = max(0.0, seconds)
        while True:
            elapsed = time.monotonic() - start
            remaining = max(0, math.ceil(total - elapsed))
            overlay.set_remaining(remaining)
            QApplication.processEvents()
            if elapsed >= total:
                break
            time.sleep(0.05)
        overlay.hide()
        QApplication.processEvents()
        time.sleep(0.05)


def _window_rect(hwnd: int | None) -> CaptureRect | None:
    if not hwnd or win32gui is None:
        return None
    if not win32gui.IsWindowVisible(hwnd):
        return None
    dwm_rect = _dwm_window_rect(hwnd)
    if dwm_rect is not None:
        return dwm_rect
    left, top, right, bottom = win32gui.GetWindowRect(hwnd)
    return CaptureRect(left, top, right - left, bottom - top)


def _window_rect_at_point(
    point: QPoint,
    exclude_hwnd: int | None = None,
    use_uia: bool = True,
) -> CaptureRect | None:
    if win32gui is None:
        return None
    uia_rect = _uia_rect_at_point(point) if use_uia else None
    if uia_rect is not None and not _looks_like_desktop_rect(uia_rect):
        return uia_rect
    hwnd = _window_from_point(point, exclude_hwnd)
    return _window_rect(hwnd)


def _window_from_point(point: QPoint, exclude_hwnd: int | None = None) -> int | None:
    if win32gui is None or win32con is None:
        return None
    screen_point = (point.x(), point.y())
    hwnd = win32gui.WindowFromPoint(screen_point)
    if exclude_hwnd and _same_hwnd(hwnd, exclude_hwnd):
        hwnd = win32gui.GetWindow(hwnd, win32con.GW_HWNDNEXT)
        while hwnd:
            rect = _window_rect(hwnd)
            if rect and _rect_contains(rect, point):
                break
            hwnd = win32gui.GetWindow(hwnd, win32con.GW_HWNDNEXT)
    if not hwnd:
        return None
    return _deepest_child_at_point(hwnd, screen_point)


def _deepest_child_at_point(hwnd: int, screen_point: tuple[int, int]) -> int:
    if win32gui is None or win32con is None:
        return hwnd
    current = hwnd
    flags = win32con.CWP_SKIPINVISIBLE | win32con.CWP_SKIPDISABLED | win32con.CWP_SKIPTRANSPARENT
    while True:
        try:
            client_point = win32gui.ScreenToClient(current, screen_point)
            child = _real_child_window_from_point(current, client_point)
            if not child or _same_hwnd(child, current):
                child = win32gui.ChildWindowFromPointEx(current, client_point, flags)
        except Exception:
            return current
        if not child or _same_hwnd(child, current):
            return current
        current = child


def _real_child_window_from_point(hwnd: int, client_point: tuple[int, int]) -> int | None:
    try:
        ctypes.windll.user32.RealChildWindowFromPoint.restype = c_void_p
        ctypes.windll.user32.RealChildWindowFromPoint.argtypes = [c_void_p, wintypes.POINT]
        value = ctypes.windll.user32.RealChildWindowFromPoint(
            c_void_p(_handle_value(hwnd)),
            wintypes.POINT(client_point[0], client_point[1]),
        )
    except Exception:
        return None
    return int(value) if value else None


def _rect_contains(rect: CaptureRect, point: QPoint) -> bool:
    return (
        rect.left <= point.x() < rect.left + rect.width
        and rect.top <= point.y() < rect.top + rect.height
    )


def _same_hwnd(left: object, right: object) -> bool:
    return _handle_value(left) == _handle_value(right)


def _uia_rect_at_point(point: QPoint) -> CaptureRect | None:
    if sys.platform != "win32":
        return None
    global _UIA_AUTOMATION, _UIA_POINT
    try:
        if _UIA_AUTOMATION is None or _UIA_POINT is None:
            import comtypes.client

            comtypes.client.GetModule("UIAutomationCore.dll")
            from comtypes.gen.UIAutomationClient import CUIAutomation, IUIAutomation, tagPOINT

            _UIA_AUTOMATION = comtypes.client.CreateObject(CUIAutomation, interface=IUIAutomation)
            _UIA_POINT = tagPOINT
        element = _UIA_AUTOMATION.ElementFromPoint(_UIA_POINT(point.x(), point.y()))
        if not element:
            return None
        rect = element.CurrentBoundingRectangle
        width = int(rect.right - rect.left)
        height = int(rect.bottom - rect.top)
        if width <= 1 or height <= 1:
            return None
        return CaptureRect(int(rect.left), int(rect.top), width, height)
    except Exception:
        return None


def _looks_like_desktop_rect(rect: CaptureRect) -> bool:
    virtual = _virtual_capture_rect()
    width_delta = abs(rect.width - virtual.width)
    height_delta = abs(rect.height - virtual.height)
    return width_delta <= 4 and height_delta <= 4


def _virtual_capture_rect() -> CaptureRect:
    with mss.mss() as sct:
        monitor = sct.monitors[0]
        return CaptureRect(monitor["left"], monitor["top"], monitor["width"], monitor["height"])


def _current_cursor_image() -> tuple[Image.Image, int, int, int, int] | None:
    if sys.platform != "win32" or win32gui is None or win32api is None:
        return None
    windll.user32.GetDC.restype = HDC
    windll.user32.GetDC.argtypes = [c_void_p]
    windll.user32.ReleaseDC.argtypes = [c_void_p, HDC]
    windll.user32.GetIconInfo.argtypes = [c_void_p, POINTER(ICONINFO)]
    windll.user32.DrawIconEx.argtypes = [HDC, c_int, c_int, c_void_p, c_int, c_int, c_uint, c_void_p, c_uint]
    windll.gdi32.CreateCompatibleDC.restype = HDC
    windll.gdi32.CreateCompatibleDC.argtypes = [HDC]
    windll.gdi32.CreateDIBSection.restype = HBITMAP
    windll.gdi32.CreateDIBSection.argtypes = [HDC, POINTER(BITMAPINFO), c_uint, POINTER(c_void_p), c_void_p, DWORD]
    windll.gdi32.SelectObject.restype = HGDIOBJ
    windll.gdi32.SelectObject.argtypes = [HDC, HGDIOBJ]
    windll.gdi32.DeleteObject.argtypes = [HGDIOBJ]
    windll.gdi32.DeleteDC.argtypes = [HDC]
    flags, hcursor, (screen_x, screen_y) = win32gui.GetCursorInfo()
    if flags != CURSOR_SHOWING or not hcursor:
        return None

    icon_info = ICONINFO()
    if not windll.user32.GetIconInfo(c_void_p(_handle_value(hcursor)), byref(icon_info)):
        return None

    width = max(16, win32api.GetSystemMetrics(13))
    height = max(16, win32api.GetSystemMetrics(14))
    size = width * height * 4
    screen_dc = windll.user32.GetDC(c_void_p(0))
    memory_dc = windll.gdi32.CreateCompatibleDC(screen_dc)
    bits = c_void_p()
    bitmap_info = BITMAPINFO()
    bitmap_info.bmiHeader.biSize = sizeof(BITMAPINFOHEADER)
    bitmap_info.bmiHeader.biWidth = width
    bitmap_info.bmiHeader.biHeight = -height
    bitmap_info.bmiHeader.biPlanes = 1
    bitmap_info.bmiHeader.biBitCount = 32
    bitmap_info.bmiHeader.biCompression = BI_RGB
    bitmap = windll.gdi32.CreateDIBSection(
        screen_dc,
        byref(bitmap_info),
        DIB_RGB_COLORS,
        byref(bits),
        None,
        0,
    )
    if not bitmap:
        _delete_icon_bitmaps(icon_info)
        windll.gdi32.DeleteDC(memory_dc)
        windll.user32.ReleaseDC(c_void_p(0), screen_dc)
        return None

    old_bitmap = windll.gdi32.SelectObject(memory_dc, bitmap)
    memset(bits, 0, size)
    windll.user32.DrawIconEx(memory_dc, 0, 0, c_void_p(_handle_value(hcursor)), width, height, 0, None, DI_NORMAL)
    raw = string_at(bits, size)
    cursor_image = Image.frombuffer("RGBA", (width, height), raw, "raw", "BGRA", 0, 1).copy()

    windll.gdi32.SelectObject(memory_dc, old_bitmap)
    windll.gdi32.DeleteObject(bitmap)
    windll.gdi32.DeleteDC(memory_dc)
    windll.user32.ReleaseDC(c_void_p(0), screen_dc)
    _delete_icon_bitmaps(icon_info)
    return cursor_image, int(icon_info.xHotspot), int(icon_info.yHotspot), screen_x, screen_y


def _delete_icon_bitmaps(icon_info: ICONINFO) -> None:
    if icon_info.hbmMask:
        windll.gdi32.DeleteObject(icon_info.hbmMask)
    if icon_info.hbmColor:
        windll.gdi32.DeleteObject(icon_info.hbmColor)


def _dwm_window_rect(hwnd: int) -> CaptureRect | None:
    if sys.platform != "win32" or DWMWA_EXTENDED_FRAME_BOUNDS is None:
        return None
    rect = RECT()
    result = windll.dwmapi.DwmGetWindowAttribute(
        c_void_p(_handle_value(hwnd)),
        c_int(DWMWA_EXTENDED_FRAME_BOUNDS),
        byref(rect),
        c_int(sizeof(rect)),
    )
    if result != 0:
        return None
    width = rect.right - rect.left
    height = rect.bottom - rect.top
    if width <= 0 or height <= 0:
        return None
    return CaptureRect(rect.left, rect.top, width, height)


def _handle_value(handle: object) -> int:
    value = int(handle)
    bits = sizeof(c_void_p) * 8
    return value & ((1 << bits) - 1)


def _virtual_screen_rect() -> QRect:
    app = QGuiApplication.instance()
    if app is None:
        return QRect(0, 0, 0, 0)
    screens = app.screens()
    if not screens:
        return QRect(0, 0, 0, 0)
    rect = screens[0].geometry()
    for screen in screens[1:]:
        rect = rect.united(screen.geometry())
    return rect
