from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QKeySequence
from PySide6.QtWidgets import QScrollArea, QWidget

from fastshot.canvas import CANVAS_PADDING
from fastshot.main_window import _align_scrollbars_to_image


def test_image_scrollbars_exclude_canvas_padding(qt_app):
    area = QScrollArea()
    area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
    area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
    _align_scrollbars_to_image(area)
    area.resize(600, 400)
    area.show()
    qt_app.processEvents()

    vertical = area.verticalScrollBar()
    horizontal = area.horizontalScrollBar()
    padding = area.findChildren(QWidget, "imageScrollBarPadding")

    assert len(padding) == 5
    assert all(widget.autoFillBackground() for widget in padding)
    assert area.cornerWidget() in padding
    assert vertical.y() == CANVAS_PADDING
    assert vertical.height() == vertical.parentWidget().height() - CANVAS_PADDING * 2
    assert horizontal.x() == CANVAS_PADDING
    assert horizontal.width() == horizontal.parentWidget().width() - CANVAS_PADDING * 2


def test_saved_tab_can_rename_file_inline(qt_app, tmp_path):
    from fastshot.main_window import EditorWindow

    source = tmp_path / "old-name.png"
    source.write_bytes(b"image")
    window = EditorWindow()
    image = QImage(6, 5, QImage.Format.Format_ARGB32)
    window._add_image(image, source.name, path=source, dirty=False)

    window.rename_current()

    assert window._tab_name_editor.isVisible()
    assert window._tab_name_editor.text() == "old-name"
    window._tab_name_editor.setText("new-name")
    window._commit_tab_rename()

    target = tmp_path / "new-name.png"
    assert target.exists()
    assert not source.exists()
    assert window.documents[0].path == target
    assert window.tabs.tabText(0) == "new-name"


def test_unsaved_tab_cannot_be_renamed(qt_app):
    from fastshot.main_window import EditorWindow

    window = EditorWindow()
    window._add_image(QImage(6, 5, QImage.Format.Format_ARGB32), "new-shot")

    assert not window.rename_action.isEnabled()
    window.rename_current()
    assert not window._tab_name_editor.isVisible()


def test_rename_preserves_dirty_state_and_does_not_replace_existing_file(
    qt_app, tmp_path, monkeypatch
):
    import fastshot.main_window as main_window

    source = tmp_path / "old.png"
    existing = tmp_path / "existing.png"
    source.write_bytes(b"old")
    existing.write_bytes(b"existing")
    warnings = []
    monkeypatch.setattr(main_window.QMessageBox, "warning", lambda *args: warnings.append(args))
    window = main_window.EditorWindow()
    window._add_image(
        QImage(6, 5, QImage.Format.Format_ARGB32), source.name, path=source, dirty=True
    )

    window.rename_current()
    window._tab_name_editor.setText("existing")
    window._commit_tab_rename()

    assert source.exists()
    assert existing.read_bytes() == b"existing"
    assert window.documents[0].path == source
    assert window.documents[0].is_dirty
    assert warnings


def test_rename_shortcut_matches_platform_file_manager(qt_app, monkeypatch):
    import fastshot.main_window as main_window

    monkeypatch.setattr(main_window.sys, "platform", "darwin")
    mac_window = main_window.EditorWindow()
    assert mac_window.rename_action.shortcut() == QKeySequence("Return")

    monkeypatch.setattr(main_window.sys, "platform", "win32")
    windows_window = main_window.EditorWindow()
    assert windows_window.rename_action.shortcut() == QKeySequence("F2")
