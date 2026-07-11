from datetime import datetime

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
