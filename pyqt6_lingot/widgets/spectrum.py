from __future__ import annotations

import math

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import QWidget


class SpectrumWidget(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.samples: list[float] = []
        self.max_frequency = 22050.0
        self.frequency = 0.0
        self.target_frequency = 0.0
        self.noise_threshold = 10.0
        self.min_db = 0.0
        self.max_db = 52.0
        self.setMinimumSize(320, 160)

    def set_samples(self, samples: list[float]) -> None:
        self.samples = samples
        self.update()

    def set_frequency(self, frequency: float) -> None:
        self.frequency = max(0.0, frequency)
        self.update()

    def set_target_frequency(self, frequency: float) -> None:
        self.target_frequency = max(0.0, frequency)
        self.update()

    def set_scale(self, max_frequency: float, noise_threshold: float) -> None:
        self.max_frequency = max(1.0, max_frequency)
        self.noise_threshold = noise_threshold
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt override name
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        metrics = painter.fontMetrics()
        left_margin = max(28.0, metrics.horizontalAdvance(f"{int(self.max_db)}") * 1.7)
        bottom_margin = max(20.0, metrics.height() * 1.6)
        top_margin = bottom_margin
        right_margin = min(0.03 * self.width(), 0.8 * left_margin)
        plot = QRectF(
            left_margin,
            top_margin,
            max(1.0, self.width() - left_margin - right_margin),
            max(1.0, self.height() - top_margin - bottom_margin),
        )

        painter.fillRect(self.rect(), QColor(15, 51, 15))
        self._draw_grid(painter, plot)

        if not self.samples:
            painter.setPen(QColor(180, 200, 184))
            painter.drawText(plot, Qt.AlignmentFlag.AlignCenter, "spectrum")
            return

        self._draw_spectrum(painter, plot)
        self._draw_noise_threshold(painter, plot)
        self._draw_frequency_markers(painter, plot)

    def _format_frequency(self, frequency_hz: float) -> str:
        if frequency_hz == 0.0:
            return "0 Hz"
        frequency_khz = frequency_hz / 1000.0
        if frequency_khz >= 1.0:
            if abs(frequency_khz - round(frequency_khz)) < 1e-9:
                return f"{frequency_khz:.0f} kHz"
            return f"{frequency_khz:.1f} kHz"
        return f"{frequency_hz:.0f} Hz"

    def _value_to_y(self, value: float, plot: QRectF) -> float:
        bounded = max(self.min_db, min(self.max_db, value)) - self.min_db
        density = plot.height() / (self.max_db - self.min_db)
        return plot.bottom() - bounded * density

    def _frequency_to_x(self, frequency: float, plot: QRectF) -> float:
        return plot.left() + plot.width() * max(0.0, min(self.max_frequency, frequency)) / self.max_frequency

    def _frequency_grid_step(self, plot: QRectF) -> float:
        scales_khz = (0.01, 0.05, 0.1, 0.2, 0.5, 1.0, 2.0, 4.0, 11.0, 22.0)
        minimum_width = max(50.0, 1.5 * self.fontMetrics().horizontalAdvance("000 Hz"))
        for scale_khz in scales_khz:
            if 1000.0 * scale_khz * plot.width() / self.max_frequency > minimum_width:
                return 1000.0 * scale_khz
        return 22000.0

    def _db_grid_step(self, plot: QRectF) -> int:
        density = plot.height() / (self.max_db - self.min_db)
        minimum_height = max(24.0, 3.0 * self.fontMetrics().height())
        for scale in (5, 10, 20, 25, 50, 75, 100):
            if scale * density > minimum_height:
                return scale
        return 100

    def _draw_grid(self, painter: QPainter, plot: QRectF) -> None:
        painter.setPen(QPen(QColor(143, 143, 143), 1))
        painter.drawLine(QPointF(plot.left(), plot.bottom()), QPointF(plot.right(), plot.bottom()))

        font = painter.font()
        font.setPointSizeF(max(7.0, min(11.0, 8.0 + self.height() / 90.0)))
        painter.setFont(font)
        metrics = painter.fontMetrics()

        frequency_step = self._frequency_grid_step(plot)
        frequency = 0.0
        while frequency <= self.max_frequency + 1e-9:
            x = self._frequency_to_x(frequency, plot)
            painter.drawLine(QPointF(x, plot.top()), QPointF(x, plot.bottom() + 3))
            label = self._format_frequency(frequency)
            rect = QRectF(
                x - metrics.horizontalAdvance(label) / 2 + 6,
                plot.bottom() + 3,
                metrics.horizontalAdvance(label) + 8,
                metrics.height(),
            )
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, label)
            frequency += frequency_step

        painter.drawText(
            QRectF(0, 0, plot.left(), plot.top()),
            Qt.AlignmentFlag.AlignCenter,
            "dB",
        )

        db_step = self._db_grid_step(plot)
        first = int(math.ceil(self.min_db / db_step))
        last = int(math.ceil(self.max_db / db_step))
        for index in range(first, last + 1):
            value = index * db_step
            if value < self.min_db or value > self.max_db:
                continue
            y = self._value_to_y(value, plot)
            label = str(value)
            painter.drawText(
                QRectF(0, y - metrics.height() / 2, plot.left() * 0.9, metrics.height()),
                Qt.AlignmentFlag.AlignCenter,
                label,
            )
            painter.drawLine(QPointF(plot.left() - 3, y), QPointF(plot.right() + 3, y))

    def _draw_spectrum(self, painter: QPainter, plot: QRectF) -> None:
        points = self.samples
        if len(points) < 2:
            return
        step = max(1, len(points) // max(int(plot.width()), 1))
        points = points[::step]

        path = QPainterPath(QPointF(plot.left(), plot.bottom()))
        for index, value in enumerate(points):
            x = plot.left() + plot.width() * index / max(len(points) - 1, 1)
            y = self._value_to_y(value, plot)
            path.lineTo(QPointF(x, y))
        path.lineTo(QPointF(plot.right(), plot.bottom()))
        path.closeSubpath()

        painter.save()
        painter.setClipRect(plot.adjusted(1, 1, -1, -1))
        painter.fillPath(path, QColor(33, 255, 33, 185))
        painter.setPen(QPen(QColor(33, 255, 33), 1))
        painter.drawPath(path)
        painter.restore()

    def _draw_noise_threshold(self, painter: QPainter, plot: QRectF) -> None:
        y = self._value_to_y(self.noise_threshold, plot)
        pen = QPen(QColor(255, 255, 50), 1)
        pen.setDashPattern([5.0, 5.0])
        painter.setPen(pen)
        painter.drawLine(QPointF(plot.left(), y), QPointF(plot.right(), y))

    def _draw_frequency_markers(self, painter: QPainter, plot: QRectF) -> None:
        if self.target_frequency > 0.0:
            x = self._frequency_to_x(self.target_frequency, plot)
            painter.setPen(QPen(QColor(59, 212, 255), 1, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            painter.drawLine(QPointF(x, plot.bottom()), QPointF(x, plot.top()))

        if self.frequency > 0.0:
            x = self._frequency_to_x(self.frequency, plot)
            painter.setPen(QPen(QColor(255, 33, 33), 2, Qt.PenStyle.DashLine, Qt.PenCapStyle.RoundCap))
            painter.drawLine(QPointF(x, plot.bottom()), QPointF(x, plot.top()))
