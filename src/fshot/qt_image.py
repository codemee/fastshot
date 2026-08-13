from __future__ import annotations

from io import BytesIO

from PIL import Image
from PySide6.QtCore import QBuffer, QByteArray, QIODevice
from PySide6.QtGui import QImage, QPixmap


def pil_to_qimage(image: Image.Image) -> QImage:
    rgba = image.convert("RGBA")
    data = rgba.tobytes("raw", "RGBA")
    qimage = QImage(data, rgba.width, rgba.height, QImage.Format.Format_RGBA8888)
    return qimage.copy()


def qimage_to_pil(image: QImage) -> Image.Image:
    converted = image.convertToFormat(QImage.Format.Format_RGBA8888)
    width = converted.width()
    height = converted.height()
    ptr = converted.bits()
    data = bytes(ptr[: converted.sizeInBytes()])
    return Image.frombytes("RGBA", (width, height), data, "raw", "RGBA")


def qpixmap_to_png_bytes(pixmap: QPixmap) -> bytes:
    data = QByteArray()
    buffer = QBuffer(data)
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    pixmap.save(buffer, "PNG")
    return bytes(data)


def pil_to_png_bytes(image: Image.Image) -> bytes:
    stream = BytesIO()
    image.save(stream, format="PNG")
    return stream.getvalue()
