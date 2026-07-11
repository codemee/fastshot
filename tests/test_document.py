from datetime import datetime

from PIL import Image
from PySide6.QtCore import QMimeData, QUrl
from PySide6.QtGui import QImage

from fastshot.document import ShotDocument, make_tab_title


def test_make_tab_title_format():
    assert make_tab_title(datetime(2026, 7, 9, 5, 6, 7)) == "26-07-09-050607"


def test_dirty_state_transitions():
    doc = ShotDocument(title="26-07-09-050607", image=None)
    assert doc.is_unsaved
    assert doc.is_dirty
    assert doc.can_save
    assert doc.display_title == "26-07-09-050607"

    doc.mark_saved("C:/tmp/example.png")
    assert not doc.is_unsaved
    assert not doc.is_dirty
    assert not doc.can_save

    doc.mark_dirty()
    assert doc.can_save


def test_reindex_after_middle_tab_close(qt_app):
    from fastshot.main_window import EditorWindow

    window = EditorWindow()
    docs = {
        0: ShotDocument("first", None),
        1: ShotDocument("second", None),
        2: ShotDocument("third", None),
    }
    window.documents = docs

    window._reindex_documents(1)

    assert window.documents[0].title == "first"
    assert window.documents[1].title == "third"
    assert 2 not in window.documents


def test_windows_dirty_marker_is_left_of_tab_title(qt_app, monkeypatch):
    from PySide6.QtWidgets import QTabBar

    import fastshot.main_window as main_window

    monkeypatch.setattr(main_window.sys, "platform", "win32")
    window = main_window.EditorWindow()
    index = window.tabs.addTab(main_window.QWidget(), "example")

    status = window._ensure_tab_status_widget(index)

    assert window.tabs.tabBar().tabButton(index, QTabBar.ButtonPosition.LeftSide) is status
    assert status.layout().contentsMargins().right() == 6
    assert window.tabs.tabBar().tabButton(index, QTabBar.ButtonPosition.RightSide) is not None


def test_open_image_uses_supplied_filename_as_tab_title(qt_app, tmp_path):
    from fastshot.main_window import EditorWindow

    path = tmp_path / "sample-image.png"
    Image.new("RGB", (12, 8), "red").save(path)
    window = EditorWindow()

    assert window._open_image_path(path, path.name, remember_path=True)
    assert window.tabs.tabText(0) == "sample-image.png"
    assert window.documents[0].path == path
    assert not window.documents[0].is_dirty
    assert not window.save_action.isEnabled()


def test_mime_image_paths_accepts_local_files(tmp_path):
    from fastshot.main_window import EditorWindow

    path = tmp_path / "drop.png"
    Image.new("RGB", (4, 4), "blue").save(path)
    mime = QMimeData()
    mime.setUrls([QUrl.fromLocalFile(str(path))])

    assert EditorWindow._image_paths_from_mime(mime) == [path]


def test_paste_image_uses_screenshot_title(qt_app):
    from fastshot.main_window import EditorWindow

    qt_app.clipboard().setImage(QImage(6, 5, QImage.Format.Format_ARGB32))
    window = EditorWindow()
    window.paste_image()

    assert window.tabs.count() == 1
    assert len(window.tabs.tabText(0)) == len("26-07-09-050607")
