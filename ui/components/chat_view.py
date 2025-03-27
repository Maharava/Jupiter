import tkinter as tk
from tkinter import scrolledtext
import logging
from ui.utils.ui_helpers import get_color

# Set up logging
logger = logging.getLogger("jupiter.gui.chat_view")

class ChatView:
    """Chat view component for Jupiter GUI"""
    
    def __init__(self, parent, jupiter_color="yellow", user_color="magenta"):
        """
        Initialize chat view component
        
        Args:
            parent: Parent tkinter container
            jupiter_color: Color for Jupiter's messages
            user_color: Color for user's messages
        """
        self.parent = parent
        self.jupiter_color = jupiter_color
        self.user_color = user_color
        self.user_prefix = "User"
        
        # Create chat frame
        self.frame = tk.Frame(parent, bg="black")
        
        # Create scrollable text area for chat
        self.chat_text = scrolledtext.ScrolledText(
            self.frame,
            wrap=tk.WORD,
            bg="black",
            fg="white",
            insertbackground="white",
            selectbackground="#666",
            selectforeground="white",
            font=("Helvetica", 10),
            padx=10,
            pady=10
        )
        self.chat_text.pack(fill=tk.BOTH, expand=True)
        self.chat_text.config(state=tk.DISABLED)  # Make read-only
        
        # Reference to current status bubble for removal
        self.status_bubble_start = None
        self.status_bubble_end = None
        
        # Configure text tags for different message types
        self._setup_tags()
    
    def _setup_tags(self):
        """Set up text tags for message styling"""
        try:
            if not hasattr(self, 'chat_text') or not self.chat_text:
                logger.error("Cannot set up tags - chat_text not initialized")
                return
                
            self.chat_text.tag_configure(
                "jupiter_prefix", 
                foreground=get_color(self.jupiter_color)
            )
            self.chat_text.tag_configure(
                "jupiter_bubble", 
                background=get_color(self.jupiter_color, 0.7), 
                foreground="black", 
                relief=tk.SOLID, 
                borderwidth=1, 
                lmargin1=10, 
                lmargin2=10, 
                rmargin=10, 
                spacing1=3, 
                spacing3=3
            )
            
            self.chat_text.tag_configure(
                "user_prefix", 
                foreground=get_color(self.user_color)
            )
            self.chat_text.tag_configure(
                "user_bubble", 
                background=get_color(self.user_color, 0.7), 
                foreground="white", 
                relief=tk.SOLID, 
                borderwidth=1, 
                lmargin1=10, 
                lmargin2=10, 
                rmargin=10, 
                spacing1=3, 
                spacing3=3
            )
            
            # Status bubble tag
            self.chat_text.tag_configure(
                "status_bubble", 
                background="#333333",
                foreground="#FFFFFF",
                relief=tk.SOLID, 
                borderwidth=1,
                lmargin1=10, 
                lmargin2=10,
                rmargin=10,
                spacing1=3,
                spacing3=3
            )
        except Exception as e:
            logger.error(f"Error setting up chat tags: {e}")
    
    def display_jupiter_message(self, message):
        """
        Display a message from Jupiter in the chat
        
        Args:
            message: Text message to display
        """
        try:
            # Check if widget still exists
            if not hasattr(self, 'chat_text') or not self.chat_text or not self.chat_text.winfo_exists():
                logger.warning("Cannot display Jupiter message - widget no longer exists")
                return
                
            # Enable editing
            self.chat_text.config(state=tk.NORMAL)
            
            # Add prefix
            self.chat_text.insert(tk.END, "Jupiter: ", "jupiter_prefix")
            self.chat_text.insert(tk.END, "\n")
            
            # Add message in bubble
            bubble_start = self.chat_text.index(tk.INSERT)
            self.chat_text.insert(tk.END, f"{message}\n\n")
            bubble_end = self.chat_text.index(tk.INSERT)
            
            # Apply bubble tag
            self.chat_text.tag_add("jupiter_bubble", bubble_start, bubble_end)
            
            # Scroll to bottom
            self.chat_text.see(tk.END)
            
            # Disable editing
            self.chat_text.config(state=tk.DISABLED)
            
        except Exception as e:
            logger.error(f"Error displaying Jupiter message: {e}")
    
    def display_user_message(self, message):
        """
        Display a message from the user in the chat
        
        Args:
            message: Text message to display
        """
        try:
            # Check if widget still exists
            if not hasattr(self, 'chat_text') or not self.chat_text or not self.chat_text.winfo_exists():
                logger.warning("Cannot display user message - widget no longer exists")
                return
                
            # Enable editing
            self.chat_text.config(state=tk.NORMAL)
            
            # Add prefix
            self.chat_text.insert(tk.END, f"{self.user_prefix}: ", "user_prefix")
            self.chat_text.insert(tk.END, "\n")
            
            # Add message in bubble - this now uses the actual message directly from the input
            # Not relying on the entry widget's current content
            bubble_start = self.chat_text.index(tk.INSERT)
            self.chat_text.insert(tk.END, f"{message}\n\n")
            bubble_end = self.chat_text.index(tk.INSERT)
            
            # Apply bubble tag
            self.chat_text.tag_add("user_bubble", bubble_start, bubble_end)
            
            # Scroll to bottom
            self.chat_text.see(tk.END)
            
            # Disable editing
            self.chat_text.config(state=tk.DISABLED)
            
        except Exception as e:
            logger.error(f"Error displaying user message: {e}")
    
    def display_status_bubble(self, text):
        """
        Display a status message in the chat area
        
        Args:
            text: Status message to display
        """
        try:
            # Check if widget still exists
            if not hasattr(self, 'chat_text') or not self.chat_text or not self.chat_text.winfo_exists():
                logger.warning("Cannot display status bubble - widget no longer exists")
                return
                
            # Remove existing status bubble if any
            self.remove_status_bubble()
            
            # Enable editing
            self.chat_text.config(state=tk.NORMAL)
            
            # Add some spacing before the bubble
            self.chat_text.insert(tk.END, "\n")
            
            # Store location for removal
            self.status_bubble_start = self.chat_text.index(tk.INSERT)
            
            # Add the status message with a special tag
            self.chat_text.insert(tk.END, f"🎤 {text}\n\n")
            self.status_bubble_end = self.chat_text.index(tk.INSERT)
            
            # Apply the tag
            self.chat_text.tag_add("status_bubble", self.status_bubble_start, self.status_bubble_end)
            
            # Scroll to bottom
            self.chat_text.see(tk.END)
            
            # Disable editing
            self.chat_text.config(state=tk.DISABLED)
            
        except Exception as e:
            logger.error(f"Error displaying status bubble: {e}")
    
    def remove_status_bubble(self):
        """Remove the status bubble from the chat area with proper error handling"""
        try:
            # Check if widget still exists and we have bubble positions
            if not hasattr(self, 'chat_text') or not self.chat_text or not self.chat_text.winfo_exists():
                logger.debug("Cannot remove status bubble - widget no longer exists")
                return
                
            if not hasattr(self, 'status_bubble_start') or not hasattr(self, 'status_bubble_end'):
                return
                
            if self.status_bubble_start is None or self.status_bubble_end is None:
                return
                
            # Enable editing
            self.chat_text.config(state=tk.NORMAL)
            
            # Remove the status message
            self.chat_text.delete(self.status_bubble_start, self.status_bubble_end)
            
            # Reset bubble references
            self.status_bubble_start = None
            self.status_bubble_end = None
            
            # Disable editing
            self.chat_text.config(state=tk.DISABLED)
            
        except Exception as e:
            logger.error(f"Error removing status bubble: {e}")
            # Reset bubble references even on error
            self.status_bubble_start = None
            self.status_bubble_end = None
    
    def update_user_prefix(self, prefix):
        """
        Update user prefix display
        
        Args:
            prefix: New user prefix
        """
        if prefix:
            self.user_prefix = prefix
    
    def clear(self):
        """Clear the chat display with proper error handling"""
        try:
            # Check if widget still exists
            if not hasattr(self, 'chat_text') or not self.chat_text or not self.chat_text.winfo_exists():
                logger.warning("Cannot clear chat - widget no longer exists")
                return
                
            # Enable editing
            self.chat_text.config(state=tk.NORMAL)
            
            # Clear all text
            self.chat_text.delete(1.0, tk.END)
            
            # Reset bubble references
            self.status_bubble_start = None
            self.status_bubble_end = None
            
            # Disable editing
            self.chat_text.config(state=tk.DISABLED)
            
        except Exception as e:
            logger.error(f"Error clearing chat: {e}")
    
    def pack(self, **kwargs):
        """Pack the chat view into its parent with error handling"""
        try:
            if hasattr(self, 'frame') and self.frame and self.frame.winfo_exists():
                self.frame.pack(**kwargs)
        except Exception as e:
            logger.error(f"Error packing chat view: {e}")
    
    def grid(self, **kwargs):
        """Grid the chat view into its parent with error handling"""
        try:
            if hasattr(self, 'frame') and self.frame and self.frame.winfo_exists():
                self.frame.grid(**kwargs)
        except Exception as e:
            logger.error(f"Error gridding chat view: {e}")
    
    def pack_forget(self):
        """Remove the chat view from the parent's layout with error handling"""
        try:
            if hasattr(self, 'frame') and self.frame and self.frame.winfo_exists():
                self.frame.pack_forget()
        except Exception as e:
            logger.error(f"Error hiding chat view: {e}")