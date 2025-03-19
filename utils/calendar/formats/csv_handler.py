import csv
import datetime
import json
from pathlib import Path

class CSVHandler:
    """Handles import and export of calendar events in CSV format"""
    
    def __init__(self, calendar_manager):
        """Initialize with a reference to the calendar manager"""
        self.calendar_manager = calendar_manager
    
    def export_events(self, events, output_path):
        """
        Export events to CSV format
        
        Args:
            events (list): List of events to export
            output_path (str): Path to save the CSV file
            
        Returns:
            str: Path to the saved file
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Define CSV columns
        fieldnames = [
            'Title', 'Start Time', 'End Time', 'All Day', 
            'Location', 'Description', 'Recurrence', 'Privacy'
        ]
        
        try:
            with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                
                for event in events:
                    # Format recurrence as a simple string if present
                    recurrence_str = ""
                    if event.get('recurrence'):
                        if isinstance(event['recurrence'], dict):
                            recurrence = event['recurrence']
                            freq = recurrence.get('frequency', '').capitalize()
                            interval = recurrence.get('interval', 1)
                            
                            if freq:
                                recurrence_str = f"{freq}"
                                if interval > 1:
                                    recurrence_str += f", every {interval} "
                                    if freq == 'Daily':
                                        recurrence_str += "days"
                                    elif freq == 'Weekly':
                                        recurrence_str += "weeks"
                                    elif freq == 'Monthly':
                                        recurrence_str += "months"
                                    elif freq == 'Yearly':
                                        recurrence_str += "years"
                        else:
                            # If it's a string or other format, use as is
                            recurrence_str = str(event['recurrence'])
                    
                    # Format dates for CSV
                    start_time = event.get('start_time', '')
                    end_time = event.get('end_time', '')
                    
                    # Write CSV row
                    writer.writerow({
                        'Title': event.get('title', ''),
                        'Start Time': start_time,
                        'End Time': end_time,
                        'All Day': 'Yes' if event.get('all_day') else 'No',
                        'Location': event.get('location', ''),
                        'Description': event.get('description', ''),
                        'Recurrence': recurrence_str,
                        'Privacy': event.get('privacy_level', 'default')
                    })
                    
            return str(output_path)
            
        except Exception as e:
            print(f"Error exporting events to CSV: {e}")
            return None
    
    def import_events(self, user_id, file_path):
        """
        Import events from CSV format
        
        Args:
            user_id (str): ID of the user importing events
            file_path (str): Path to CSV file
            
        Returns:
            dict: Import results with counts of imported and failed events
        """
        imported = 0
        failed = 0
        
        try:
            with open(file_path, 'r', encoding='utf-8-sig') as csvfile:
                # Try to determine the dialect
                dialect = csv.Sniffer().sniff(csvfile.read(1024))
                csvfile.seek(0)
                
                # Check if the file has a header
                has_header = csv.Sniffer().has_header(csvfile.read(1024))
                csvfile.seek(0)
                
                # Create reader
                if has_header:
                    reader = csv.DictReader(csvfile, dialect=dialect)
                    field_mapping = self._get_field_mapping(reader.fieldnames)
                else:
                    # Without headers, use positional guessing
                    reader = csv.reader(csvfile, dialect=dialect)
                    field_mapping = {
                        0: 'title',
                        1: 'start_time',
                        2: 'end_time',
                        3: 'all_day',
                        4: 'location',
                        5: 'description'
                    }
                
                # Process each row
                for row in reader:
                    try:
                        if isinstance(row, dict):
                            # DictReader provides named fields
                            event_data = self._process_dict_row(row, field_mapping)
                        else:
                            # Reader provides list of values
                            event_data = self._process_list_row(row, field_mapping)
                        
                        # Create event
                        if 'title' in event_data and 'start_time' in event_data:
                            event_id = self.calendar_manager.create_event(
                                user_id, 
                                event_data.pop('title'),
                                event_data.pop('start_time'),
                                **event_data
                            )
                            
                            if event_id:
                                imported += 1
                            else:
                                failed += 1
                        else:
                            # Skip rows without required fields
                            failed += 1
                            
                    except Exception as e:
                        print(f"Error importing event from CSV: {e}")
                        failed += 1
                        
            return {
                'success': True,
                'imported': imported,
                'failed': failed
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f"Failed to read CSV file: {str(e)}",
                'imported': imported,
                'failed': failed
            }
    
    def _get_field_mapping(self, fieldnames):
        """Map CSV column names to event field names"""
        # Initialize with empty mapping
        mapping = {}
        
        # Check each field name and map to event field
        for i, field in enumerate(fieldnames):
            lower_field = field.lower()
            
            # Title
            if lower_field in ['title', 'summary', 'subject', 'event']:
                mapping[field] = 'title'
                
            # Start time
            elif lower_field in ['start', 'start time', 'start_time', 'starttime', 'begins', 'start date']:
                mapping[field] = 'start_time'
                
            # End time
            elif lower_field in ['end', 'end time', 'end_time', 'endtime', 'finish', 'end date']:
                mapping[field] = 'end_time'
                
            # All day
            elif lower_field in ['all day', 'all_day', 'allday', 'full day']:
                mapping[field] = 'all_day'
                
            # Location
            elif lower_field in ['location', 'place', 'venue']:
                mapping[field] = 'location'
                
            # Description
            elif lower_field in ['description', 'desc', 'details', 'notes']:
                mapping[field] = 'description'
                
            # Recurrence
            elif lower_field in ['recurrence', 'repeat', 'frequency', 'recurring']:
                mapping[field] = 'recurrence'
                
            # Privacy
            elif lower_field in ['privacy', 'privacy level', 'privacy_level', 'sharing']:
                mapping[field] = 'privacy_level'
        
        return mapping
    
    def _process_dict_row(self, row, field_mapping):
        """Process a CSV row from DictReader"""
        event_data = {}
        
        # Map fields using the field mapping
        for csv_field, event_field in field_mapping.items():
            if csv_field in row and row[csv_field]:
                # Process based on field type
                if event_field == 'all_day':
                    # Convert various representations of boolean to Python boolean
                    value = row[csv_field].lower()
                    event_data[event_field] = value in ['yes', 'y', 'true', '1', 'on']
                    
                elif event_field == 'recurrence':
                    # Parse recurrence text into a dict
                    event_data[event_field] = self._parse_recurrence(row[csv_field])
                    
                else:
                    # Regular string fields
                    event_data[event_field] = row[csv_field]
        
        # Process dates
        self._process_dates(event_data)
        
        return event_data
    
    def _process_list_row(self, row, field_mapping):
        """Process a CSV row from regular reader"""
        event_data = {}
        
        # Map fields by position
        for i, value in enumerate(row):
            if i in field_mapping and value:
                event_field = field_mapping[i]
                
                # Process based on field type
                if event_field == 'all_day':
                    # Convert various representations of boolean to Python boolean
                    value_lower = value.lower()
                    event_data[event_field] = value_lower in ['yes', 'y', 'true', '1', 'on']
                    
                elif event_field == 'recurrence':
                    # Parse recurrence text into a dict
                    event_data[event_field] = self._parse_recurrence(value)
                    
                else:
                    # Regular string fields
                    event_data[event_field] = value
        
        # Process dates
        self._process_dates(event_data)
        
        return event_data
    
    def _process_dates(self, event_data):
        """Process date fields to ensure they're in the correct format"""
        # Try to parse start time
        if 'start_time' in event_data:
            try:
                # Try different date formats
                start_time = self._parse_date_string(event_data['start_time'])
                if start_time:
                    event_data['start_time'] = start_time
            except ValueError:
                # Leave as is if parsing fails
                pass
                
        # Try to parse end time
        if 'end_time' in event_data:
            try:
                # Try different date formats
                end_time = self._parse_date_string(event_data['end_time'])
                if end_time:
                    event_data['end_time'] = end_time
            except ValueError:
                # Leave as is if parsing fails
                pass
    
    def _parse_date_string(self, date_string):
        """Try to parse a date string in various formats"""
        # List of date formats to try
        formats = [
            # ISO formats
            '%Y-%m-%dT%H:%M:%S',  # 2023-01-01T12:00:00
            '%Y-%m-%dT%H:%M',     # 2023-01-01T12:00
            '%Y-%m-%d %H:%M:%S',  # 2023-01-01 12:00:00
            '%Y-%m-%d %H:%M',     # 2023-01-01 12:00
            '%Y-%m-%d',           # 2023-01-01
            
            # USA formats
            '%m/%d/%Y %H:%M:%S',  # 01/01/2023 12:00:00
            '%m/%d/%Y %H:%M',     # 01/01/2023 12:00
            '%m/%d/%Y',           # 01/01/2023
            
            # European formats
            '%d/%m/%Y %H:%M:%S',  # 01/01/2023 12:00:00
            '%d/%m/%Y %H:%M',     # 01/01/2023 12:00
            '%d/%m/%Y',           # 01/01/2023
            
            # Other common formats
            '%d-%m-%Y %H:%M:%S',  # 01-01-2023 12:00:00
            '%d-%m-%Y %H:%M',     # 01-01-2023 12:00
            '%d-%m-%Y',           # 01-01-2023
            '%d.%m.%Y %H:%M:%S',  # 01.01.2023 12:00:00
            '%d.%m.%Y %H:%M',     # 01.01.2023 12:00
            '%d.%m.%Y',           # 01.01.2023
        ]
        
        # Try each format
        for fmt in formats:
            try:
                dt = datetime.datetime.strptime(date_string, fmt)
                return dt.isoformat()
            except ValueError:
                continue
                
        # If we get here, no format matched
        return None
    
    def _parse_recurrence(self, recurrence_str):
        """Parse a recurrence string into a structured dict"""
        if not recurrence_str:
            return None
            
        recurrence = {}
        recurrence_str = recurrence_str.lower()
        
        # Determine frequency
        if 'daily' in recurrence_str:
            recurrence['frequency'] = 'daily'
        elif 'weekly' in recurrence_str:
            recurrence['frequency'] = 'weekly'
        elif 'monthly' in recurrence_str:
            recurrence['frequency'] = 'monthly'
        elif 'yearly' in recurrence_str or 'annual' in recurrence_str:
            recurrence['frequency'] = 'yearly'
        else:
            # Default to daily if frequency can't be determined
            recurrence['frequency'] = 'daily'
            
        # Check for interval
        interval_match = None
        if 'every' in recurrence_str:
            # Look for "every N days/weeks/months/years"
            for word in ['days', 'weeks', 'months', 'years']:
                if word in recurrence_str:
                    parts = recurrence_str.split(word)[0].split('every')
                    if len(parts) > 1:
                        try:
                            interval = int(''.join(c for c in parts[1] if c.isdigit()))
                            if interval > 0:
                                recurrence['interval'] = interval
                                interval_match = True
                        except (ValueError, IndexError):
                            pass
                            
            # If no specific interval found but "every" is present, default to 1
            if 'interval' not in recurrence and not interval_match:
                recurrence['interval'] = 1
        
        return recurrence
