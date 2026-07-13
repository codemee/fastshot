from PySide6.QtCore import Qt
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
