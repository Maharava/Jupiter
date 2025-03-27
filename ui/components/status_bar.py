import tkinter as tk

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
    
    def set_status(self, text, color="#4CAF50"):
        """
        Update the status text and color
        
        Args:
            text: Status text to display
            color: Text color
        """
        if self.status_label and self.status_label.winfo_exists():
            self.status_label.config(text=text, fg=color)
    
    def get_frame(self):
        """Get the frame containing the status bar"""
        return self.frame
    
    def pack(self, **kwargs):
        """Pack the status bar into its parent"""
        self.frame.pack(**kwargs)
    
    def grid(self, **kwargs):
        """Grid the status bar into its parent"""
        self.frame.grid(**kwargs)
    
    def pack_forget(self):
        """Remove the status bar from the parent's layout"""
        self.frame.pack_forget()
