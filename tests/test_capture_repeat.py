from PIL import Image

from fastshot.capture import CaptureRect, CaptureService, WindowCaptureTarget
from fastshot.settings import CaptureMode, CaptureSettings


def _image() -> Image.Image:
    return Image.new("RGB", (1, 1))


def test_repeat_region_reuses_the_previous_coordinates(monkeypatch):
    service = CaptureService()
    selected = CaptureRect(12, 34, 200, 100)
    captured = []
    monkeypatch.setattr(service, "_rect_for_mode", lambda _mode: selected)
    monkeypatch.setattr(
        service,
        "_capture_rect_for_mode",
        lambda mode, rect, _settings: captured.append((mode, rect)) or _image(),
    )

    service.capture(CaptureMode.REGION, CaptureSettings())
    monkeypatch.setattr(
        service,
        "_rect_for_mode",
        lambda _mode: CaptureRect(900, 900, 10, 10),
    )
    service.repeat(CaptureSettings())

    assert captured == [
        (CaptureMode.REGION, selected),
        (CaptureMode.REGION, selected),
    ]


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


def test_repeat_before_any_successful_capture_does_nothing():
    assert CaptureService().repeat(CaptureSettings()) is None
