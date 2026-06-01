"""Tests for the lingot PyQt6 bindings module.

These tests verify the Python-side binding layer against the C shared
library.  When the library is not available the tests are skipped rather
than failing, so the suite can run in CI environments that do not have
liblingot built.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

# ---------------------------------------------------------------------------
# Try to import the real bindings module.
# ---------------------------------------------------------------------------
_REPO_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

try:
    from pyqt6_lingot.bindings import (
        ConfigValues,
        LingotBindings,
        LingotContext,
        LingotLibraryError,
        Scale,
        ScaleNote,
        Snapshot,
        UiSettings,
    )

    _LIBRARY_AVAILABLE = True
except (ImportError, LingotLibraryError):
    _LIBRARY_AVAILABLE = False


def _has_library() -> bool:
    """Return True only if we can actually load liblingot."""
    if not _LIBRARY_AVAILABLE:
        return False
    try:
        LingotBindings()
        return True
    except LingotLibraryError:
        return False


HAS_LIBRARY = _has_library()


# ---------------------------------------------------------------------------
# Pure-Python unit tests (no C library required)
# ---------------------------------------------------------------------------


class TestSnapshotProperties(unittest.TestCase):
    """Verify Snapshot helper properties."""

    def test_note_name_empty(self) -> None:
        snap = Snapshot()
        snap.closest_note_name = None
        self.assertEqual(snap.note_name, "")

    def test_has_pitch_negative_index(self) -> None:
        snap = Snapshot()
        snap.closest_note_index = -1
        snap.error_cents = 0.0
        self.assertFalse(snap.has_pitch)

    def test_has_pitch_nan_error(self) -> None:
        snap = Snapshot()
        snap.closest_note_index = 0
        snap.error_cents = float("nan")
        self.assertFalse(snap.has_pitch)

    def test_has_pitch_valid(self) -> None:
        snap = Snapshot()
        snap.closest_note_index = 3
        snap.error_cents = -5.0
        self.assertTrue(snap.has_pitch)


class TestScaleNoteDataclass(unittest.TestCase):
    """Verify ScaleNote dataclass defaults."""

    def test_defaults(self) -> None:
        note = ScaleNote(name="C", cents=0.0)
        self.assertEqual(note.name, "C")
        self.assertEqual(note.cents, 0.0)
        self.assertEqual(note.shift, "")

    def test_with_shift(self) -> None:
        note = ScaleNote(name="Eb", cents=315.64, shift="3/2")
        self.assertEqual(note.shift, "3/2")


class TestScaleDataclass(unittest.TestCase):
    """Verify Scale dataclass."""

    def test_scale_construction(self) -> None:
        notes = [ScaleNote("C", 0.0), ScaleNote("G", 700.0)]
        scale = Scale(name="Test", base_frequency=261.63, notes=notes)
        self.assertEqual(scale.name, "Test")
        self.assertEqual(len(scale.notes), 2)


class TestConfigValuesDefaults(unittest.TestCase):
    """Verify ConfigValues structure defaults."""

    def test_zero_initialized(self) -> None:
        cv = ConfigValues()
        self.assertEqual(cv.audio_system_index, 0)
        self.assertEqual(cv.fft_size, 0)
        self.assertEqual(cv.temporal_window, 0.0)


class TestUiSettingsDefaults(unittest.TestCase):
    """Verify UiSettings structure defaults."""

    def test_zero_initialized(self) -> None:
        us = UiSettings()
        self.assertEqual(us.win_width, 0)
        self.assertEqual(us.visualization_rate, 0.0)


# ---------------------------------------------------------------------------
# Tests that require the C shared library
# ---------------------------------------------------------------------------


@unittest.skipUnless(HAS_LIBRARY, "liblingot.so not available")
class TestBindingsInitialize(unittest.TestCase):
    """Test LingotBindings initialization."""

    def setUp(self) -> None:
        self.bindings = LingotBindings()

    def test_initialize_default(self) -> None:
        self.bindings.initialize(None)

    def test_config_filename_nonempty(self) -> None:
        self.bindings.initialize(None)
        name = self.bindings.config_filename()
        self.assertIsInstance(name, str)
        self.assertTrue(len(name) > 0)

    def test_audio_systems_list(self) -> None:
        self.bindings.initialize(None)
        systems = self.bindings.audio_systems()
        self.assertIsInstance(systems, list)


@unittest.skipUnless(HAS_LIBRARY, "liblingot.so not available")
class TestBindingsConfigValues(unittest.TestCase):
    """Test reading and writing config values through bindings."""

    def setUp(self) -> None:
        self.bindings = LingotBindings()
        self.bindings.initialize(None)

    def test_default_config_values(self) -> None:
        defaults = self.bindings.default_config_values()
        self.assertIsInstance(defaults, ConfigValues)
        self.assertGreater(defaults.fft_size, 0)

    def test_ui_settings_roundtrip(self) -> None:
        settings = self.bindings.ui_settings()
        original_width = settings.win_width
        settings.win_width = 999
        self.bindings.set_ui_settings(settings)
        restored = self.bindings.ui_settings()
        self.assertEqual(restored.win_width, 999)
        # Restore original
        settings.win_width = original_width
        self.bindings.set_ui_settings(settings)


@unittest.skipUnless(HAS_LIBRARY, "liblingot.so not available")
class TestContextLifecycle(unittest.TestCase):
    """Test LingotContext creation, start, stop, and destroy."""

    def setUp(self) -> None:
        self.bindings = LingotBindings()
        self.bindings.initialize(None)

    def test_create_and_destroy(self) -> None:
        ctx = LingotContext(self.bindings)
        ctx.close()

    def test_start_stop(self) -> None:
        ctx = LingotContext(self.bindings)
        ctx.start()
        ctx.stop()
        ctx.close()

    def test_snapshot_when_not_running(self) -> None:
        ctx = LingotContext(self.bindings)
        snap = ctx.snapshot()
        self.assertFalse(snap.running)
        ctx.close()

    def test_restart(self) -> None:
        ctx = LingotContext(self.bindings)
        ctx.start()
        ctx.restart()
        ctx.stop()
        ctx.close()

    def test_load_config(self) -> None:
        ctx = LingotContext(self.bindings)
        filename = self.bindings.config_filename()
        ctx.load_config(filename)
        ctx.close()


@unittest.skipUnless(HAS_LIBRARY, "liblingot.so not available")
class TestContextScale(unittest.TestCase):
    """Test scale reading and writing through context."""

    def setUp(self) -> None:
        self.bindings = LingotBindings()
        self.bindings.initialize(None)
        self.ctx = LingotContext(self.bindings)

    def tearDown(self) -> None:
        self.ctx.close()

    def test_read_scale(self) -> None:
        scale = self.ctx.scale()
        self.assertIsInstance(scale, Scale)
        self.assertGreater(len(scale.notes), 0)
        self.assertGreater(scale.base_frequency, 0)

    def test_read_default_scale(self) -> None:
        scale = self.ctx.default_scale()
        self.assertIsInstance(scale, Scale)
        self.assertGreater(len(scale.notes), 0)

    def test_set_and_read_scale(self) -> None:
        original_scale = self.ctx.scale()
        new_notes = [ScaleNote("C", 0.0, "1/1"), ScaleNote("G", 700.0, "3/2")]
        new_scale = Scale(name="Test scale", base_frequency=261.63, notes=new_notes)
        self.ctx.set_scale(new_scale)
        read_back = self.ctx.scale()
        self.assertEqual(read_back.name, "Test scale")
        self.assertEqual(len(read_back.notes), 2)
        # Restore original
        self.ctx.set_scale_shifts(original_scale)


@unittest.skipUnless(HAS_LIBRARY, "liblingot.so not available")
class TestContextSnapshot(unittest.TestCase):
    """Test snapshot and spectrum reading."""

    def setUp(self) -> None:
        self.bindings = LingotBindings()
        self.bindings.initialize(None)
        self.ctx = LingotContext(self.bindings)

    def tearDown(self) -> None:
        self.ctx.close()

    def test_snapshot_structure(self) -> None:
        snap = self.ctx.snapshot()
        self.assertIsInstance(snap, Snapshot)
        self.assertIn(snap.running, (0, 1))

    def test_spectrum_empty_when_not_running(self) -> None:
        self.ctx.stop()
        spectrum = self.ctx.spectrum(100)
        self.assertIsInstance(spectrum, list)


@unittest.skipUnless(HAS_LIBRARY, "liblingot.so not available")
class TestPopMessage(unittest.TestCase):
    """Test message queue."""

    def setUp(self) -> None:
        self.bindings = LingotBindings()
        self.bindings.initialize(None)
        self.ctx = LingotContext(self.bindings)

    def tearDown(self) -> None:
        self.ctx.close()

    def test_pop_message_returns_none_or_tuple(self) -> None:
        result = self.ctx.pop_message()
        if result is not None:
            self.assertEqual(len(result), 3)
            self.assertIsInstance(result[0], int)
            self.assertIsInstance(result[1], int)
            self.assertIsInstance(result[2], str)


if __name__ == "__main__":
    unittest.main()