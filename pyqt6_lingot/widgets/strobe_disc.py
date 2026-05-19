from __future__ import annotations

import math

from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QColor, QPainter, QPen
from PyQt6.QtWidgets import QWidget


class StrobeDiscWidget(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.error_cents = math.nan
        self.phase = 0.0
        self.setMinimumSize(280, 180)

        self.timer = QTimer(self)
        self.timer.setInterval(33)
        self.timer.timeout.connect(self._tick)
        self.timer.start()

    def set_error(self, error_cents: float) -> None:
        self.error_cents = error_cents

    def _tick(self) -> None:
        if not math.isnan(self.error_cents):
            self.phase += max(-20.0, min(20.0, self.error_cents)) * 0.01
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt override name
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor(14, 18, 22))

        rect = self.rect().adjusted(24, 16, -24, -16)
        size = min(rect.width(), rect.height())
        cx = rect.center().x()
        cy = rect.center().y()
        radius = size / 2

        painter.setPen(QPen(QColor(200, 220, 210), 2))
        painter.drawEllipse(int(cx - radius), int(cy - radius), int(radius * 2), int(radius * 2))

        for index in range(24):
            angle = self.phase + index * math.tau / 24
            if index % 2 == 0:
                painter.setPen(QPen(QColor(230, 238, 232), 4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            else:
                painter.setPen(QPen(QColor(80, 100, 95), 3, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            x1 = cx + radius * 0.25 * math.cos(angle)
            y1 = cy + radius * 0.25 * math.sin(angle)
            x2 = cx + radius * 0.92 * math.cos(angle)
            y2 = cy + radius * 0.92 * math.sin(angle)
            painter.drawLine(int(x1), int(y1), int(x2), int(y2))
