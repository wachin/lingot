"""Workflow tests for the PyQt6 frontend.

These tests verify the key user workflows work correctly:
- First run creates config
- Config loading and saving
- Preferences apply/restart core
- About dialog
"""
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

# Ensure a QApplication exists before any widget is created.
import sys
from PyQt6.QtWidgets import QApplication

_app = QApplication.instance() or QApplication([])

# Import i18n first to install _() builtin
from pyqt6_lingot.i18n import install as _install_i18n
_install_i18n()

# Try to import the real bindings module
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


@unittest.skipUnless(HAS_LIBRARY, "liblingot.so not available")
class TestWorkflowFirstRun(unittest.TestCase):
    """Test that first run creates config file."""

    def test_first_run_creates_config(self) -> None:
        """First run should create the default config file."""
        # Get the config filename
        bindings = LingotBindings()
        bindings.initialize(None)
        config_filename = bindings.config_filename()
        
        # Check if config file exists (or would be created)
        self.assertIsInstance(config_filename, str)
        self.assertTrue(len(config_filename) > 0)


@unittest.skipUnless(HAS_LIBRARY, "liblingot.so not available")
class TestWorkflowConfigLoading(unittest.TestCase):
    """Test config loading and saving workflows."""

    def test_load_default_config(self) -> None:
        """Load the default config file."""
        bindings = LingotBindings()
        bindings.initialize(None)
        ctx = LingotContext(bindings)
        
        # Load the default config
        filename = bindings.config_filename()
        ctx.load_config(filename)
        
        # Verify config values are loaded
        values = ctx.config_values()
        self.assertIsNotNone(values)
        self.assertGreater(values.fft_size, 0)
        
        ctx.close()

    def test_save_config_to_temp_file(self) -> None:
        """Save config to a temporary file."""
        bindings = LingotBindings()
        bindings.initialize(None)
        ctx = LingotContext(bindings)
        
        # Get current config values
        values = ctx.config_values()
        
        # Save to a temporary file
        with tempfile.NamedTemporaryFile(suffix='.conf', delete=False) as f:
            temp_filename = f.name
        
        try:
            ctx.save_config(temp_filename)
            
            # Verify the file was created
            self.assertTrue(os.path.exists(temp_filename))
            self.assertGreater(os.path.getsize(temp_filename), 0)
        finally:
            # Clean up
            if os.path.exists(temp_filename):
                os.unlink(temp_filename)
        
        ctx.close()


@unittest.skipUnless(HAS_LIBRARY, "liblingot.so not available")
class TestWorkflowPreferences(unittest.TestCase):
    """Test preferences apply/restart workflow."""

    def test_apply_preferences(self) -> None:
        """Apply preferences and restart the core."""
        bindings = LingotBindings()
        bindings.initialize(None)
        ctx = LingotContext(bindings)
        
        # Get current config values
        values = ctx.config_values()
        
        # Modify a value
        original_fft_size = values.fft_size
        values.fft_size = 2048 if original_fft_size != 2048 else 1024
        
        # Apply the changes
        ctx.set_config_values(values)
        
        # Restart the core
        ctx.restart()
        
        # Verify the changes were applied
        new_values = ctx.config_values()
        self.assertEqual(new_values.fft_size, values.fft_size)
        
        # Restore original values
        values.fft_size = original_fft_size
        ctx.set_config_values(values)
        ctx.restart()
        
        ctx.close()


@unittest.skipUnless(HAS_LIBRARY, "liblingot.so not available")
class TestWorkflowAboutDialog(unittest.TestCase):
    """Test that About dialog can be shown."""

    def test_about_dialog_import(self) -> None:
        """Verify About dialog can be imported."""
        from pyqt6_lingot.main_window import MainWindow
        
        # Create a main window (this will have the About menu)
        win = MainWindow(context=None)
        
        # Verify the window was created
        self.assertIsNotNone(win)
        
        # Verify the window has a menu bar
        menu_bar = win.menuBar()
        self.assertIsNotNone(menu_bar)
        
        win.close()


if __name__ == "__main__":
    unittest.main()