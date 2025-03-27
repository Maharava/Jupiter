"""
Adapter layer for the wake word detector models.
This allows for easy swapping of wake word systems while maintaining the interface.
"""

from utils.io.io import WakeWordDetector

# Re-export the class for backwards compatibility
__all__ = ["WakeWordDetector"]
