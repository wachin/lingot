"""Basic tests for lingot bindings module."""
import unittest
import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

try:
    from lingot import bindings
    BINDINGS_AVAILABLE = True
except ImportError as e:
    BINDINGS_AVAILABLE = False
    print(f"Bindings not available: {e}")


@unittest.skipUnless(BINDINGS_AVAILABLE, "Bindings module not available")
class TestBindings(unittest.TestCase):
    """Tests for the bindings module."""
    
    def test_version(self):
        """Test version retrieval."""
        version = bindings.get_version()
        self.assertIsInstance(version, tuple)
        self.assertGreater(len(version), 0)
        print(f"Lingot version: {version}")
    
    def test_create_params(self):
        """Test params creation."""
        params = bindings.create_params()
        self.assertIsNotNone(params)
    
    def test_params_has_required_fields(self):
        """Test that params has required fields."""
        params = bindings.create_params()
        # Check that params has expected structure
        self.assertTrue(hasattr(params, 'sample_rate'))
        self.assertTrue(hasattr(params, 'fft_size'))
        self.assertTrue(hasattr(params, 'overlap'))


if __name__ == '__main__':
    unittest.main()