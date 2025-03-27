"""
Adapter layer between Jupiter's AudioCapture and the wake word detector.
This allows for easy swapping of wake word systems while maintaining the interface.
"""

from utils.io.io import AudioCapture, WakeWordDetector, FeatureExtractor

# Re-export the classes for backwards compatibility
__all__ = ["AudioCapture", "WakeWordDetector", "FeatureExtractor"]
