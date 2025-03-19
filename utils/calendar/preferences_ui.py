import tkinter as tk
from tkinter import ttk
import json
import os
import logging
from pathlib import Path

logger = logging.getLogger('jupiter.calendar.preferences')

class NotificationPreferences:
    """
    Manages notification preferences for Jupiter Calendar
    """
    
    DEFAULT_PREFERENCES = {
        "gui_notifications": True,
        "terminal_notifications": True,
        "voice_notifications": True,
        "notification_duration": 10,  # seconds
        "default_reminder_minutes": 15,
        "auto_add_reminders": True,
        "notification_position": "bottom-right",  # "bottom-right", "top-right", "top-left", "bottom-left"
        "play_sound": True
    }
    
    def __init__(self):
        """Initialize notification preferences"""
        self.prefs_file = self._get_preferences_file()
        self.preferences = self._load_preferences()
        
    def _get_preferences_file(self):
        """Get the path to the preferences file"""
        base_dir = Path(os.path.dirname(os.path.abspath(__file__))).parent.parent
        return os.path.join(base_dir, "calendar_preferences.json")
    
    def _load_preferences(self):
        """Load preferences from file or use defaults"""
        if os.path.exists(self.prefs_file):
            try:
                with open(self.prefs_file, 'r', encoding='utf-8') as f:
                    prefs = json.load(f)
                    
                # Ensure all default preferences exist
                for key, value in self.DEFAULT_PREFERENCES.items():
                    if key not in prefs:
                        prefs[key] = value
                        
                return prefs
            except Exception as e:
                logger.error(f"Error loading notification preferences: {e}")
                return self.DEFAULT_PREFERENCES.copy()
        else:
            return self.DEFAULT_PREFERENCES.copy()
    
    def save_preferences(self):
        """Save preferences to file"""
        try:
            with open(self.prefs_file, 'w', encoding='utf-8') as f:
                json.dump(self.preferences, f, indent=4)
            return True
        except Exception as e:
            logger.error(f"Error saving notification preferences: {e}")
            return False
    
    def get_preference(self, key, default=None):
        """Get a specific preference value"""
        return self.preferences.get(key, default)
    
    def set_preference(self, key, value):
        """Set a specific preference value"""
        self.preferences[key] = value
        return self.save_preferences()
    
    def show_preferences_dialog(self, parent):
        """Show the preferences dialog"""
        PreferencesDialog(parent, self)


class PreferencesDialog:
    """Dialog for editing notification preferences"""
    
    def __init__(self, parent, preferences):
        """Initialize the preferences dialog"""
        self.parent = parent
        self.preferences = preferences
        
        # Create dialog window
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Calendar Notification Preferences")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Set dialog size and position
        window_width = 450
        window_height = 500
        screen_width = parent.winfo_screenwidth()
        screen_height = parent.winfo_screenheight()
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        self.dialog.geometry(f"{window_width}x{window_height}+{x}+{y}")
        
        # Add padding to the dialog
        self.dialog.configure(padx=20, pady=20)
        
        # Create UI elements
        self._create_widgets()
        
        # Center dialog on parent window
        self.dialog.update_idletasks()
        self.dialog.focus_set()
    
    def _create_widgets(self):
        """Create the UI widgets"""
        # Main frame with padding
        main_frame = ttk.Frame(self.dialog, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label = ttk.Label(
            main_frame, 
            text="Calendar Notification Settings",
            font=("Arial", 16, "bold")
        )
        title_label.pack(pady=(0, 20))
        
        # Create notebook for tabs
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # General settings tab
        general_tab = ttk.Frame(notebook, padding=10)
        notebook.add(general_tab, text="General")
        self._create_general_tab(general_tab)
        
        # Notification settings tab
        notif_tab = ttk.Frame(notebook, padding=10)
        notebook.add(notif_tab, text="Notifications")
        self._create_notification_tab(notif_tab)
        
        # Reminder settings tab
        reminder_tab = ttk.Frame(notebook, padding=10)
        notebook.add(reminder_tab, text="Reminders")
        self._create_reminder_tab(reminder_tab)
        
        # Button frame
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(20, 0))
        
        # Save button
        save_button = ttk.Button(
            button_frame,
            text="Save",
            command=self._save_preferences
        )
        save_button.pack(side=tk.RIGHT, padx=5)
        
        # Cancel button
        cancel_button = ttk.Button(
            button_frame,
            text="Cancel",
            command=self.dialog.destroy
        )
        cancel_button.pack(side=tk.RIGHT, padx=5)
    
    def _create_general_tab(self, parent):
        """Create general settings tab"""
        # Frame for general settings
        frame = ttk.LabelFrame(parent, text="General Settings", padding=10)
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Notification position
        position_frame = ttk.Frame(frame)
        position_frame.pack(fill=tk.X, pady=5)
        
        position_label = ttk.Label(position_frame, text="Notification Position:")
        position_label.pack(side=tk.LEFT)
        
        # Get current position
        current_position = self.preferences.get_preference("notification_position", "bottom-right")
        
        # Position options
        self.position_var = tk.StringVar(value=current_position)
        positions = [
            ("Bottom Right", "bottom-right"),
            ("Top Right", "top-right"),
            ("Bottom Left", "bottom-left"),
            ("Top Left", "top-left")
        ]
        
        # Position dropdown
        position_combo = ttk.Combobox(
            position_frame,
            textvariable=self.position_var,
            values=[p[0] for p in positions],
            state="readonly",
            width=15
        )
        position_combo.pack(side=tk.RIGHT)
        
        # Map display names to values
        self.position_map = {p[0]: p[1] for p in positions}
        self.reverse_position_map = {p[1]: p[0] for p in positions}
        
        # Set the current value display name
        if current_position in self.reverse_position_map:
            position_combo.set(self.reverse_position_map[current_position])
        
        # Sound setting
        sound_frame = ttk.Frame(frame)
        sound_frame.pack(fill=tk.X, pady=5)
        
        # Sound checkbox
        sound_value = self.preferences.get_preference("play_sound", True)
        self.sound_var = tk.BooleanVar(value=sound_value)
        sound_check = ttk.Checkbutton(
            sound_frame,
            text="Play sound with notifications",
            variable=self.sound_var
        )
        sound_check.pack(fill=tk.X)
    
    def _create_notification_tab(self, parent):
        """Create notification settings tab"""
        # Frame for notification types
        types_frame = ttk.LabelFrame(parent, text="Notification Types", padding=10)
        types_frame.pack(fill=tk.X, pady=(0, 10))
        
        # GUI notifications
        gui_value = self.preferences.get_preference("gui_notifications", True)
        self.gui_var = tk.BooleanVar(value=gui_value)
        gui_check = ttk.Checkbutton(
            types_frame,
            text="Show popup notifications in GUI",
            variable=self.gui_var
        )
        gui_check.pack(fill=tk.X, pady=2)
        
        # Terminal notifications
        terminal_value = self.preferences.get_preference("terminal_notifications", True)
        self.terminal_var = tk.BooleanVar(value=terminal_value)
        terminal_check = ttk.Checkbutton(
            types_frame,
            text="Show notifications in terminal",
            variable=self.terminal_var
        )
        terminal_check.pack(fill=tk.X, pady=2)
        
        # Voice notifications
        voice_value = self.preferences.get_preference("voice_notifications", True)
        self.voice_var = tk.BooleanVar(value=voice_value)
        voice_check = ttk.Checkbutton(
            types_frame,
            text="Enable voice announcements",
            variable=self.voice_var
        )
        voice_check.pack(fill=tk.X, pady=2)
        
        # Frame for notification behavior
        behavior_frame = ttk.LabelFrame(parent, text="Notification Behavior", padding=10)
        behavior_frame.pack(fill=tk.X)
        
        # Duration slider
        duration_frame = ttk.Frame(behavior_frame)
        duration_frame.pack(fill=tk.X, pady=5)
        
        duration_label = ttk.Label(duration_frame, text="Notification Duration:")
        duration_label.pack(side=tk.LEFT)
        
        duration_value = self.preferences.get_preference("notification_duration", 10)
        self.duration_var = tk.IntVar(value=duration_value)
        
        duration_scale = ttk.Scale(
            duration_frame,
            from_=5,
            to=30,
            orient=tk.HORIZONTAL,
            variable=self.duration_var
        )
        duration_scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # Display the current value
        self.duration_value_label = ttk.Label(duration_frame, text=f"{duration_value} seconds")
        self.duration_value_label.pack(side=tk.RIGHT)
        
        # Update label when slider changes
        def update_duration_label(*args):
            self.duration_value_label.config(text=f"{self.duration_var.get()} seconds")
        
        self.duration_var.trace('w', update_duration_label)
    
    def _create_reminder_tab(self, parent):
        """Create reminder settings tab"""
        # Frame for reminder settings
        reminder_frame = ttk.LabelFrame(parent, text="Reminder Settings", padding=10)
        reminder_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Auto-add reminders
        auto_value = self.preferences.get_preference("auto_add_reminders", True)
        self.auto_var = tk.BooleanVar(value=auto_value)
        auto_check = ttk.Checkbutton(
            reminder_frame,
            text="Automatically add reminders to new events",
            variable=self.auto_var
        )
        auto_check.pack(fill=tk.X, pady=2)
        
        # Default reminder time
        time_frame = ttk.Frame(reminder_frame)
        time_frame.pack(fill=tk.X, pady=5)
        
        time_label = ttk.Label(time_frame, text="Default Reminder Time:")
        time_label.pack(side=tk.LEFT)
        
        default_minutes = self.preferences.get_preference("default_reminder_minutes", 15)
        self.default_minutes_var = tk.IntVar(value=default_minutes)
        
        # Common reminder times
        reminder_times = [
            ("5 minutes", 5),
            ("10 minutes", 10),
            ("15 minutes", 15),
            ("30 minutes", 30),
            ("1 hour", 60),
            ("2 hours", 120),
            ("1 day", 1440)
        ]
        
        # Reminder dropdown
        time_combo = ttk.Combobox(
            time_frame,
            textvariable=self.default_minutes_var,
            values=[t[0] for t in reminder_times],
            state="readonly",
            width=15
        )
        time_combo.pack(side=tk.RIGHT)
        
        # Map display names to values
        self.time_map = {t[0]: t[1] for t in reminder_times}
        self.reverse_time_map = {t[1]: t[0] for t in reminder_times}
        
        # Set the current value display name
        if default_minutes in self.reverse_time_map:
            time_combo.set(self.reverse_time_map[default_minutes])
    
    def _save_preferences(self):
        """Save preferences and close dialog"""
        try:
            # Save notification types
            self.preferences.set_preference("gui_notifications", self.gui_var.get())
            self.preferences.set_preference("terminal_notifications", self.terminal_var.get())
            self.preferences.set_preference("voice_notifications", self.voice_var.get())
            
            # Save notification behavior
            self.preferences.set_preference("notification_duration", self.duration_var.get())
            
            # Save position
            position_display = self.position_var.get()
            if position_display in self.position_map:
                self.preferences.set_preference("notification_position", self.position_map[position_display])
            else:
                # Directly use the value if it's not a display name
                self.preferences.set_preference("notification_position", position_display)
            
            # Save sound setting
            self.preferences.set_preference("play_sound", self.sound_var.get())
            
            # Save reminder settings
            self.preferences.set_preference("auto_add_reminders", self.auto_var.get())
            
            # Save default reminder time
            default_minutes_display = self.default_minutes_var.get()
            if isinstance(default_minutes_display, str) and default_minutes_display in self.time_map:
                self.preferences.set_preference("default_reminder_minutes", self.time_map[default_minutes_display])
            else:
                # Use the direct value (which might be an integer)
                self.preferences.set_preference("default_reminder_minutes", default_minutes_display)
            
            # Save all changes
            self.preferences.save_preferences()
            
            # Close dialog
            self.dialog.destroy()
            
        except Exception as e:
            logger.error(f"Error saving preferences: {e}")
            # Show error message
            tk.messagebox.showerror(
                "Error Saving Preferences",
                f"An error occurred while saving preferences: {str(e)}"
            )


# Singleton instance
_preferences = None

def get_preferences():
    """Get the notification preferences singleton instance"""
    global _preferences
    if _preferences is None:
        _preferences = NotificationPreferences()
    return _preferences

def show_preferences_dialog(parent):
    """Show the notification preferences dialog"""
    prefs = get_preferences()
    prefs.show_preferences_dialog(parent)
