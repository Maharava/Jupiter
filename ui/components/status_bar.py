import tkinter as tk
import logging

# Set up logging
logger = logging.getLogger("jupiter.gui.status_bar")

class StatusBar:
    """Status bar component for Jupiter GUI"""
    
    def __init__(self, parent, initial_text="Ready", initial_color="#4CAF50"):
        """
        Initialize the status bar
        
        Args:
            parent: Parent tkinter container
            initial_text: Initial status text
            initial_color: Initial text color
        """
        self.parent = parent
        
        try:
            # Create frame
            self.frame = tk.Frame(parent, bg="black")
            
            # Create status label
            self.status_label = tk.Label(
                self.frame,
                text=initial_text,
                bg="black",
                fg=initial_color,
                font=("Helvetica", 9, "italic"),
                anchor="w"
            )
            self.status_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
            
        except Exception as e:
            logger.error(f"Error initializing status bar: {e}")
    
    def set_status(self, text, color="#4CAF50"):
        """
        Update the status text and color with proper error handling
        
        Args:
            text: Status text to display
            color: Text color (string or hex color code)
        """
        try:
            # Check if label widget still exists
            if hasattr(self, 'status_label') and self.status_label and self.status_label.winfo_exists():
                self.status_label.config(text=text, fg=color)
                # Force update to ensure visibility
                self.status_label.update_idletasks()
            else:
                logger.warning(f"Cannot update status - widget no longer exists: {text}")
                
        except Exception as e:
            logger.error(f"Error setting status: {e}")
    
    def get_frame(self):
        """Get the frame containing the status bar with error handling"""
        if hasattr(self, 'frame') and self.frame:
            return self.frame
        logger.warning("Status bar frame requested but not available")
        return None
    
    def pack(self, **kwargs):
        """Pack the status bar into its parent with error handling"""
        try:
            if hasattr(self, 'frame') and self.frame and self.frame.winfo_exists():
                self.frame.pack(**kwargs)
        except Exception as e:
            logger.error(f"Error packing status bar: {e}")
    
    def grid(self, **kwargs):
        """Grid the status bar into its parent with error handling"""
        try:
            if hasattr(self, 'frame') and self.frame and self.frame.winfo_exists():
                self.frame.grid(**kwargs)
        except Exception as e:
            logger.error(f"Error gridding status bar: {e}")
    
    def pack_forget(self):
        """Remove the status bar from the parent's layout with error handling"""
        try:
            if hasattr(self, 'frame') and self.frame and self.frame.winfo_exists():
                self.frame.pack_forget()
        except Exception as e:
            logger.error(f"Error hiding status bar: {e}")