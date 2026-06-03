#!/usr/bin/env python3
"""Test audio capture with PulseAudio."""

import sys
import time
from pyqt6_lingot.bindings import LingotBindings, LingotContext

def test_audio_capture():
    """Test audio capture with PulseAudio."""
    try:
        # Initialize the bindings
        bindings = LingotBindings()
        bindings.initialize(None)
        
        print("Initialized successfully")
        
        # Create a context
        ctx = LingotContext(bindings)
        
        # Start the context
        ctx.start()
        print("Context started")
        
        # Wait a moment for audio to start
        time.sleep(1)
        
        # Take a snapshot
        snap = ctx.snapshot()
        print(f"Snapshot: running={snap.running}, frequency={snap.frequency}, error={snap.error_cents}")
        
        # Wait a bit more to see if frequency changes
        time.sleep(2)
        
        # Take another snapshot
        snap2 = ctx.snapshot()
        print(f"Snapshot 2: running={snap2.running}, frequency={snap2.frequency}, error={snap2.error_cents}")
        
        # Stop the context
        ctx.stop()
        print("Context stopped")
        
        # Close the context
        ctx.close()
        print("Test completed successfully!")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(test_audio_capture())