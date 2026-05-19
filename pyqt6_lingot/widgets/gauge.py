from __future__ import annotations

import math

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import QWidget


class GaugeWidget(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.error_cents = math.nan
        self.gauge_range = 50.0
        self.setMinimumSize(280, 180)

    def set_error(self, error_cents: float) -> None:
        self.error_cents = error_cents
        self.update()

    def set_range(self, gauge_range: float) -> None:
        self.gauge_range = max(1.0, gauge_range)
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt override name
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor(255, 255, 255))

        width = max(1, self.width())
        raw_height = max(1, self.height())
        height = raw_height
        center = QPointF(width / 2.0, height * 0.94)
        if width < 1.6 * height:
            height = width / 1.6
            center.setY(0.5 * (raw_height - height) + height * 0.94)

        overture = math.radians(65.0)
        self._draw_colored_arc(painter, center, height * 0.48, height * 0.07, -overture, overture, QColor(221, 170, 170))
        self._draw_colored_arc(painter, center, height * 0.48, height * 0.07, -0.1 * overture, 0.1 * overture, QColor(153, 221, 153))
        self._draw_colored_arc(painter, center, height * 0.75, height * 0.025, -1.05 * overture, 1.05 * overture, QColor(51, 51, 85))
        self._draw_colored_arc(painter, center, height * 0.78, height * 0.025, -1.05 * overture, 1.05 * overture, QColor(85, 85, 51))

        self._draw_ticks(painter, center, height, overture)
        self._draw_labels(painter, center, height, overture)
        self._draw_needle(painter, center, height, overture)

    def _arc_rect(self, center: QPointF, radius: float) -> QRectF:
        return QRectF(center.x() - radius, center.y() - radius, 2 * radius, 2 * radius)

    def _qt_arc_angle(self, angle: float) -> int:
        return int((90.0 - math.degrees(angle)) * 16)

    def _draw_colored_arc(
        self,
        painter: QPainter,
        center: QPointF,
        radius: float,
        stroke: float,
        start_angle: float,
        end_angle: float,
        color: QColor,
    ) -> None:
        painter.setPen(QPen(color, max(1.0, stroke), Qt.PenStyle.SolidLine, Qt.PenCapStyle.FlatCap))
        painter.drawArc(
            self._arc_rect(center, radius),
            self._qt_arc_angle(start_angle),
            int(-math.degrees(end_angle - start_angle) * 16),
        )

    def _point_on_gauge(self, center: QPointF, radius: float, angle: float) -> QPointF:
        return QPointF(
            center.x() + radius * math.sin(angle),
            center.y() - radius * math.cos(angle),
        )

    def _draw_radial_line(
        self,
        painter: QPainter,
        center: QPointF,
        radius1: float,
        radius2: float,
        angle: float,
    ) -> None:
        painter.drawLine(
            self._point_on_gauge(center, radius1, angle),
            self._point_on_gauge(center, radius2, angle),
        )

    def _division_size(self) -> tuple[float, float]:
        cents_per_minor = self.gauge_range / 20.0
        base = 10.0 ** math.floor(math.log10(cents_per_minor))
        normalized = cents_per_minor / base
        if normalized >= 6.0:
            normalized = 10.0
        elif normalized >= 2.5:
            normalized = 5.0
        elif normalized >= 1.2:
            normalized = 2.0
        else:
            normalized = 1.0
        cents_per_minor = normalized * base
        return cents_per_minor, cents_per_minor * 5.0

    def _draw_ticks(self, painter: QPainter, center: QPointF, height: float, overture: float) -> None:
        cents_per_minor, cents_per_major = self._division_size()
        cents_radius = height * 0.75

        painter.setPen(QPen(QColor(51, 51, 85), max(1.0, height * 0.01), Qt.PenStyle.SolidLine, Qt.PenCapStyle.FlatCap))
        max_index = int(math.floor(0.5 * self.gauge_range / cents_per_minor))
        angle_step = 2.0 * overture * cents_per_minor / self.gauge_range
        for index in range(-max_index, max_index + 1):
            self._draw_radial_line(painter, center, cents_radius - height * 0.03, cents_radius, index * angle_step)

        painter.setPen(QPen(QColor(51, 51, 85), max(1.0, height * 0.03), Qt.PenStyle.SolidLine, Qt.PenCapStyle.FlatCap))
        max_index = int(math.floor(0.5 * self.gauge_range / cents_per_major))
        angle_step = 2.0 * overture * cents_per_major / self.gauge_range
        for index in range(-max_index, max_index + 1):
            self._draw_radial_line(painter, center, cents_radius - height * 0.04, cents_radius, index * angle_step)

        painter.setPen(QPen(QColor(85, 85, 51), max(1.0, height * 0.03), Qt.PenStyle.SolidLine, Qt.PenCapStyle.FlatCap))
        self._draw_radial_line(painter, center, height * 0.82, height * 0.78, 0.0)

    def _draw_labels(self, painter: QPainter, center: QPointF, height: float, overture: float) -> None:
        _minor, cents_per_major = self._division_size()
        max_index = int(math.floor(0.5 * self.gauge_range / cents_per_major))
        angle_step = 2.0 * overture * cents_per_major / self.gauge_range
        painter.setPen(QColor(0, 0, 0))
        font = painter.font()
        font.setPointSizeF(max(7.0, height * 0.055))
        painter.setFont(font)

        label_rect = QRectF(center.x() - height * 0.18, center.y() - height * 0.64, height * 0.36, height * 0.08)
        painter.drawText(label_rect, Qt.AlignmentFlag.AlignCenter, "cent")

        radius = height * 0.62
        metrics = painter.fontMetrics()
        for index in range(-max_index, max_index + 1):
            cents = int(index * cents_per_major)
            text = f"+{cents}" if cents > 0 else str(cents)
            angle = index * angle_step
            point = self._point_on_gauge(center, radius, angle)
            text_rect = QRectF(
                point.x() - metrics.horizontalAdvance(text) / 2 - 4,
                point.y() - metrics.height() / 2,
                metrics.horizontalAdvance(text) + 8,
                metrics.height(),
            )
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, text)

    def _draw_needle(self, painter: QPainter, center: QPointF, height: float, overture: float) -> None:
        cents = 0.0 if math.isnan(self.error_cents) else max(-self.gauge_range / 2.0, min(self.gauge_range / 2.0, self.error_cents))
        angle = 2.0 * (cents / self.gauge_range) * overture
        needle_length = height * 0.85
        back_length = height * 0.08
        center_radius = height * 0.045

        shadow_center = QPointF(center.x() + height * 0.015, center.y() + height * 0.01)
        painter.setPen(QPen(QColor(0, 0, 0, 125), max(1.0, height * 0.012), Qt.PenStyle.SolidLine, Qt.PenCapStyle.FlatCap))
        self._draw_radial_line(painter, shadow_center, -back_length, -center_radius, angle)
        self._draw_radial_line(painter, shadow_center, center_radius, needle_length, angle)
        painter.setBrush(QColor(0, 0, 0, 125))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(shadow_center, center_radius, center_radius)

        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(QColor(170, 51, 51), max(1.0, height * 0.012), Qt.PenStyle.SolidLine, Qt.PenCapStyle.FlatCap))
        self._draw_radial_line(painter, center, -back_length, needle_length, angle)
        painter.setBrush(QColor(170, 51, 51))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(center, center_radius, center_radius)
