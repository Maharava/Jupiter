"""
Adapter layer between Jupiter's AudioCapture and the wake word detector.
"""

# Import from the actual io-wake-word package
import io_wake_word as iww  # Replace with actual package import

class AudioCapture:
    """Captures audio from microphone"""
    def __init__(self):
        self.capture = iww.AudioCapture()
        self.is_running = False
    
    def start(self):
        self.capture.start()
        self.is_running = True
    
    def stop(self):
        self.capture.stop()
        self.is_running = False
    
    def get_buffer(self):
        return self.capture.get_audio_buffer()

class FeatureExtractor:
    """Extracts features from audio data"""
    def __init__(self):
        self.extractor = iww.FeatureExtractor()
    
    def extract_features(self, audio_data):
        return self.extractor.process(audio_data)

# Re-export classes
__all__ = ["AudioCapture", "FeatureExtractor"]