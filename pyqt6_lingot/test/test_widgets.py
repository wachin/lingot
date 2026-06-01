"""Visual smoke tests for the custom drawing widgets.

These tests verify that the gauge, spectrum, and strobe disc widgets
can paint nonblank frames without crashing.  They use the offscreen
Qt platform so no display server is required.
"""
from __future__ import annotations

import math
import unittest

from PyQt6.QtCore import QRect, Qt
from PyQt6.QtGui import QImage, QPainter
from PyQt6.QtWidgets import QApplication

from pyqt6_lingot.widgets.gauge import GaugeWidget
from pyqt6_lingot.widgets.spectrum import SpectrumWidget
from pyqt6_lingot.widgets.strobe_disc import StrobeDiscWidget

# Ensure a QApplication exists before any widget is created.
_app = QApplication.instance() or QApplication([])


def _paint_to_image(widget: QWidget, width: int = 320, height: int = 200) -> QImage:
    """Force a paint event by rendering the widget into a QImage."""
    widget.resize(width, height)
    widget.show()
    image = QImage(width, height, QImage.Format.Format_ARGB32)
    image.fill(0)
    painter = QPainter(image)
    widget.render(painter)
    painter.end()
    return image


def _image_is_nonblank(image: QImage) -> bool:
    """Return True if the image contains any non-zero pixel."""
    for y in range(image.height()):
        for x in range(image.width()):
            if image.pixelColor(x, x % image.width()).alpha() > 0:
                return True
            if image.pixel(x, y) != 0:
                return True
    return False


class _QWidget:
    pass


class TestGaugeWidgetSmoke(unittest.TestCase):
    """Smoke tests for GaugeWidget."""

    def test_paint_default(self) -> None:
        widget = GaugeWidget()
        image = _paint_to_image(widget)
        self.assertFalse(image.isNull())
        # Widget should paint something (not fully transparent).
        self.assertTrue(_image_is_nonblank(image))

    def test_paint_with_error(self) -> None:
        widget = GaugeWidget()
        widget.set_error(-15.5)
        image = _paint_to_image(widget)
        self.assertFalse(image.isNull())
        self.assertTrue(_image_is_nonblank(image))

    def test_paint_with_positive_error(self) -> None:
        widget = GaugeWidget()
        widget.set_error(25.0)
        image = _paint_to_image(widget)
        self.assertFalse(image.isNull())
        self.assertTrue(_image_is_nonblank(image))

    def test_paint_nan_error(self) -> None:
        widget = GaugeWidget()
        widget.set_error(float("nan"))
        image = _paint_to_image(widget)
        self.assertFalse(image.isNull())
        self.assertTrue(_image_is_nonblank(image))

    def test_set_range(self) -> None:
        widget = GaugeWidget()
        widget.set_range(100.0)
        widget.set_error(50.0)
        image = _paint_to_image(widget)
        self.assertFalse(image.isNull())
        self.assertTrue(_image_is_nonblank(image))


class TestSpectrumWidgetSmoke(unittest.TestCase):
    """Smoke tests for SpectrumWidget."""

    def test_paint_empty(self) -> None:
        widget = SpectrumWidget()
        image = _paint_to_image(widget)
        self.assertFalse(image.isNull())
        self.assertTrue(_image_is_nonblank(image))

    def test_paint_with_samples(self) -> None:
        widget = SpectrumWidget()
        samples = [float(i) for i in range(256)]
        widget.set_samples(samples)
        widget.set_frequency(440.0)
        widget.set_target_frequency(440.0)
        image = _paint_to_image(widget)
        self.assertFalse(image.isNull())
        self.assertTrue(_image_is_nonblank(image))

    def test_paint_with_target_only(self) -> None:
        widget = SpectrumWidget()
        samples = [math.sin(i * 0.1) * 20 + 20 for i in range(512)]
        widget.set_samples(samples)
        widget.set_target_frequency(261.63)
        image = _paint_to_image(widget)
        self.assertFalse(image.isNull())
        self.assertTrue(_image_is_nonblank(image))

    def test_set_scale(self) -> None:
        widget = SpectrumWidget()
        widget.set_scale(8000.0, 15.0)
        samples = [10.0] * 256
        widget.set_samples(samples)
        image = _paint_to_image(widget)
        self.assertFalse(image.isNull())
        self.assertTrue(_image_is_nonblank(image))


class TestStrobeDiscWidgetSmoke(unittest.TestCase):
    """Smoke tests for StrobeDiscWidget."""

    def test_paint_default(self) -> None:
        widget = StrobeDiscWidget()
        image = _paint_to_image(widget)
        self.assertFalse(image.isNull())
        self.assertTrue(_image_is_nonblank(image))

    def test_paint_with_zero_error(self) -> None:
        widget = StrobeDiscWidget()
        widget.set_error(0.0)
        # Let the timer tick once to update phase.
        widget._tick()
        image = _paint_to_image(widget)
        self.assertFalse(image.isNull())
        self.assertTrue(_image_is_nonblank(image))

    def test_paint_with_positive_error(self) -> None:
        widget = StrobeDiscWidget()
        widget.set_error(10.0)
        widget._tick()
        image = _paint_to_image(widget)
        self.assertFalse(image.isNull())
        self.assertTrue(_image_is_nonblank(image))

    def test_paint_with_negative_error(self) -> None:
        widget = StrobeDiscWidget()
        widget.set_error(-10.0)
        widget._tick()
        image = _paint_to_image(widget)
        self.assertFalse(image.isNull())
        self.assertTrue(_image_is_nonblank(image))

    def test_multiple_ticks(self) -> None:
        widget = StrobeDiscWidget()
        widget.set_error(5.0)
        for _ in range(10):
            widget._tick()
        image = _paint_to_image(widget)
        self.assertFalse(image.isNull())
        self.assertTrue(_image_is_nonblank(image))


if __name__ == "__main__":
    unittest.main()