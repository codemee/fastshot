from fshot.icons import camera_icon, tool_icon, tray_icon


def _opaque_rect(icon, size):
    image = icon.pixmap(size, size).toImage()
    opaque = [
        (x, y)
        for y in range(image.height())
        for x in range(image.width())
        if image.pixelColor(x, y).alpha() > 0
    ]
    left = min(x for x, _y in opaque)
    right = max(x for x, _y in opaque)
    top = min(y for _x, y in opaque)
    bottom = max(y for _x, y in opaque)
    return left, top, right, bottom


def _opaque_bounds(icon, size):
    left, top, right, bottom = _opaque_rect(icon, size)
    return right - left + 1, bottom - top + 1


def test_window_icon_fills_the_taskbar_slot(qt_app):
    width, height = _opaque_bounds(camera_icon(), 32)

    assert width >= 27
    assert height >= 25


def test_tray_icon_fills_the_system_tray_slot(qt_app):
    width, height = _opaque_bounds(tray_icon(), 16)

    assert width >= 14
    assert height >= 13


def test_macos_tray_icon_fills_the_menu_bar_slot(qt_app):
    width, height = _opaque_bounds(tray_icon(macos=True), 16)

    assert width >= 15
    assert height >= 15


def test_pen_tool_icon_is_vertically_centered(qt_app):
    _left, top, _right, bottom = _opaque_rect(tool_icon("pen"), 32)

    assert abs(((top + bottom) / 2) - 15.5) <= 1.5
