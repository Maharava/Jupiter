"""
Adapter layer for the wake word detector models.
"""

# Import from the actual io-wake-word package
import io-wake-word as iww  # Replace with actual package import 

class WakeWordDetector:
    """Detects wake words in audio stream"""
    def __init__(self, model_path=None):
        self.detector = iww.WakeWordDetector(model_path=model_path)
        self.is_running = False
    
    def start(self):
        self.detector.start()
        self.is_running = True
    
    def stop(self):
        self.detector.stop()
        self.is_running = False
    
    def register_detection_callback(self, callback):
        self.detector.on_detection(callback)

# Re-export class
__all__ = ["WakeWordDetector"]