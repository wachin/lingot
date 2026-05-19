from __future__ import annotations

from PyQt6.QtCore import QPointF, Qt
from PyQt6.QtGui import QColor, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import QWidget


class SpectrumWidget(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.samples: list[float] = []
        self.setMinimumSize(320, 160)

    def set_samples(self, samples: list[float]) -> None:
        self.samples = samples
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt override name
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect().adjusted(10, 10, -10, -10)
        painter.fillRect(self.rect(), QColor(8, 36, 16))

        painter.setPen(QPen(QColor(96, 128, 100), 1))
        for index in range(5):
            y = rect.top() + rect.height() * index / 4
            painter.drawLine(rect.left(), int(y), rect.right(), int(y))

        if not self.samples:
            painter.setPen(QColor(180, 200, 184))
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, "spectrum")
            return

        max_value = max(max(self.samples), 1.0)
        step = max(1, len(self.samples) // max(rect.width(), 1))
        points = self.samples[::step]
        path = QPainterPath(QPointF(rect.left(), rect.bottom()))

        for index, value in enumerate(points):
            x = rect.left() + rect.width() * index / max(len(points) - 1, 1)
            y = rect.bottom() - rect.height() * min(max(value / max_value, 0.0), 1.0)
            path.lineTo(QPointF(x, y))

        path.lineTo(QPointF(rect.right(), rect.bottom()))
        path.closeSubpath()
        painter.fillPath(path, QColor(35, 220, 80, 160))
        painter.setPen(QPen(QColor(130, 255, 150), 1))
        painter.drawPath(path)
