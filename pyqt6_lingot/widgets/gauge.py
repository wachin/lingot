from __future__ import annotations

import math

from PyQt6.QtCore import QPointF, Qt
from PyQt6.QtGui import QColor, QPainter, QPen
from PyQt6.QtWidgets import QWidget


class GaugeWidget(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.error_cents = math.nan
        self.setMinimumSize(280, 180)

    def set_error(self, error_cents: float) -> None:
        self.error_cents = error_cents
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt override name
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect().adjusted(12, 12, -12, -12)

        painter.fillRect(self.rect(), QColor(15, 28, 24))
        painter.setPen(QPen(QColor(98, 132, 120), 2))
        painter.drawArc(rect, 20 * 16, 140 * 16)

        center = QPointF(rect.center().x(), rect.bottom())
        radius = min(rect.width() * 0.48, rect.height() * 0.94)
        for cents in range(-50, 51, 10):
            angle = math.radians(90 - cents * 1.4)
            outer = QPointF(center.x() + radius * math.cos(angle), center.y() - radius * math.sin(angle))
            inner_radius = radius - (16 if cents % 50 == 0 else 9)
            inner = QPointF(
                center.x() + inner_radius * math.cos(angle),
                center.y() - inner_radius * math.sin(angle),
            )
            painter.drawLine(inner, outer)

        cents = 0.0 if math.isnan(self.error_cents) else max(-50.0, min(50.0, self.error_cents))
        angle = math.radians(90 - cents * 1.4)
        needle = QPointF(center.x() + (radius - 22) * math.cos(angle), center.y() - (radius - 22) * math.sin(angle))
        painter.setPen(QPen(QColor(246, 88, 88), 4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawLine(center, needle)

        painter.setPen(QColor(210, 230, 220))
        painter.drawText(rect, Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter, "cents")
