import datetime
import json
from .calendar_storage import CalendarStorage

class CalendarManager:
    """Manages calendar operations for Jupiter"""
    
    def __init__(self, storage=None):
        """Initialize the calendar manager with storage"""
        self.storage = storage or CalendarStorage()
    
    # Event CRUD Operations
    
    def create_event(self, user_id, title, start_time, end_time=None, **kwargs):
        """
        Create a new calendar event
        
        Args:
            user_id (str): ID of the user creating the event
            title (str): Event title
            start_time (str/datetime): Event start time
            end_time (str/datetime, optional): Event end time
            **kwargs: Additional event properties
                - description (str): Event description
                - location (str): Event location
                - all_day (bool): Whether this is an all-day event
                - recurrence (dict): Recurrence pattern
                - privacy_level (str): Privacy level ('private', 'shared', 'public')
                - reminders (list): List of reminder objects
                
        Returns:
            str: ID of the created event or None if failed
        """
        # Ensure times are in ISO format
        if isinstance(start_time, datetime.datetime):
            start_time = start_time.isoformat()
            
        if isinstance(end_time, datetime.datetime):
            end_time = end_time.isoformat()
        elif end_time is None and not kwargs.get('all_day', False):
            # Default to 1 hour event if end time not specified
            try:
                dt_start = datetime.datetime.fromisoformat(start_time)
                end_time = (dt_start + datetime.timedelta(hours=1)).isoformat()
            except ValueError:
                # Couldn't parse start_time, will let storage layer handle it
                pass
                
        # Prepare event data
        event_data = {
            'title': title,
            'start_time': start_time,
            'end_time': end_time,
            **kwargs
        }
        
        # Create event in storage
        return self.storage.add_event(event_data, user_id)
    
    def update_event(self, user_id, event_id, **updates):
        """
        Update an existing event
        
        Args:
            user_id (str): ID of the user updating the event
            event_id (str): ID of the event to update
            **updates: Fields to update
                
        Returns:
            bool: True if update was successful, False otherwise
        """
        # Convert datetime objects to ISO strings
        for key, value in updates.items():
            if isinstance(value, datetime.datetime):
                updates[key] = value.isoformat()
                
        return self.storage.update_event(event_id, updates, user_id)
    
    def delete_event(self, user_id, event_id):
        """
        Delete an event
        
        Args:
            user_id (str): ID of the user deleting the event
            event_id (str): ID of the event to delete
                
        Returns:
            bool: True if deletion was successful, False otherwise
        """
        return self.storage.delete_event(event_id, user_id)
    
    def get_event(self, user_id, event_id):
        """
        Get a specific event by ID
        
        Args:
            user_id (str): ID of the user requesting the event
            event_id (str): ID of the event to retrieve
                
        Returns:
            dict: Event data or None if not found or not authorized
        """
        event = self.storage.get_event(event_id, user_id)
        if event:
            return self._process_event_recurrence(event)
        return None
    
    # Query Methods
    
    def get_events_by_date(self, user_id, date):
        """
        Get events for a specific date
        
        Args:
            user_id (str): ID of the user
            date (str/datetime.date): The date to get events for
                
        Returns:
            list: List of events on the given date
        """
        if isinstance(date, datetime.date):
            date_obj = date
        else:
            # Parse string date
            date_obj = datetime.date.fromisoformat(date)
            
        # Convert to datetime range for the whole day
        start_date = datetime.datetime.combine(date_obj, datetime.time.min).isoformat()
        end_date = datetime.datetime.combine(date_obj, datetime.time.max).isoformat()
        
        events = self.storage.get_events_by_daterange(user_id, start_date, end_date)
        return self._process_recurrences(events)
    
    def get_events_by_daterange(self, user_id, start_date, end_date):
        """
        Get events within a date range
        
        Args:
            user_id (str): ID of the user
            start_date (str/datetime): Start of date range
            end_date (str/datetime): End of date range
                
        Returns:
            list: List of events within the date range
        """
        # Convert to ISO strings if needed
        if isinstance(start_date, (datetime.date, datetime.datetime)):
            start_date = start_date.isoformat()
            
        if isinstance(end_date, (datetime.date, datetime.datetime)):
            end_date = end_date.isoformat()
            
        events = self.storage.get_events_by_daterange(user_id, start_date, end_date)
        return self._process_recurrences(events)
    
    def get_upcoming_events(self, user_id, days=7):
        """
        Get upcoming events for a user
        
        Args:
            user_id (str): ID of the user
            days (int): Number of days to look ahead
                
        Returns:
            list: List of upcoming events
        """
        events = self.storage.get_upcoming_events(user_id, days)
        return self._process_recurrences(events)
    
    def search_events(self, user_id, query, start_date=None, end_date=None):
        """
        Search for events by title or description
        
        Args:
            user_id (str): ID of the user
            query (str): Search term
            start_date (str/datetime, optional): Start date for search range
            end_date (str/datetime, optional): End date for search range
                
        Returns:
            list: List of matching events
        """
        # This is a simple implementation. For a more advanced search,
        # we might want to add a dedicated search method to the storage class.
        
        # Get events within date range (or all events if no range specified)
        if not start_date:
            start_date = datetime.datetime(1900, 1, 1).isoformat()
        elif isinstance(start_date, (datetime.date, datetime.datetime)):
            start_date = start_date.isoformat()
            
        if not end_date:
            end_date = datetime.datetime(2100, 1, 1).isoformat() 
        elif isinstance(end_date, (datetime.date, datetime.datetime)):
            end_date = end_date.isoformat()
        
        events = self.storage.get_events_by_daterange(user_id, start_date, end_date)
        
        # Filter by search term
        query = query.lower()
        filtered_events = []
        
        for event in events:
            if (query in event.get('title', '').lower() or 
                query in event.get('description', '').lower() or
                query in event.get('location', '').lower()):
                filtered_events.append(event)
                
        return self._process_recurrences(filtered_events)
    
    # Recurrence Handling
    
    def _process_recurrences(self, events):
        """Process recurring events in a list of events"""
        processed_events = []
        for event in events:
            processed_events.append(self._process_event_recurrence(event))
        return processed_events
    
    def _process_event_recurrence(self, event):
        """Process recurrence information for an event"""
        # This is a placeholder - in a full implementation, this would 
        # expand recurring events into their individual instances within
        # the requested date range.
        
        # For now, we just make sure the recurrence data is properly formatted
        if event.get('recurrence'):
            if isinstance(event['recurrence'], str):
                try:
                    event['recurrence'] = json.loads(event['recurrence'])
                except json.JSONDecodeError:
                    event['recurrence'] = None
        return event
    
    # Sharing & Collaboration
    
    def share_event(self, owner_id, event_id, shared_user_id):
        """
        Share an event with another user
        
        Args:
            owner_id (str): ID of the user sharing the event
            event_id (str): ID of the event to share
            shared_user_id (str): ID of the user to share with
                
        Returns:
            bool: True if sharing was successful, False otherwise
        """
        return self.storage.share_event(event_id, owner_id, shared_user_id)
    
    # Calendar Analysis
    
    def get_schedule_density(self, user_id, days=7):
        """
        Calculate how busy a user's schedule is
        
        Args:
            user_id (str): ID of the user
            days (int): Number of days to analyze
                
        Returns:
            float: Schedule density (0.0 to 1.0, higher means busier)
        """
        # Get upcoming events
        events = self.get_upcoming_events(user_id, days)
        
        # Base metrics - a certain number of events per day makes a "full" schedule
        events_per_full_day = 5
        hours_per_full_day = 8
        
        # Calculate density based on event count and duration
        total_hours = 0
        total_events = len(events)
        
        for event in events:
            # Skip all-day events as they're counted separately
            if event.get('all_day'):
                total_hours += 8  # Count all-day events as 8 hours
                continue
                
            # Calculate event duration
            try:
                start_time = datetime.datetime.fromisoformat(event['start_time'])
                
                if event.get('end_time'):
                    end_time = datetime.datetime.fromisoformat(event['end_time'])
                    duration = (end_time - start_time).total_seconds() / 3600
                    total_hours += min(duration, 24)  # Cap at 24 hours per event
            except (ValueError, TypeError):
                # Fallback if we can't parse the times
                total_hours += 1  # Assume 1 hour
        
        # Calculate density components (0.0 to 1.0)
        event_density = min(1.0, total_events / (days * events_per_full_day))
        hour_density = min(1.0, total_hours / (days * hours_per_full_day))
        
        # Combined density (weighted average)
        combined_density = (event_density * 0.4) + (hour_density * 0.6)
        
        return combined_density
    
    def is_time_available(self, user_id, proposed_time, duration_minutes=60):
        """
        Check if a user is available at a proposed time
        
        Args:
            user_id (str): ID of the user
            proposed_time (str/datetime): Proposed start time
            duration_minutes (int): Duration of the proposed event in minutes
                
        Returns:
            bool: True if time is available, False if there's a conflict
        """
        if isinstance(proposed_time, datetime.datetime):
            proposed_time = proposed_time.isoformat()
            
        return self.storage.is_time_available(user_id, proposed_time, duration_minutes)
    
    # Reminder Management
    
    def get_pending_reminders(self):
        """
        Get reminders that are due to be delivered
        
        Returns:
            list: List of reminders to be delivered
        """
        return self.storage.get_pending_reminders()
    
    def mark_reminder_delivered(self, reminder_id):
        """
        Mark a reminder as delivered
        
        Args:
            reminder_id (str): ID of the reminder
                
        Returns:
            bool: True if successful, False otherwise
        """
        return self.storage.mark_reminder_delivered(reminder_id)

    def add_default_reminder(self, event_id, minutes_before=15):
        """
        Add a default reminder to an event
        
        Args:
            event_id (str): ID of the event
            minutes_before (int): Minutes before the event to trigger reminder
            
        Returns:
            bool: Success or failure
        """
        try:
            # Get the event
            event = self.storage.get_event(event_id, None)  # Admin access
            
            if not event:
                return False
                
            # Calculate reminder time
            start_time = datetime.datetime.fromisoformat(event['start_time'])
            reminder_time = start_time - datetime.timedelta(minutes=minutes_before)
            
            # Add reminder
            reminder_id = str(uuid.uuid4())
            success = self.storage.add_reminder(
                reminder_id,
                event_id,
                reminder_time.isoformat(),
                "notification"
            )
            
            return success
            
        except Exception as e:
            logger.error(f"Error adding default reminder: {e}")
            return False