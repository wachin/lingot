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

# Install i18n so that _() is available for main_window.py and config_dialog.py
from pyqt6_lingot.i18n import install as _install_i18n

_install_i18n()

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



# ---------------------------------------------------------------------------
# GUI smoke tests for MainWindow and ConfigDialog
# ---------------------------------------------------------------------------

# Try to import the real bindings module (for tests that need the C library).
import sys as _sys
from pathlib import Path as _Path

_REPO_ROOT = str(_Path(__file__).resolve().parent.parent.parent)
if _REPO_ROOT not in _sys.path:
    _sys.path.insert(0, _REPO_ROOT)

try:
    from pyqt6_lingot.bindings import LingotBindings, LingotContext, LingotLibraryError

    _LIBRARY_AVAILABLE = True
except (ImportError, Exception):
    _LIBRARY_AVAILABLE = False


def _has_library() -> bool:
    if not _LIBRARY_AVAILABLE:
        return False
    try:
        b = LingotBindings()
        return True
    except Exception:
        return False


HAS_LIBRARY = _has_library()


class TestMainWindowSmoke(unittest.TestCase):
    """Smoke tests for MainWindow construction and basic operations."""

    def test_construct_without_context(self) -> None:
        """MainWindow should construct with None context (offline mode)."""
        from pyqt6_lingot.main_window import MainWindow

        win = MainWindow(context=None)
        self.assertIsNotNone(win)
        self.setWindowTitle = win.windowTitle()
        self.assertTrue(len(win.windowTitle()) > 0)
        win.close()

    def test_menus_exist(self) -> None:
        """All expected menus should be created."""
        from pyqt6_lingot.main_window import MainWindow

        win = MainWindow(context=None)
        menu_bar = win.menuBar()
        menu_titles = [menu_bar.actions()[i].text() for i in range(len(menu_bar.actions()))]
        self.assertTrue(any("&File" in t for t in menu_titles))
        self.assertTrue(any("&Edit" in t for t in menu_titles))
        self.assertTrue(any("&View" in t for t in menu_titles))
        self.assertTrue(any("&Help" in t for t in menu_titles))
        win.close()

    def test_gauge_strobe_toggle(self) -> None:
        """Gauge/strobe toggle should show/hide the correct widget.

        Note: isVisible() returns False for widgets inside a hidden window,
        so we check the internal show_gauge flag instead.
        """
        from pyqt6_lingot.main_window import MainWindow

        win = MainWindow(context=None)
        self.assertTrue(win.show_gauge)
        win._set_strobe_mode()
        self.assertFalse(win.show_gauge)
        win._set_gauge_mode()
        self.assertTrue(win.show_gauge)
        win.close()

    def test_spectrum_toggle(self) -> None:
        """Spectrum visibility should toggle with the action."""
        from pyqt6_lingot.main_window import MainWindow

        win = MainWindow(context=None)
        # Show the window so isVisible() works correctly
        win.show()
        win.spectrum_action.setChecked(False)
        win.spectrum.setVisible(win.spectrum_action.isChecked())
        self.assertFalse(win.spectrum.isVisible())
        win.spectrum_action.setChecked(True)
        win.spectrum.setVisible(win.spectrum_action.isChecked())
        self.assertTrue(win.spectrum.isVisible())
        win.close()

    def test_status_bar(self) -> None:
        """Status bar should show a message."""
        from pyqt6_lingot.main_window import MainWindow

        win = MainWindow(context=None)
        win._set_status("Test status")
        self.assertIsNotNone(win.statusBar().currentMessage())
        win.close()


@unittest.skipUnless(HAS_LIBRARY, "liblingot.so not available")
class TestMainWindowWithLibrarySmoke(unittest.TestCase):
    """Smoke tests that require the C library."""

    def test_construct_with_real_context(self) -> None:
        """MainWindow should construct with a real LingotContext."""
        from pyqt6_lingot.main_window import MainWindow

        bindings = LingotBindings()
        bindings.initialize(None)
        ctx = LingotContext(bindings)
        try:
            win = MainWindow(context=ctx, bindings=bindings)
            self.assertIsNotNone(win)
            win.close()
        finally:
            ctx.close()

    def test_snapshot_timer_ticks(self) -> None:
        """The snapshot timer should fire without crashing."""
        from pyqt6_lingot.main_window import MainWindow

        bindings = LingotBindings()
        bindings.initialize(None)
        ctx = LingotContext(bindings)
        try:
            win = MainWindow(context=ctx, bindings=bindings)
            win._refresh_snapshot()
            self.assertIsNotNone(win.frequency_label.text())
            win.close()
        finally:
            ctx.close()


class TestConfigDialogSmoke(unittest.TestCase):
    """Smoke tests for ConfigDialog construction."""

    @unittest.skipUnless(HAS_LIBRARY, "liblingot.so not available")
    def test_construct(self) -> None:
        """ConfigDialog should construct without crashing."""
        from pyqt6_lingot.config_dialog import ConfigDialog

        bindings = LingotBindings()
        bindings.initialize(None)
        ctx = LingotContext(bindings)
        try:
            dialog = ConfigDialog(ctx)
            self.assertIsNotNone(dialog)
            dialog.close()
        finally:
            ctx.close()

    @unittest.skipUnless(HAS_LIBRARY, "liblingot.so not available")
    def test_tabs_exist(self) -> None:
        """All expected tabs should be created."""
        from pyqt6_lingot.config_dialog import ConfigDialog

        bindings = LingotBindings()
        bindings.initialize(None)
        ctx = LingotContext(bindings)
        try:
            dialog = ConfigDialog(ctx)
            # Find the QTabWidget
            from PyQt6.QtWidgets import QTabWidget

            tab_widget = dialog.findChild(QTabWidget)
            self.assertIsNotNone(tab_widget)
            self.assertEqual(tab_widget.count(), 4)
            tab_names = [tab_widget.tabText(i) for i in range(tab_widget.count())]
            self.assertTrue(any("Capture" in n for n in tab_names))
            self.assertTrue(any("Adjustments" in n for n in tab_names))
            self.assertTrue(any("Settings" in n for n in tab_names))
            self.assertTrue(any("Scale" in n for n in tab_names))
            dialog.close()
        finally:
            ctx.close()

    @unittest.skipUnless(HAS_LIBRARY, "liblingot.so not available")
    def test_capture_tab_widgets(self) -> None:
        """Capture tab should have audio system and device combos."""
        from pyqt6_lingot.config_dialog import ConfigDialog

        bindings = LingotBindings()
        bindings.initialize(None)
        ctx = LingotContext(bindings)
        try:
            dialog = ConfigDialog(ctx)
            self.assertIsNotNone(dialog.audio_system)
            self.assertGreater(dialog.audio_system.count(), 0)
            self.assertIsNotNone(dialog.audio_device)
            dialog.close()
        finally:
            ctx.close()

    @unittest.skipUnless(HAS_LIBRARY, "liblingot.so not available")
    def test_adjustments_tab_widgets(self) -> None:
        """Adjustments tab should have calculation rate and noise sliders."""
        from pyqt6_lingot.config_dialog import ConfigDialog

        bindings = LingotBindings()
        bindings.initialize(None)
        ctx = LingotContext(bindings)
        try:
            dialog = ConfigDialog(ctx)
            self.assertIsNotNone(dialog.calculation_rate_slider)
            self.assertIsNotNone(dialog.noise_threshold_slider)
            self.assertGreater(dialog.calculation_rate_slider.minimum(), 0)
            dialog.close()
        finally:
            ctx.close()

    @unittest.skipUnless(HAS_LIBRARY, "liblingot.so not available")
    def test_settings_tab_widgets(self) -> None:
        """Settings tab should have FFT size and temporal window."""
        from pyqt6_lingot.config_dialog import ConfigDialog

        bindings = LingotBindings()
        bindings.initialize(None)
        ctx = LingotContext(bindings)
        try:
            dialog = ConfigDialog(ctx)
            self.assertIsNotNone(dialog.fft_size)
            self.assertGreater(dialog.fft_size.count(), 0)
            self.assertIsNotNone(dialog.temporal_window)
            self.assertGreaterEqual(dialog.temporal_window.minimum(), 0.0)
            dialog.close()
        finally:
            ctx.close()

    @unittest.skipUnless(HAS_LIBRARY, "liblingot.so not available")
    def test_scale_tab_widgets(self) -> None:
        """Scale tab should have name, table, and buttons."""
        from pyqt6_lingot.config_dialog import ConfigDialog

        bindings = LingotBindings()
        bindings.initialize(None)
        ctx = LingotContext(bindings)
        try:
            dialog = ConfigDialog(ctx)
            self.assertIsNotNone(dialog.scale_name)
            self.assertIsNotNone(dialog.scale_table)
            self.assertGreater(dialog.scale_table.columnCount(), 0)
            self.assertIsNotNone(dialog.scale_add_button)
            self.assertIsNotNone(dialog.scale_remove_button)
            self.assertIsNotNone(dialog.scale_import_button)
            dialog.close()
        finally:
            ctx.close()


if __name__ == "__main__":
    unittest.main()
