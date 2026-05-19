from __future__ import annotations

import math
from pathlib import Path

from PyQt6.QtCore import QPointF, QRectF, QTimer
from PyQt6.QtGui import QColor, QImage, QPainter, QPainterPath, QPen, QPixmap
from PyQt6.QtWidgets import QWidget


class StrobeDiscWidget(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.error_cents = math.nan
        self.phase = 0.0
        self.computation_rate = 60.0
        self.strobe_image = self._load_strobe_image()
        self.setMinimumSize(280, 180)

        self.timer = QTimer(self)
        self.timer.setInterval(33)
        self.timer.timeout.connect(self._tick)
        self.timer.start()

    def set_error(self, error_cents: float) -> None:
        self.error_cents = error_cents

    def set_computation_rate(self, computation_rate: float) -> None:
        self.computation_rate = max(1.0, computation_rate)

    def _tick(self) -> None:
        if not math.isnan(self.error_cents):
            self.phase += 0.1 * self.error_cents / self.computation_rate
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt override name
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor(255, 255, 255))

        image = self.strobe_image
        if image.isNull():
            image = self._fallback_strobe_image()

        area_width = max(1, self.width())
        area_height = max(1, self.height())
        scale = 1.5 * (area_width + area_height) / (image.width() + image.height())
        scale += 0.3 * area_height / area_width

        painter.translate(area_width / 2.0, 1.5 * area_height)
        painter.rotate(math.degrees(self.phase))
        painter.scale(scale, scale)
        painter.translate(-image.width() / 2.0 + 1.0, -image.height() / 2.0 + 1.0)
        painter.drawPixmap(0, 0, image)

    def _load_strobe_image(self) -> QPixmap:
        candidates = [
            Path(__file__).resolve().parents[2] / "src" / "lingot-strobe.png",
            Path(__file__).resolve().parents[1] / "assets" / "lingot-strobe.png",
        ]
        for candidate in candidates:
            if candidate.exists():
                pixmap = QPixmap(str(candidate))
                if not pixmap.isNull():
                    return pixmap
        return QPixmap()

    def _fallback_strobe_image(self) -> QPixmap:
        size = 1024
        image = QImage(size, size, QImage.Format.Format_ARGB32)
        image.fill(QColor(255, 255, 255))
        painter = QPainter(image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        center = QPointF(size / 2.0, size / 2.0)
        radius = size * 0.48

        painter.setPen(QPen(QColor(32, 32, 32), 2))
        painter.drawEllipse(QRectF(center.x() - radius, center.y() - radius, 2 * radius, 2 * radius))

        for band in range(7):
            inner = radius * (0.12 + band * 0.12)
            outer = radius * (0.18 + band * 0.12)
            sectors = 18 + band * 6
            for sector in range(sectors):
                if sector % 2:
                    continue
                start = sector * math.tau / sectors
                end = (sector + 0.5) * math.tau / sectors
                path = QPainterPath()
                path.moveTo(center + QPointF(inner * math.cos(start), inner * math.sin(start)))
                path.lineTo(center + QPointF(outer * math.cos(start), outer * math.sin(start)))
                steps = 6
                for step in range(1, steps + 1):
                    angle = start + (end - start) * step / steps
                    path.lineTo(center + QPointF(outer * math.cos(angle), outer * math.sin(angle)))
                path.lineTo(center + QPointF(inner * math.cos(end), inner * math.sin(end)))
                for step in range(steps - 1, -1, -1):
                    angle = start + (end - start) * step / steps
                    path.lineTo(center + QPointF(inner * math.cos(angle), inner * math.sin(angle)))
                path.closeSubpath()
                painter.fillPath(path, QColor(20, 20, 20))

        painter.end()
        return QPixmap.fromImage(image)
