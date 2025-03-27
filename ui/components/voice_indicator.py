import tkinter as tk
import logging
from enum import Enum

# Set up logging
logger = logging.getLogger("jupiter.gui.voice_indicator")

class VoiceIndicator:
    """
    Voice state indicator for Jupiter GUI
    
    This class creates and manages a voice status indicator
    that can be added to the Jupiter GUI.
    """
    
    def __init__(self, parent_frame, callback=None):
        """
        Initialize the voice indicator
        
        Args:
            parent_frame: The parent Tkinter frame
            callback: Optional callback function when indicator is clicked
        """
        self.parent = parent_frame
        self.callback = callback
        
        # Status colors
        self.INACTIVE_COLOR = "#888888"  # Gray
        self.LISTENING_COLOR = "#4CAF50"  # Green
        self.FOCUSING_COLOR = "#9C27B0"  # Purple
        self.PROCESSING_COLOR = "#2196F3"  # Blue
        self.SPEAKING_COLOR = "#FF9800"  # Orange
        
        try:
            # Create indicator frame
            self.frame = tk.Frame(parent_frame, bg=parent_frame["bg"])
            
            # Create indicator components
            self._create_indicator()
            
        except Exception as e:
            logger.error(f"Error initializing voice indicator: {e}")
        
    def _create_indicator(self):
        """Create the visual indicator components with proper error handling"""
        try:
            # Create canvas for circle
            self.canvas = tk.Canvas(
                self.frame, 
                width=10, 
                height=10,
                bg=self.parent["bg"],
                highlightthickness=0
            )
            self.canvas.pack(side=tk.LEFT, padx=(0, 5))
            
            # Draw circle (initially gray)
            self.circle = self.canvas.create_oval(1, 1, 9, 9, fill=self.INACTIVE_COLOR)
            
            # Create label
            self.label = tk.Label(
                self.frame,
                text="Deaf",
                font=("Helvetica", 9),
                bg=self.parent["bg"],
                fg="#999999"
            )
            self.label.pack(side=tk.LEFT)
            
            # Bind click event
            self.canvas.bind("<Button-1>", self._handle_click)
            self.label.bind("<Button-1>", self._handle_click)
            
        except Exception as e:
            logger.error(f"Error creating voice indicator components: {e}")
        
    def _handle_click(self, event):
        """Handle click event on the indicator with proper error handling"""
        try:
            if self.callback and callable(self.callback):
                self.callback()
        except Exception as e:
            logger.error(f"Error handling voice indicator click: {e}")
            
    def update_state(self, state):
        """
        Update the indicator to match the current voice state with proper error handling
        
        Args:
            state: VoiceState enum value or string
        """
        try:
            if state is None:
                return
                
            # Get state name as a string
            state_name = state.name if hasattr(state, "name") else str(state)
            
            if state_name == "INACTIVE":
                self._set_state("Deaf", self.INACTIVE_COLOR)
            elif state_name == "LISTENING":
                self._set_state("Listening", self.LISTENING_COLOR)
            elif state_name == "FOCUSING":
                self._set_state("Focusing", self.FOCUSING_COLOR)
            elif state_name == "PROCESSING":
                self._set_state("Processing", self.PROCESSING_COLOR)
            elif state_name == "SPEAKING":
                self._set_state("Speaking", self.SPEAKING_COLOR)
                
        except Exception as e:
            logger.error(f"Error updating voice indicator state: {e}")
            
    def _set_state(self, text, color):
        """Set the indicator state with proper error handling"""
        try:
            # Check if components still exist
            if not hasattr(self, 'label') or not self.label or not self.label.winfo_exists():
                logger.debug("Cannot update voice indicator label - widget no longer exists")
                return
                
            if not hasattr(self, 'canvas') or not self.canvas or not self.canvas.winfo_exists():
                logger.debug("Cannot update voice indicator circle - widget no longer exists")
                return
                
            # Update label
            self.label.config(text=text)
            
            # Update circle
            self.canvas.itemconfig(self.circle, fill=color)
            
        except Exception as e:
            logger.error(f"Error setting voice indicator state: {e}")
        
    def pack(self, **kwargs):
        """Pack the frame into the parent with proper error handling"""
        try:
            if hasattr(self, 'frame') and self.frame and self.frame.winfo_exists():
                self.frame.pack(**kwargs)
        except Exception as e:
            logger.error(f"Error packing voice indicator: {e}")
        
    def grid(self, **kwargs):
        """Grid the frame into the parent with proper error handling"""
        try:
            if hasattr(self, 'frame') and self.frame and self.frame.winfo_exists():
                self.frame.grid(**kwargs)
        except Exception as e:
            logger.error(f"Error gridding voice indicator: {e}")