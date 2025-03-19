import tkinter as tk
from tkinter import ttk
import logging
import threading
import time
import queue
from pathlib import Path
import os

logger = logging.getLogger('jupiter.calendar.gui_notifications')

# Try to import preferences
try:
    from .preferences_ui import get_preferences
except ImportError:
    # Create a dummy preferences getter
    def get_preferences():
        return None

class NotificationWindow:
    """
    Popup window for calendar notifications in GUI mode
    """
    
    def __init__(self, root=None):
        """
        Initialize the notification window
        
        Args:
            root: Tkinter root window (or None to create a new one)
        """
        self.root = root
        self.active_notifications = {}
        self.notification_queue = queue.Queue()
        self.processing_thread = None
        self.running = False
        
        # Get preferences
        self.prefs = get_preferences()
        
        # Position settings
        self.screen_width = 1920  # Default, will be updated
        self.screen_height = 1080  # Default, will be updated
        self.notification_width = 350
        self.notification_height = 100
        self.notification_spacing = 10
        
        # Duration from preferences or default
        self.notification_duration = 10  # seconds
        if self.prefs:
            self.notification_duration = self.prefs.get_preference("notification_duration", 10)
            
        # Position from preferences or default
        self.notification_position = "bottom-right"
        if self.prefs:
            self.notification_position = self.prefs.get_preference("notification_position", "bottom-right")
        
        # Load bell sound (if available)
        self.bell_sound_file = self._get_bell_sound_path()
        
        # Check if sound is enabled
        self.play_sound = True
        if self.prefs:
            self.play_sound = self.prefs.get_preference("play_sound", True)
        
        # Start processing thread
        self.start()
        
    def _get_bell_sound_path(self):
        """Get path to notification sound file"""
        base_dir = Path(os.path.dirname(os.path.abspath(__file__))).parent.parent
        sound_file = os.path.join(base_dir, "assets", "notification.wav")
        
        if os.path.exists(sound_file):
            return sound_file
        return None
        
    def start(self):
        """Start the notification processing thread"""
        if self.running:
            return
            
        self.running = True
        self.processing_thread = threading.Thread(
            target=self._process_notifications,
            daemon=True,
            name="GuiNotificationProcessor"
        )
        self.processing_thread.start()
        logger.info("GUI notification processor started")
        
    def stop(self):
        """Stop the notification processing thread"""
        self.running = False
        if self.processing_thread:
            self.processing_thread.join(timeout=2.0)
            self.processing_thread = None
            
        # Close any active notifications
        for window in list(self.active_notifications.values()):
            try:
                window.destroy()
            except:
                pass
        self.active_notifications.clear()
        
    def _process_notifications(self):
        """Process notifications from the queue"""
        while self.running:
            try:
                # Get notification from queue (with timeout)
                try:
                    notification = self.notification_queue.get(timeout=1.0)
                except queue.Empty:
                    continue
                    
                # Process notification in main thread
                if self.root:
                    self.root.after(0, lambda n=notification: self._show_notification(n))
                else:
                    # Create a temporary Tk root if needed
                    temp_root = tk.Tk()
                    temp_root.withdraw()  # Hide main window
                    self._show_notification(notification, temp_root)
                    temp_root.mainloop()
                    
                self.notification_queue.task_done()
                
            except Exception as e:
                logger.error(f"Error processing GUI notification: {e}")
                time.sleep(1)
                
    def _show_notification(self, notification, temp_root=None):
        """Show a notification window"""
        try:
            # Create a new toplevel window
            parent = temp_root or self.root
            notif_win = tk.Toplevel(parent)
            notif_win.title("Calendar Reminder")
            
            # Store metadata
            notif_id = notification.get('id', str(id(notification)))
            self.active_notifications[notif_id] = notif_win
            notif_win.notification_id = notif_id
            
            # Set window properties
            notif_win.attributes('-topmost', True)  # Stay on top
            notif_win.overrideredirect(True)  # Remove window decorations
            
            # Update screen dimensions
            self.screen_width = parent.winfo_screenwidth()
            self.screen_height = parent.winfo_screenheight()
            
            # Calculate position based on preference
            position = self._calculate_notification_position(notif_id)
            notif_win.geometry(f"{self.notification_width}x{self.notification_height}+{position[0]}+{position[1]}")
            
            # Create notification content
            self._create_notification_content(notif_win, notification)
            
            # Make semi-transparent with fade-in effect
            notif_win.attributes('-alpha', 0.0)
            self._fade_in(notif_win)
            
            # Play notification sound if enabled
            if self.play_sound and self.bell_sound_file and hasattr(parent, 'bell'):
                parent.bell()
            
            # Get current duration from preferences if available
            duration = self.notification_duration
            if self.prefs:
                duration = self.prefs.get_preference("notification_duration", duration)
                
            # Schedule auto-close
            parent.after(duration * 1000, 
                        lambda: self._close_notification(notif_id))
            
        except Exception as e:
            logger.error(f"Error showing notification window: {e}")
            
    def _create_notification_content(self, window, notification):
        """Create content for notification window"""
        # Style
        bg_color = "#3a7ebf"  # Blue background
        fg_color = "white"    # White text
        
        # Main frame
        frame = tk.Frame(window, bg=bg_color, bd=0)
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Add close button (X)
        close_btn = tk.Label(
            frame, 
            text="×", 
            font=("Arial", 16), 
            bg=bg_color,
            fg=fg_color,
            cursor="hand2"
        )
        close_btn.pack(side=tk.TOP, anchor=tk.NE, padx=5, pady=2)
        close_btn.bind("<Button-1>", lambda e: self._close_notification(window.notification_id))
        
        # Title
        title_label = tk.Label(
            frame,
            text=notification.get('title', 'Calendar Reminder'),
            font=("Arial", 12, "bold"),
            bg=bg_color,
            fg=fg_color,
            anchor=tk.W,
            padx=10
        )
        title_label.pack(fill=tk.X, pady=(0, 5))
        
        # Message
        message_label = tk.Label(
            frame,
            text=notification.get('message', ''),
            font=("Arial", 10),
            bg=bg_color,
            fg=fg_color,
            anchor=tk.W,
            justify=tk.LEFT,
            wraplength=self.notification_width - 20,
            padx=10
        )
        message_label.pack(fill=tk.X, expand=True)
        
        # Buttons frame
        btn_frame = tk.Frame(frame, bg=bg_color)
        btn_frame.pack(fill=tk.X, side=tk.BOTTOM, padx=10, pady=10)
        
        # Snooze button
        snooze_btn = tk.Button(
            btn_frame,
            text="Snooze",
            font=("Arial", 9),
            bg="#2a5985",
            fg=fg_color,
            bd=0,
            padx=10,
            command=lambda: self._snooze_notification(window.notification_id)
        )
        snooze_btn.pack(side=tk.LEFT)
        
        # Dismiss button
        dismiss_btn = tk.Button(
            btn_frame,
            text="Dismiss",
            font=("Arial", 9),
            bg="#2a5985",
            fg=fg_color,
            bd=0,
            padx=10,
            command=lambda: self._close_notification(window.notification_id)
        )
        dismiss_btn.pack(side=tk.RIGHT)
        
        # Make window draggable
        title_label.bind("<ButtonPress-1>", self._start_drag)
        title_label.bind("<ButtonRelease-1>", self._stop_drag)
        title_label.bind("<B1-Motion>", self._on_drag)
        
        # Store drag data
        window.drag_data = {"x": 0, "y": 0, "dragging": False}
        
    def _calculate_notification_position(self, notif_id):
        """Calculate position for the notification window based on preferences"""
        # Count current notifications for stacking
        num_active = len(self.active_notifications)
        
        # Base position based on preference
        position = self.notification_position
        if self.prefs:
            position = self.prefs.get_preference("notification_position", position)
        
        # Calculate position
        if position == "bottom-right":
            x = self.screen_width - self.notification_width - 20
            y = self.screen_height - (self.notification_height + self.notification_spacing) * num_active - 40
        elif position == "top-right":
            x = self.screen_width - self.notification_width - 20
            y = 40 + (self.notification_height + self.notification_spacing) * (num_active - 1)
        elif position == "bottom-left":
            x = 20
            y = self.screen_height - (self.notification_height + self.notification_spacing) * num_active - 40
        elif position == "top-left":
            x = 20
            y = 40 + (self.notification_height + self.notification_spacing) * (num_active - 1)
        else:
            # Default to bottom-right
            x = self.screen_width - self.notification_width - 20
            y = self.screen_height - (self.notification_height + self.notification_spacing) * num_active - 40
            
        # Make sure it's visible (don't go off screen)
        if y < 10:
            y = 10
        if y > self.screen_height - self.notification_height - 10:
            y = self.screen_height - self.notification_height - 10
            
        return (x, y)
        
    def _fade_in(self, window, step=0.1):
        """Fade in the notification window"""
        current_alpha = window.attributes('-alpha')
        
        if current_alpha < 0.9:
            window.attributes('-alpha', current_alpha + step)
            window.after(50, lambda: self._fade_in(window, step))
            
    def _fade_out(self, window, step=0.1, callback=None):
        """Fade out the notification window"""
        current_alpha = window.attributes('-alpha')
        
        if current_alpha > step:
            window.attributes('-alpha', current_alpha - step)
            window.after(50, lambda: self._fade_out(window, step, callback))
        else:
            if callback:
                callback()
                
    def _close_notification(self, notif_id):
        """Close a notification window"""
        if notif_id in self.active_notifications:
            window = self.active_notifications[notif_id]
            
            # Fade out then destroy
            self._fade_out(window, callback=lambda: self._destroy_notification(notif_id))
            
    def _destroy_notification(self, notif_id):
        """Destroy a notification window"""
        if notif_id in self.active_notifications:
            try:
                self.active_notifications[notif_id].destroy()
            except:
                pass
            del self.active_notifications[notif_id]
            
            # Adjust positions of remaining notifications
            self._reposition_notifications()
            
    def _reposition_notifications(self):
        """Reposition all active notifications"""
        # This would typically restack notifications after one is removed
        # For simplicity, not implemented in this version
        pass
        
    def _snooze_notification(self, notif_id):
        """Snooze a notification for later"""
        # Just close for now
        self._close_notification(notif_id)
        
    def _start_drag(self, event):
        """Start dragging the notification window"""
        window = event.widget.master  # Get the parent window
        window.drag_data["x"] = event.x
        window.drag_data["y"] = event.y
        window.drag_data["dragging"] = True
        
    def _stop_drag(self, event):
        """Stop dragging the notification window"""
        window = event.widget.master
        window.drag_data["dragging"] = False
        
    def _on_drag(self, event):
        """Handle window dragging"""
        window = event.widget.master
        
        if window.drag_data["dragging"]:
            x = window.winfo_x() - window.drag_data["x"] + event.x
            y = window.winfo_y() - window.drag_data["y"] + event.y
            window.geometry(f"+{x}+{y}")
        
    def add_notification(self, notification):
        """
        Add a notification to the queue
        
        Args:
            notification: Notification data dictionary
        """
        self.notification_queue.put(notification)
        logger.debug(f"Added notification to GUI queue: {notification.get('title')}")


class GUINotificationHandler:
    """
    Handler for GUI notifications that integrates with Jupiter's GUI
    """
    
    def __init__(self, gui_root=None):
        """
        Initialize GUI notification handler
        
        Args:
            gui_root: Tkinter root window from Jupiter GUI
        """
        self.notification_window = NotificationWindow(gui_root)
        self.logger = logger
        
    def handle_notification(self, notification):
        """
        Handle a calendar notification for GUI display
        
        Args:
            notification: Notification data dictionary
        """
        try:
            self.notification_window.add_notification(notification)
            return True
        except Exception as e:
            self.logger.error(f"Error handling GUI notification: {e}")
            return False
            
    def shutdown(self):
        """Stop the notification handler"""
        self.notification_window.stop()


# Function to get a notification handler to register with the manager
def get_notification_handler(gui_root=None):
    """
    Get a GUI notification handler
    
    Args:
        gui_root: Tkinter root window from Jupiter GUI
        
    Returns:
        Tuple of (handler_name, handler_function)
    """
    handler = GUINotificationHandler(gui_root)
    return ("gui", handler.handle_notification)