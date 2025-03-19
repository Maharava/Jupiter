import datetime
import uuid
import re
from pathlib import Path

class ICalHandler:
    """Handles import and export of iCalendar (ICS) files"""
    
    def __init__(self, calendar_manager):
        """Initialize with a reference to the calendar manager"""
        self.calendar_manager = calendar_manager
    
    def export_events(self, events, output_path=None):
        """
        Export events to iCalendar format
        
        Args:
            events (list): List of events to export
            output_path (str, optional): Path to save the file (if None, returns string)
            
        Returns:
            str: iCalendar formatted string (if output_path is None)
                 or path to the saved file
        """
        # Create iCalendar content
        ical_content = [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PRODID:-//Jupiter//Calendar//EN",
            "CALSCALE:GREGORIAN",
            "METHOD:PUBLISH"
        ]
        
        # Add each event
        for event in events:
            event_content = self._format_event(event)
            ical_content.extend(event_content)
            
        # Finalize content
        ical_content.append("END:VCALENDAR")
        
        # Join lines and ensure proper line endings
        ical_string = "\r\n".join(ical_content) + "\r\n"
        
        # Save to file if path provided
        if output_path:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(ical_string)
            return str(output_path)
            
        # Return content string otherwise
        return ical_string
    
    def _format_event(self, event):
        """Format a single event for iCalendar"""
        ical_event = [
            "BEGIN:VEVENT",
            f"UID:{event.get('event_id', str(uuid.uuid4()))}",
            f"SUMMARY:{self._escape_text(event['title'])}"
        ]
        
        # Handle dates
        try:
            start = datetime.datetime.fromisoformat(event['start_time'])
            
            # Handle all-day events
            if event.get('all_day'):
                ical_event.append(f"DTSTART;VALUE=DATE:{start.strftime('%Y%m%d')}")
                
                # For all-day events, the end date should be the day after
                # (because iCal end dates are exclusive)
                if event.get('end_time'):
                    end = datetime.datetime.fromisoformat(event['end_time'])
                    # Add a day unless it's already the next day or later
                    if end.date() <= start.date():
                        end = start + datetime.timedelta(days=1)
                else:
                    end = start + datetime.timedelta(days=1)
                    
                ical_event.append(f"DTEND;VALUE=DATE:{end.strftime('%Y%m%d')}")
            else:
                # Regular event with time
                ical_event.append(f"DTSTART:{start.strftime('%Y%m%dT%H%M%SZ')}")
                
                if event.get('end_time'):
                    end = datetime.datetime.fromisoformat(event['end_time'])
                    ical_event.append(f"DTEND:{end.strftime('%Y%m%dT%H%M%SZ')}")
                else:
                    # Default to 1 hour if no end time specified
                    end = start + datetime.timedelta(hours=1)
                    ical_event.append(f"DTEND:{end.strftime('%Y%m%dT%H%M%SZ')}")
        except ValueError:
            # Fallback for unparseable dates (shouldn't happen, but just in case)
            ical_event.append(f"DTSTART:{event['start_time']}")
            if event.get('end_time'):
                ical_event.append(f"DTEND:{event['end_time']}")
        
        # Add other properties
        if event.get('description'):
            ical_event.append(f"DESCRIPTION:{self._escape_text(event['description'])}")
            
        if event.get('location'):
            ical_event.append(f"LOCATION:{self._escape_text(event['location'])}")
        
        # Add created and modified timestamps
        try:
            created = datetime.datetime.fromisoformat(event['created_at'])
            ical_event.append(f"CREATED:{created.strftime('%Y%m%dT%H%M%SZ')}")
        except (ValueError, KeyError):
            # Use current time if not available or invalid
            now = datetime.datetime.now()
            ical_event.append(f"CREATED:{now.strftime('%Y%m%dT%H%M%SZ')}")
            
        try:
            modified = datetime.datetime.fromisoformat(event['modified_at'])
            ical_event.append(f"LAST-MODIFIED:{modified.strftime('%Y%m%dT%H%M%SZ')}")
        except (ValueError, KeyError):
            # Use creation time or current time if not available
            if 'created_at' in event:
                ical_event.append(f"LAST-MODIFIED:{created.strftime('%Y%m%dT%H%M%SZ')}")
            else:
                now = datetime.datetime.now()
                ical_event.append(f"LAST-MODIFIED:{now.strftime('%Y%m%dT%H%M%SZ')}")
        
        # Handle recurrence if present
        if event.get('recurrence'):
            recur_rule = self._format_recurrence(event['recurrence'])
            if recur_rule:
                ical_event.append(f"RRULE:{recur_rule}")
        
        # Add reminders as alarms
        if event.get('reminders'):
            for reminder in event['reminders']:
                alarm = self._format_reminder(reminder)
                ical_event.extend(alarm)
        
        # Close the event
        ical_event.append("END:VEVENT")
        
        return ical_event
    
    def _format_recurrence(self, recurrence):
        """Format a recurrence pattern for iCalendar"""
        if not recurrence or not isinstance(recurrence, dict):
            return ""
            
        rrule_parts = []
        
        # Frequency
        freq = recurrence.get('frequency', '').upper()
        if freq in ['DAILY', 'WEEKLY', 'MONTHLY', 'YEARLY']:
            rrule_parts.append(f"FREQ={freq}")
        else:
            # Invalid frequency
            return ""
            
        # Interval
        interval = recurrence.get('interval')
        if interval and isinstance(interval, int) and interval > 1:
            rrule_parts.append(f"INTERVAL={interval}")
            
        # Count (number of occurrences)
        count = recurrence.get('count')
        if count and isinstance(count, int) and count > 0:
            rrule_parts.append(f"COUNT={count}")
            
        # Until (end date)
        until = recurrence.get('until')
        if until:
            try:
                until_date = datetime.datetime.fromisoformat(until)
                rrule_parts.append(f"UNTIL={until_date.strftime('%Y%m%dT%H%M%SZ')}")
            except ValueError:
                # Invalid date format, ignore
                pass
                
        # Days of week (for weekly recurrence)
        if freq == 'WEEKLY' and 'byDay' in recurrence:
            days = recurrence['byDay']
            if isinstance(days, list) and days:
                days_str = ','.join(day.upper() for day in days if day.upper() in 
                                   ['MO', 'TU', 'WE', 'TH', 'FR', 'SA', 'SU'])
                if days_str:
                    rrule_parts.append(f"BYDAY={days_str}")
                    
        # Days of month (for monthly recurrence)
        if freq == 'MONTHLY' and 'byMonthDay' in recurrence:
            days = recurrence['byMonthDay']
            if isinstance(days, list) and days:
                days_str = ','.join(str(day) for day in days if isinstance(day, int))
                if days_str:
                    rrule_parts.append(f"BYMONTHDAY={days_str}")
        
        return ';'.join(rrule_parts)
    
    def _format_reminder(self, reminder):
        """Format a reminder as an iCalendar VALARM"""
        alarm = [
            "BEGIN:VALARM",
            "ACTION:DISPLAY",
            f"DESCRIPTION:Reminder for event"
        ]
        
        # Set trigger time
        try:
            if 'time' in reminder:
                # Absolute time
                trigger_time = datetime.datetime.fromisoformat(reminder['time'])
                alarm.append(f"TRIGGER;VALUE=DATE-TIME:{trigger_time.strftime('%Y%m%dT%H%M%SZ')}")
            elif 'minutes_before' in reminder:
                # Relative time (minutes before event)
                minutes = int(reminder['minutes_before'])
                alarm.append(f"TRIGGER:-PT{minutes}M")
            else:
                # Default to 15 minutes before
                alarm.append("TRIGGER:-PT15M")
        except (ValueError, TypeError):
            # Default to 15 minutes before if parsing fails
            alarm.append("TRIGGER:-PT15M")
            
        alarm.append("END:VALARM")
        return alarm
    
    def _escape_text(self, text):
        """Escape special characters for iCalendar"""
        if not text:
            return ""
            
        # Escape special characters
        text = text.replace('\\', '\\\\')
        text = text.replace(';', '\\;')
        text = text.replace(',', '\\,')
        text = text.replace('\n', '\\n')
        
        return text
    
    def import_events(self, user_id, ical_content, file_path=None):
        """
        Import events from iCalendar format
        
        Args:
            user_id (str): ID of the user importing events
            ical_content (str, optional): iCalendar content as string
            file_path (str, optional): Path to iCalendar file
            
        Returns:
            dict: Import results with counts of imported and failed events
        """
        if file_path and not ical_content:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    ical_content = f.read()
            except Exception as e:
                return {
                    'success': False,
                    'error': f"Failed to read file: {str(e)}",
                    'imported': 0,
                    'failed': 0
                }
                
        if not ical_content:
            return {
                'success': False,
                'error': "No content provided",
                'imported': 0,
                'failed': 0
            }
        
        # Parse iCalendar content
        events = self._parse_ical(ical_content)
        
        # Import each event
        imported = 0
        failed = 0
        
        for event in events:
            try:
                event_id = self.calendar_manager.create_event(user_id, **event)
                if event_id:
                    imported += 1
                else:
                    failed += 1
            except Exception as e:
                print(f"Failed to import event: {str(e)}")
                failed += 1
        
        return {
            'success': True,
            'imported': imported,
            'failed': failed
        }
    
    def _parse_ical(self, ical_content):
        """Parse iCalendar content into event objects"""
        events = []
        
        # Normalize line breaks
        ical_content = ical_content.replace('\r\n', '\n').replace('\r', '\n')
        
        # Unfold lines (iCal format can fold long lines with a newline followed by whitespace)
        content_unfolded = re.sub(r'\n[ \t]', '', ical_content)
        
        # Split into lines
        lines = content_unfolded.split('\n')
        
        # Process lines
        in_event = False
        current_event = {}
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Check for event boundaries
            if line == 'BEGIN:VEVENT':
                in_event = True
                current_event = {}
                continue
                
            if line == 'END:VEVENT':
                if in_event and current_event:
                    events.append(current_event)
                in_event = False
                continue
                
            # Skip if not in an event
            if not in_event:
                continue
                
            # Parse property
            if ':' not in line:
                continue
                
            prop_parts = line.split(':', 1)
            prop_name = prop_parts[0]
            prop_value = prop_parts[1]
            
            # Handle parameters
            params = {}
            if ';' in prop_name:
                prop_parts = prop_name.split(';')
                prop_name = prop_parts[0]
                
                for param in prop_parts[1:]:
                    if '=' in param:
                        param_parts = param.split('=', 1)
                        params[param_parts[0]] = param_parts[1]
            
            # Process properties based on name
            self._process_property(current_event, prop_name, prop_value, params)
        
        return events
    
    def _process_property(self, event, prop_name, value, params):
        """Process an iCalendar property and add to event"""
        # Handle escaped characters
        value = value.replace('\\n', '\n').replace('\\,', ',').replace('\\;', ';').replace('\\\\', '\\')
        
        # Process based on property name
        if prop_name == 'SUMMARY':
            event['title'] = value
            
        elif prop_name == 'DESCRIPTION':
            event['description'] = value
            
        elif prop_name == 'LOCATION':
            event['location'] = value
            
        elif prop_name == 'DTSTART':
            is_date_only = 'VALUE' in params and params['VALUE'] == 'DATE'
            
            if is_date_only:
                # All-day event
                event['all_day'] = True
                try:
                    # Parse date in YYYYMMDD format
                    year = int(value[0:4])
                    month = int(value[4:6])
                    day = int(value[6:8])
                    date_obj = datetime.date(year, month, day)
                    event['start_time'] = date_obj.isoformat()
                except (ValueError, IndexError):
                    # Fallback if parsing fails
                    event['start_time'] = value
            else:
                # Regular event with time
                try:
                    # Parse datetime in various formats
                    if 'T' in value:
                        # Has time component
                        if value.endswith('Z'):
                            # UTC time
                            dt_format = '%Y%m%dT%H%M%SZ'
                        else:
                            # Local time
                            dt_format = '%Y%m%dT%H%M%S'
                            
                        dt = datetime.datetime.strptime(value, dt_format)
                        event['start_time'] = dt.isoformat()
                    else:
                        # Just date
                        dt = datetime.datetime.strptime(value, '%Y%m%d')
                        event['start_time'] = dt.isoformat()
                        event['all_day'] = True
                except ValueError:
                    # Fallback
                    event['start_time'] = value
                    
        elif prop_name == 'DTEND':
            is_date_only = 'VALUE' in params and params['VALUE'] == 'DATE'
            
            if is_date_only:
                try:
                    # Parse date in YYYYMMDD format
                    year = int(value[0:4])
                    month = int(value[4:6])
                    day = int(value[6:8])
                    
                    # In iCal, the end date is exclusive for all-day events, but our model
                    # uses inclusive end dates. Subtract a day.
                    date_obj = datetime.date(year, month, day) - datetime.timedelta(days=1)
                    event['end_time'] = date_obj.isoformat()
                except (ValueError, IndexError):
                    # Fallback
                    event['end_time'] = value
            else:
                # Regular event with time
                try:
                    # Parse datetime in various formats
                    if 'T' in value:
                        # Has time component
                        if value.endswith('Z'):
                            # UTC time
                            dt_format = '%Y%m%dT%H%M%SZ'
                        else:
                            # Local time
                            dt_format = '%Y%m%dT%H%M%S'
                            
                        dt = datetime.datetime.strptime(value, dt_format)
                        event['end_time'] = dt.isoformat()
                    else:
                        # Just date
                        dt = datetime.datetime.strptime(value, '%Y%m%d')
                        event['end_time'] = dt.isoformat()
                except ValueError:
                    # Fallback
                    event['end_time'] = value
                    
        elif prop_name == 'RRULE':
            # Parse recurrence rule
            recurrence = {}
            for rule_part in value.split(';'):
                if '=' in rule_part:
                    rule_name, rule_value = rule_part.split('=', 1)
                    
                    if rule_name == 'FREQ':
                        recurrence['frequency'] = rule_value.lower()
                        
                    elif rule_name == 'INTERVAL':
                        try:
                            recurrence['interval'] = int(rule_value)
                        except ValueError:
                            pass
                            
                    elif rule_name == 'COUNT':
                        try:
                            recurrence['count'] = int(rule_value)
                        except ValueError:
                            pass
                            
                    elif rule_name == 'UNTIL':
                        try:
                            if 'T' in rule_value:
                                # Has time component
                                if rule_value.endswith('Z'):
                                    # UTC time
                                    dt_format = '%Y%m%dT%H%M%SZ'
                                else:
                                    # Local time
                                    dt_format = '%Y%m%dT%H%M%S'
                                
                                dt = datetime.datetime.strptime(rule_value, dt_format)
                            else:
                                # Just date
                                dt = datetime.datetime.strptime(rule_value, '%Y%m%d')
                                
                            recurrence['until'] = dt.isoformat()
                        except ValueError:
                            # Fallback
                            recurrence['until'] = rule_value
                            
                    elif rule_name == 'BYDAY':
                        recurrence['byDay'] = rule_value.split(',')
                        
                    elif rule_name == 'BYMONTHDAY':
                        try:
                            recurrence['byMonthDay'] = [int(d) for d in rule_value.split(',')]
                        except ValueError:
                            pass
            
            if recurrence:
                event['recurrence'] = recurrence
                
        # We don't process alarms/reminders here, but a full implementation would
        # look for VALARM sections and extract reminder information
