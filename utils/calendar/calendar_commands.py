import re
import os
import datetime
from pathlib import Path
from dateutil import parser as date_parser
from .calendar_manager import CalendarManager
from .formats.ical import ICalHandler
from .formats.csv_handler import CSVHandler

class CalendarCommands:
    """Handles parsing and processing of calendar-related commands"""
    
    def __init__(self, calendar_manager=None):
        """Initialize with a calendar manager instance"""
        self.calendar_manager = calendar_manager or CalendarManager()
        self.ical_handler = ICalHandler(self.calendar_manager)
        self.csv_handler = CSVHandler(self.calendar_manager)
        
        # Command patterns with their handlers
        self.commands = {
            r'add(?:\s+event)?\s+(.+?)\s+(?:on|at)\s+(.+?)(?:\s+(?:to|until)\s+(.+?))?(?:\s+(?:at|in)\s+(.+?))?(?:\s*$|\s+(.+)$)':
                self._handle_add_event,
            r'show\s+(?:events?|calendar)(?:\s+(?:for|on)\s+(.+?))?(?:\s*$|\s+(.+)$)':
                self._handle_show_events,
            r'(?:list|get)\s+(?:events?|calendar)(?:\s+(?:for|on)\s+(.+?))?(?:\s*$|\s+(.+)$)':
                self._handle_show_events,
            r'import\s+(?:events?|calendar)\s+(?:from\s+)?(.+?)(?:\s*$|\s+(.+)$)':
                self._handle_import,
            r'export\s+(?:events?|calendar)(?:\s+(?:to|as)\s+)?(.+?)(?:\s*$|\s+(.+)$)':
                self._handle_export
        }
    
    def process_command(self, user_id, command_text):
        """
        Process a calendar command
        
        Args:
            user_id (str): ID of the user issuing the command
            command_text (str): The command text to process
            
        Returns:
            str: Response message
        """
        # Remove the /calendar prefix if present
        if command_text.startswith('/calendar'):
            command_text = command_text[len('/calendar'):].strip()
            
        # Check for help command first
        if command_text.lower() in ['help', '?', '']:
            return self._get_help_text()
            
        # Check for preferences command
        elif command_text.lower() in ['preferences', 'settings', 'options']:
            return "To access calendar notification preferences in GUI mode, use the menu option or type '/calendar preferences' in the chat."
            
        # Try each command pattern
        for pattern, handler in self.commands.items():
            match = re.match(pattern, command_text, re.IGNORECASE)
            if match:
                try:
                    return handler(user_id, *match.groups())
                except Exception as e:
                    return f"Error processing calendar command: {str(e)}"
        
        # No matching command
        return "Sorry, I didn't understand that calendar command. Type '/calendar help' for available commands."
    
    def _get_help_text(self):
        """Get help text for calendar commands"""
        return """
Calendar Commands:

Add Events:
- /calendar add event Meeting with Team on tomorrow at 3:00 PM
- /calendar add Lunch with Lisa on Friday at 12:30 PM at Cafe Roma
- /calendar add Conference from 2023-07-15 to 2023-07-17

Show Events:
- /calendar show events
- /calendar show events for today
- /calendar show calendar for next week
- /calendar list events for July 15

Import/Export:
- /calendar import events from my_events.ics
- /calendar import calendar from work_schedule.csv
- /calendar export calendar to my_calendar.ics
- /calendar export events as personal_calendar.csv

Settings:
- /calendar preferences - Configure notification settings

For more detailed help, specify the command category:
- /calendar help add
- /calendar help show
- /calendar help import
"""
    
    def _handle_add_event(self, user_id, title, date_str, end_date_str=None, location=None, description=None):
        """Handle adding an event"""
        try:
            # Parse start date/time
            start_time = self._parse_time(date_str)
            if not start_time:
                return f"I couldn't understand the date/time: '{date_str}'. Please use a clearer format like 'tomorrow at 3pm' or '2023-07-15 15:00'."
            
            # Parse end date/time if provided
            end_time = None
            if end_date_str:
                end_time = self._parse_time(end_date_str)
                
                # If parsing fails or end is before start, set a default duration
                if not end_time or end_time < start_time:
                    # Default to 1 hour event
                    end_time = start_time + datetime.timedelta(hours=1)
            
            # Determine if it's an all-day event
            all_day = False
            if ' at ' not in date_str and (start_time.hour == 0 and start_time.minute == 0):
                all_day = True
                if not end_time:
                    # For all-day events, set end_time to the same day
                    end_time = start_time
                    
            # Create the event
            event_data = {
                'all_day': all_day
            }
            
            if location:
                event_data['location'] = location
                
            if description:
                event_data['description'] = description
                
            if end_time:
                event_id = self.calendar_manager.create_event(
                    user_id, title, start_time, end_time, **event_data
                )
            else:
                event_id = self.calendar_manager.create_event(
                    user_id, title, start_time, **event_data
                )
            
            if event_id:
                # Format a nice response
                time_str = self._format_time_for_display(start_time, all_day)
                end_str = ''
                
                if end_time and not all_day and end_time.date() != start_time.date():
                    end_str = f" until {self._format_time_for_display(end_time, False)}"
                    
                loc_str = f" at {location}" if location else ""
                    
                return f"Added event: '{title}' on {time_str}{end_str}{loc_str}"
            else:
                return "Sorry, I couldn't add that event. Please try again."
                
        except Exception as e:
            return f"Error adding event: {str(e)}"
    
    def _handle_show_events(self, user_id, date_str=None, extra_params=None):
        """Handle showing events"""
        try:
            # Default to today if no date specified
            if not date_str:
                date_str = 'today'
                
            # Parse the date/time range
            start_date, end_date = self._parse_date_range(date_str)
            
            if not start_date:
                return f"I couldn't understand the date: '{date_str}'. Please use a clearer format like 'today', 'next week', or '2023-07-15'."
                
            # Get events
            events = self.calendar_manager.get_events_by_daterange(user_id, start_date, end_date)
            
            if not events:
                date_range_str = self._format_date_range(start_date, end_date)
                return f"No events found for {date_range_str}."
                
            # Format the response
            date_range_str = self._format_date_range(start_date, end_date)
            response = f"Events for {date_range_str}:\n\n"
            
            # Group events by date
            events_by_date = {}
            for event in events:
                try:
                    event_date = datetime.datetime.fromisoformat(event['start_time']).date()
                    if event_date not in events_by_date:
                        events_by_date[event_date] = []
                    events_by_date[event_date].append(event)
                except (ValueError, KeyError):
                    # Skip events with invalid dates
                    continue
            
            # Sort dates
            sorted_dates = sorted(events_by_date.keys())
            
            # Format events by date
            for date in sorted_dates:
                date_events = events_by_date[date]
                response += f"**{date.strftime('%A, %B %d, %Y')}**\n"
                
                # Sort events by time
                date_events.sort(key=lambda e: e['start_time'])
                
                for event in date_events:
                    # Format time
                    time_str = "All day" if event.get('all_day') else datetime.datetime.fromisoformat(event['start_time']).strftime("%I:%M %p")
                    
                    # Format location
                    loc_str = f" at {event['location']}" if event.get('location') else ""
                    
                    response += f"- {time_str}: {event['title']}{loc_str}\n"
                
                response += "\n"
                
            return response
                
        except Exception as e:
            return f"Error showing events: {str(e)}"
    
    def _handle_import(self, user_id, file_path, extra_params=None):
        """Handle importing events"""
        try:
            # Validate and normalize file path
            if not file_path:
                return "Please specify a file to import."
                
            # Make path absolute if needed
            if not os.path.isabs(file_path):
                # Use a default location for imported files
                base_dir = Path(os.path.dirname(os.path.abspath(__file__))).parent.parent
                file_path = os.path.join(base_dir, file_path)
                
            # Check if file exists
            if not os.path.exists(file_path):
                return f"File not found: {file_path}"
                
            # Determine file type
            file_ext = os.path.splitext(file_path)[1].lower()
            
            if file_ext == '.ics':
                # Import iCalendar
                result = self.ical_handler.import_events(user_id, None, file_path)
            elif file_ext == '.csv':
                # Import CSV
                result = self.csv_handler.import_events(user_id, file_path)
            else:
                return f"Unsupported file format: {file_ext}. Please use .ics or .csv files."
                
            # Format response
            if result.get('success'):
                imported = result.get('imported', 0)
                failed = result.get('failed', 0)
                
                response = f"Successfully imported {imported} events from {os.path.basename(file_path)}."
                if failed > 0:
                    response += f" {failed} events could not be imported."
                    
                return response
            else:
                return f"Error importing events: {result.get('error', 'Unknown error')}"
                
        except Exception as e:
            return f"Error importing events: {str(e)}"
    
    def _handle_export(self, user_id, file_path, extra_params=None):
        """Handle exporting events"""
        try:
            # Validate file path
            if not file_path:
                return "Please specify a file path for export."
                
            # Make path absolute if needed
            if not os.path.isabs(file_path):
                # Use a default location for exported files
                base_dir = Path(os.path.dirname(os.path.abspath(__file__))).parent.parent
                file_path = os.path.join(base_dir, file_path)
                
            # Ensure directory exists
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
                
            # Get all events for the user (last year to next year)
            start_date = (datetime.datetime.now() - datetime.timedelta(days=365)).isoformat()
            end_date = (datetime.datetime.now() + datetime.timedelta(days=365)).isoformat()
            
            events = self.calendar_manager.get_events_by_daterange(user_id, start_date, end_date)
            
            if not events:
                return "No events found to export."
                
            # Determine file type
            file_ext = os.path.splitext(file_path)[1].lower()
            
            if file_ext == '.ics':
                # Export as iCalendar
                result = self.ical_handler.export_events(events, file_path)
            elif file_ext == '.csv':
                # Export as CSV
                result = self.csv_handler.export_events(events, file_path)
            else:
                return f"Unsupported file format: {file_ext}. Please use .ics or .csv extension."
                
            if result:
                return f"Successfully exported {len(events)} events to {os.path.basename(file_path)}."
            else:
                return "Error exporting events. Please try again."
                
        except Exception as e:
            return f"Error exporting events: {str(e)}"
    
    def _parse_time(self, time_str):
        """Parse a time string into a datetime object"""
        try:
            # Use dateutil parser for natural language date parsing
            return date_parser.parse(time_str)
        except Exception:
            return None
    
    def _parse_date_range(self, date_str):
        """Parse a date string into a start and end date range"""
        today = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Handle special keywords
        lower_date = date_str.lower()
        
        if lower_date in ['today', 'now']:
            return today.isoformat(), (today + datetime.timedelta(days=1) - datetime.timedelta(microseconds=1)).isoformat()
            
        elif lower_date == 'tomorrow':
            tomorrow = today + datetime.timedelta(days=1)
            return tomorrow.isoformat(), (tomorrow + datetime.timedelta(days=1) - datetime.timedelta(microseconds=1)).isoformat()
            
        elif lower_date == 'yesterday':
            yesterday = today - datetime.timedelta(days=1)
            return yesterday.isoformat(), (today - datetime.timedelta(microseconds=1)).isoformat()
            
        elif lower_date == 'this week':
            # Start of week (Monday)
            start = today - datetime.timedelta(days=today.weekday())
            # End of week (Sunday)
            end = start + datetime.timedelta(days=7) - datetime.timedelta(microseconds=1)
            return start.isoformat(), end.isoformat()
            
        elif lower_date == 'next week':
            # Start of next week (Monday)
            start = today + datetime.timedelta(days=7 - today.weekday())
            # End of next week (Sunday)
            end = start + datetime.timedelta(days=7) - datetime.timedelta(microseconds=1)
            return start.isoformat(), end.isoformat()
            
        elif lower_date == 'this month':
            # Start of month
            start = today.replace(day=1)
            # End of month
            if today.month == 12:
                end = today.replace(year=today.year + 1, month=1, day=1) - datetime.timedelta(microseconds=1)
            else:
                end = today.replace(month=today.month + 1, day=1) - datetime.timedelta(microseconds=1)
            return start.isoformat(), end.isoformat()
            
        elif lower_date == 'next month':
            # Start of next month
            if today.month == 12:
                start = today.replace(year=today.year + 1, month=1, day=1)
            else:
                start = today.replace(month=today.month + 1, day=1)
            # End of next month
            if start.month == 12:
                end = start.replace(year=start.year + 1, month=1, day=1) - datetime.timedelta(microseconds=1)
            else:
                end = start.replace(month=start.month + 1, day=1) - datetime.timedelta(microseconds=1)
            return start.isoformat(), end.isoformat()
            
        # Try to parse as a specific date
        try:
            date = date_parser.parse(date_str)
            # If only a date is specified (no time), assume the entire day
            if date.hour == 0 and date.minute == 0 and date.second == 0:
                end = date + datetime.timedelta(days=1) - datetime.timedelta(microseconds=1)
                return date.isoformat(), end.isoformat()
            else:
                # If a specific time is included, use a narrower range
                return date.isoformat(), date.isoformat()
        except Exception:
            # Couldn't parse the date
            return None, None
    
    def _format_date_range(self, start_date_str, end_date_str):
        """Format a date range for display"""
        try:
            start = datetime.datetime.fromisoformat(start_date_str)
            end = datetime.datetime.fromisoformat(end_date_str)
            
            # Same day?
            if start.date() == end.date():
                return start.strftime("%A, %B %d, %Y")
                
            # Same month and year?
            if start.year == end.year and start.month == end.month:
                return f"{start.strftime('%B %d')} - {end.strftime('%d, %Y')}"
                
            # Same year?
            if start.year == end.year:
                return f"{start.strftime('%B %d')} - {end.strftime('%B %d, %Y')}"
                
            # Different years
            return f"{start.strftime('%B %d, %Y')} - {end.strftime('%B %d, %Y')}"
            
        except (ValueError, TypeError):
            # Fallback
            return f"{start_date_str} to {end_date_str}"
    
    def _format_time_for_display(self, dt, all_day=False):
        """Format a datetime for user-friendly display"""
        if all_day:
            return dt.strftime("%A, %B %d, %Y")
        else:
            return dt.strftime("%A, %B %d, %Y at %I:%M %p")