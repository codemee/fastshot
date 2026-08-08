from PIL import Image

from fastshot.capture import (
    CaptureRect,
    CaptureService,
    RegionSelector,
    WindowCaptureTarget,
    _FrozenDesktop,
)
from fastshot.settings import CaptureMode, CaptureSettings


def _image() -> Image.Image:
    return Image.new("RGB", (1, 1))


def test_repeat_region_reuses_the_previous_coordinates(monkeypatch):
    monkeypatch.setattr("fastshot.capture.sys.platform", "win32")
    service = CaptureService()
    selected = CaptureRect(12, 34, 200, 100)
    desktop = _FrozenDesktop(CaptureRect(0, 0, 400, 300), Image.new("RGB", (400, 300), "red"))
    captured = []
    monkeypatch.setattr(
        service,
        "_freeze_desktop",
        lambda _settings: (_ for _ in ()).throw(AssertionError("desktop was frozen twice")),
    )
    monkeypatch.setattr(service, "_select_region", lambda _frozen: selected)
    monkeypatch.setattr(
        service,
        "_capture_rect_for_mode",
        lambda mode, rect, _settings: captured.append((mode, rect)) or _image(),
    )

    first = service.capture(CaptureMode.REGION, CaptureSettings(), desktop)
    service.repeat(CaptureSettings())

    assert first.size == (200, 100)
    assert first.getpixel((0, 0)) == (255, 0, 0)
    assert captured == [(CaptureMode.REGION, selected)]


def test_repeat_selected_window_tracks_it_and_silently_stops_after_it_disappears(monkeypatch):
    service = CaptureService()
    original = CaptureRect(10, 20, 300, 200)
    moved = CaptureRect(100, 120, 300, 200)
    resolutions = iter((moved, None))
    target = WindowCaptureTarget(original, lambda: next(resolutions))
    captured = []
    monkeypatch.setattr(service, "_select_window_target", lambda: target)
    monkeypatch.setattr(
        service,
        "_capture_rect_for_mode",
        lambda mode, rect, _settings: captured.append((mode, rect)) or _image(),
    )

    service.capture(CaptureMode.WINDOW_UNDER_CURSOR, CaptureSettings())
    assert service.repeat(CaptureSettings()) is not None
    assert service.repeat(CaptureSettings()) is None

    assert captured == [
        (CaptureMode.WINDOW_UNDER_CURSOR, original),
        (CaptureMode.WINDOW_UNDER_CURSOR, moved),
    ]


def test_frozen_desktop_crop_uses_virtual_screen_coordinates():
    image = Image.new("RGB", (4, 3), "black")
    image.putpixel((2, 1), (10, 20, 30))
    frozen = _FrozenDesktop(CaptureRect(-2, -1, 4, 3), image)

    cropped = frozen.crop(CaptureRect(0, 0, 1, 1))

    assert cropped is not None
    assert cropped.size == (1, 1)
    assert cropped.getpixel((0, 0)) == (10, 20, 30)


def test_freeze_desktop_counts_down_before_capture_and_uses_freeze_time_cursor(monkeypatch):
    service = CaptureService()
    rect = CaptureRect(0, 0, 2, 2)
    image = Image.new("RGB", (2, 2))
    events = []
    monkeypatch.setattr(service, "_countdown", lambda seconds: events.append(("countdown", seconds)))
    monkeypatch.setattr(service, "_fullscreen_rect", lambda: events.append(("rect",)) or rect)
    monkeypatch.setattr(service, "_grab_rect", lambda value: events.append(("grab", value)) or image)
    monkeypatch.setattr(
        service,
        "_draw_cursor",
        lambda value, bounds: events.append(("cursor", value, bounds)),
    )

    frozen = service._freeze_desktop(CaptureSettings(include_cursor=True, delay_seconds=3))

    assert frozen == _FrozenDesktop(rect, image)
    assert events == [
        ("countdown", 3),
        ("rect",),
        ("grab", rect),
        ("cursor", image, rect),
    ]


def test_delayed_region_cancel_stops_before_freeze_and_selection(monkeypatch):
    monkeypatch.setattr("fastshot.capture.sys.platform", "win32")
    service = CaptureService()
    monkeypatch.setattr(service, "_countdown", lambda _seconds: True)
    monkeypatch.setattr(
        service,
        "_fullscreen_rect",
        lambda: (_ for _ in ()).throw(AssertionError("desktop should not be captured")),
    )
    monkeypatch.setattr(
        service,
        "_select_region",
        lambda _frozen: (_ for _ in ()).throw(AssertionError("selector should not open")),
    )

    image = service.capture(CaptureMode.REGION, CaptureSettings(delay_seconds=3))

    assert image is None
    assert service._last_capture is None


def test_region_selector_poll_cancels_without_keyboard_focus(qt_app, monkeypatch):
    selector = RegionSelector()
    monkeypatch.setattr("fastshot.capture._escape_pressed", lambda: True)

    selector.poll()

    assert selector.cancelled


def test_zero_delay_region_can_freeze_before_hotkey_returns(monkeypatch):
    monkeypatch.setattr("fastshot.capture.sys.platform", "win32")
    service = CaptureService()
    frozen = _FrozenDesktop(CaptureRect(0, 0, 1, 1), _image())
    monkeypatch.setattr(service, "_freeze_desktop", lambda _settings: frozen)

    prepared = service.prepare_frozen_selection(CaptureMode.REGION, CaptureSettings())
    delayed = service.prepare_frozen_selection(
        CaptureMode.REGION, CaptureSettings(delay_seconds=3)
    )
    fullscreen = service.prepare_frozen_selection(CaptureMode.FULLSCREEN, CaptureSettings())
    selected_window = service.prepare_frozen_selection(
        CaptureMode.WINDOW_UNDER_CURSOR, CaptureSettings()
    )

    assert prepared is frozen
    assert delayed is None
    assert fullscreen is None
    assert selected_window is None


def test_repeat_before_any_successful_capture_does_nothing():
    assert CaptureService().repeat(CaptureSettings()) is None
