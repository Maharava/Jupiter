import threading
import time
import datetime
import queue
import logging
import json
import os
import shutil
import tempfile
from pathlib import Path

# Set up logging
logger = logging.getLogger('jupiter.calendar.notifications')

# Import preferences (deferred to avoid circular imports)
try:
    from .preferences_ui import get_preferences
except ImportError:
    # Create a dummy preferences getter if UI not available
    def get_preferences():
        return None

class NotificationManager:
    """
    Manages calendar notifications and reminders
    
    This class handles periodic checking for pending calendar reminders
    and dispatches them through appropriate delivery methods.
    """
    
    def __init__(self, calendar_manager=None, check_interval=60):
        """
        Initialize the notification manager
        
        Args:
            calendar_manager: Calendar manager instance to check for reminders
            check_interval: How often to check for reminders (in seconds)
        """
        # Import here to avoid circular imports
        if calendar_manager is None:
            from .calendar_manager import CalendarManager
            calendar_manager = CalendarManager()
            
        self.calendar_manager = calendar_manager
        self.check_interval = check_interval
        
        # Initialize notification delivery methods
        self.delivery_methods = {}
        
        # Queue for pending notifications
        self.notification_queue = queue.Queue()
        
        # Flag to control the background thread
        self.running = False
        self.daemon_thread = None
        
        # Track delivered notifications to avoid duplicates
        self.notification_history_file = self._get_history_file_path()
        self.delivered_notifications = self._load_notification_history()
        
        # Track active notification methods
        self.active_methods = []
        
        # Last cleanup time
        self.last_cleanup_time = time.time()
        self.cleanup_interval = 24 * 60 * 60  # 24 hours in seconds
        self.retention_days = 30  # Keep notification history for 30 days by default
        
    def _get_history_file_path(self):
        """Get the path to the notification history file"""
        base_dir = Path(os.path.dirname(os.path.abspath(__file__))).parent.parent
        return os.path.join(base_dir, "calendar_notifications.json")
        
    def _load_notification_history(self):
        """Load notification history from file"""
        if os.path.exists(self.notification_history_file):
            try:
                with open(self.notification_history_file, 'r', encoding='utf-8') as f:
                    history = json.load(f)
                    
                # Clean old entries (older than retention period)
                self._clean_old_notifications(history)
                
                return history
            except (json.JSONDecodeError, IOError) as e:
                logger.error(f"Error loading notification history: {e}")
                return {}
        else:
            return {}
            
    def _clean_old_notifications(self, history=None):
        """
        Clean old notifications from history
        
        Args:
            history: Notification history dict to clean (or use self.delivered_notifications)
        
        Returns:
            dict: Cleaned history
        """
        if history is None:
            history = self.delivered_notifications
            
        # Get retention period from preferences if available
        prefs = get_preferences()
        retention_days = self.retention_days
        if prefs:
            retention_days = prefs.get_preference("notification_retention_days", self.retention_days)
            
        # Calculate cutoff timestamp
        cutoff_time = (datetime.datetime.now() - datetime.timedelta(days=retention_days)).timestamp()
        
        # Filter out old entries
        cleaned_history = {k: v for k, v in history.items() if v > cutoff_time}
        
        # If we removed entries, update the instance variable
        if len(cleaned_history) < len(history):
            logger.info(f"Cleaned {len(history) - len(cleaned_history)} old notifications from history")
            if history is self.delivered_notifications:
                self.delivered_notifications = cleaned_history
                
        return cleaned_history
            
    def _save_notification_history(self):
        """Save notification history to file"""
        # Clean old notifications before saving
        self._clean_old_notifications()
        
        # Create a temporary file first (atomic write)
        try:
            fd, temp_path = tempfile.mkstemp(dir=os.path.dirname(self.notification_history_file))
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                json.dump(self.delivered_notifications, f)
                
            # Replace the original file with the temporary file
            shutil.move(temp_path, self.notification_history_file)
            
        except IOError as e:
            logger.error(f"Error saving notification history: {e}")
            # Try to clean up temporary file if it exists
            try:
                if 'temp_path' in locals() and os.path.exists(temp_path):
                    os.unlink(temp_path)
            except:
                pass
    
    def register_delivery_method(self, method_name, delivery_callback):
        """
        Register a notification delivery method
        
        Args:
            method_name: Name of the delivery method (e.g., 'gui', 'terminal')
            delivery_callback: Function to call with notification data
        """
        self.delivery_methods[method_name] = delivery_callback
        self.active_methods.append(method_name)
        logger.info(f"Registered notification delivery method: {method_name}")
        
    def unregister_delivery_method(self, method_name):
        """
        Unregister a notification delivery method
        
        Args:
            method_name: Name of the delivery method to unregister
        """
        if method_name in self.delivery_methods:
            del self.delivery_methods[method_name]
            
        if method_name in self.active_methods:
            self.active_methods.remove(method_name)
            
        logger.info(f"Unregistered notification delivery method: {method_name}")
        
    def start(self):
        """Start the notification daemon thread"""
        if self.running:
            logger.warning("Notification manager is already running")
            return
            
        self.running = True
        self.daemon_thread = threading.Thread(
            target=self._notification_daemon,
            daemon=True,
            name="JupiterCalendarNotifier"
        )
        self.daemon_thread.start()
        logger.info("Calendar notification manager started")
        
    def stop(self):
        """Stop the notification daemon thread"""
        if not self.running:
            return
            
        self.running = False
        if self.daemon_thread:
            # Wait for thread to finish (with timeout)
            self.daemon_thread.join(timeout=2.0)
            self.daemon_thread = None
            
        # Save notification history when stopping
        self._save_notification_history()
        logger.info("Calendar notification manager stopped")
        
    def _notification_daemon(self):
        """Background thread to check for and deliver notifications"""
        logger.info("Notification daemon started")
        
        while self.running:
            try:
                # Check for new reminders
                self._check_reminders()
                
                # Process notification queue
                self._process_queue()
                
                # Periodically clean up old notification history
                current_time = time.time()
                if current_time - self.last_cleanup_time > self.cleanup_interval:
                    self._run_scheduled_cleanup()
                    self.last_cleanup_time = current_time
                
                # Sleep until next check
                for _ in range(int(self.check_interval)):
                    if not self.running:
                        break
                    time.sleep(1)
                    
            except Exception as e:
                logger.error(f"Error in notification daemon: {e}")
                # Sleep a bit before retrying after an error
                time.sleep(5)
                
        logger.info("Notification daemon stopped")
        
    def _run_scheduled_cleanup(self):
        """Run scheduled cleanup tasks"""
        try:
            # Clean old notifications
            original_count = len(self.delivered_notifications)
            self._clean_old_notifications()
            new_count = len(self.delivered_notifications)
            
            if original_count != new_count:
                # Save the cleaned history
                self._save_notification_history()
                logger.info(f"Removed {original_count - new_count} expired notifications during scheduled cleanup")
        except Exception as e:
            logger.error(f"Error during scheduled cleanup: {e}")
        
    def _check_reminders(self):
        """Check for pending reminders and add to queue"""
        try:
            # Get pending reminders from calendar manager
            reminders = self.calendar_manager.get_pending_reminders()
            
            if not reminders:
                return
                
            # Process each reminder
            for reminder in reminders:
                reminder_id = reminder.get('reminder_id')
                
                # Skip if already delivered
                if reminder_id in self.delivered_notifications:
                    continue
                    
                # Format notification
                notification = {
                    'id': reminder_id,
                    'title': f"Reminder: {reminder.get('event_title', 'Event')}",
                    'message': self._format_reminder_message(reminder),
                    'event_id': reminder.get('event_id'),
                    'user_id': reminder.get('user_id'),
                    'timestamp': datetime.datetime.now().timestamp()
                }
                
                # Add to queue
                self.notification_queue.put(notification)
                
                # Mark as delivered to avoid duplicates
                self.delivered_notifications[reminder_id] = notification['timestamp']
                
                # Mark the reminder as delivered in the database
                self.calendar_manager.mark_reminder_delivered(reminder_id)
                
        except Exception as e:
            logger.error(f"Error checking reminders: {e}")
            
    def _format_reminder_message(self, reminder):
        """Format a reminder notification message"""
        try:
            event_title = reminder.get('event_title', 'Event')
            
            # Get the event details for more information
            event = self.calendar_manager.get_event(
                reminder.get('user_id'), 
                reminder.get('event_id')
            )
            
            if not event:
                return f"Reminder for: {event_title}"
                
            # Format time
            start_time = None
            try:
                start_time = datetime.datetime.fromisoformat(event.get('start_time', ''))
                time_format = "%I:%M %p" if not event.get('all_day') else ""
                date_format = "%A, %B %d"
                
                if time_format:
                    formatted_time = start_time.strftime(f"{date_format} at {time_format}")
                else:
                    formatted_time = start_time.strftime(date_format)
            except (ValueError, TypeError):
                formatted_time = "upcoming"
                
            # Format location
            location = f" at {event['location']}" if event.get('location') else ""
                
            return f"Reminder for: {event_title}{location} on {formatted_time}"
            
        except Exception as e:
            logger.error(f"Error formatting reminder message: {e}")
            return f"Reminder for calendar event"
            
    def _process_queue(self):
        """Process the notification queue"""
        # Limit how many notifications to process at once
        max_process = 10
        processed = 0
        
        while not self.notification_queue.empty() and processed < max_process:
            try:
                notification = self.notification_queue.get_nowait()
                self._deliver_notification(notification)
                self.notification_queue.task_done()
                processed += 1
            except queue.Empty:
                break
            except Exception as e:
                logger.error(f"Error processing notification queue: {e}")
                break
                
    def _deliver_notification(self, notification):
        """Deliver a notification through all active methods"""
        if not self.active_methods:
            logger.warning("No active notification delivery methods")
            return
            
        delivered = False
        prefs = get_preferences()
        
        # Try each active delivery method
        for method_name in self.active_methods:
            # Skip if this method is disabled in preferences
            if prefs:
                method_pref = f"{method_name}_notifications"
                if not prefs.get_preference(method_pref, True):
                    logger.debug(f"Skipping {method_name} notifications (disabled in preferences)")
                    continue
                    
            if method_name in self.delivery_methods:
                try:
                    self.delivery_methods[method_name](notification)
                    delivered = True
                except Exception as e:
                    logger.error(f"Error delivering notification via {method_name}: {e}")
                    
        if delivered:
            logger.info(f"Delivered notification: {notification.get('title')}")
        else:
            logger.warning(f"Failed to deliver notification: {notification.get('title')}")
            
    def get_upcoming_notifications(self, user_id, minutes=15):
        """
        Get upcoming notifications within the next X minutes
        
        Args:
            user_id: ID of the user
            minutes: Minutes to look ahead
            
        Returns:
            List of upcoming events with notifications
        """
        # Current time
        now = datetime.datetime.now()
        
        # End time for the window
        end_time = now + datetime.timedelta(minutes=minutes)
        
        # Get events in this time window
        events = self.calendar_manager.get_events_by_daterange(
            user_id, 
            now.isoformat(), 
            end_time.isoformat()
        )
        
        # Format as notification previews
        previews = []
        
        for event in events:
            try:
                # Format time
                start_time = datetime.datetime.fromisoformat(event.get('start_time', ''))
                minutes_until = max(0, int((start_time - now).total_seconds() / 60))
                
                if minutes_until == 0:
                    time_str = "now"
                elif minutes_until == 1:
                    time_str = "in 1 minute"
                else:
                    time_str = f"in {minutes_until} minutes"
                    
                # Create preview
                preview = {
                    'title': event.get('title'),
                    'time': time_str,
                    'minutes_until': minutes_until,
                    'start_time': event.get('start_time'),
                    'location': event.get('location', '')
                }
                
                previews.append(preview)
                
            except (ValueError, TypeError) as e:
                logger.error(f"Error creating notification preview: {e}")
                
        # Sort by time (soonest first)
        previews.sort(key=lambda x: x.get('minutes_until', 0))
        
        return previews
        
    def dismiss_notification(self, notification_id):
        """
        Dismiss a notification by ID
        
        Args:
            notification_id: ID of the notification to dismiss
            
        Returns:
            bool: Success or failure
        """
        # Mark as delivered if not already
        if notification_id not in self.delivered_notifications:
            self.delivered_notifications[notification_id] = datetime.datetime.now().timestamp()
            self._save_notification_history()
            
        return True
        
    def snooze_notification(self, notification_id, minutes=5):
        """
        Snooze a notification for a number of minutes
        
        Args:
            notification_id: ID of the notification to snooze
            minutes: Minutes to snooze for
            
        Returns:
            bool: Success or failure
        """
        # Remove from delivered list if present
        if notification_id in self.delivered_notifications:
            del self.delivered_notifications[notification_id]
            
        # Re-queue for later (not implemented in this version)
        # Would require modifying the reminder in the database
        
        return True