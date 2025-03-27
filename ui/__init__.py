"""
Jupiter UI Package

This package contains the user interface components for Jupiter,
including both terminal and graphical interfaces.
"""

from ui.terminal_interface import TerminalInterface
from ui.gui_interface import GUIInterface

# Import voice indicator for easy access
from ui.components.voice_indicator import VoiceIndicator

__all__ = [
    'TerminalInterface',
    'GUIInterface',
    'VoiceIndicator'
]
