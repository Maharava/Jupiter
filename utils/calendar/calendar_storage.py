import os
import sqlite3
import uuid
import json
import datetime
from pathlib import Path

class CalendarStorage:
    """Handles storage and retrieval of calendar data using SQLite"""
    
    def __init__(self, db_path=None):
        """Initialize the calendar storage with the path to the SQLite database"""
        if db_path is None:
            # Default to a calendar.db file in the same directory as the Jupiter data
            base_dir = Path(os.path.dirname(os.path.abspath(__file__))).parent.parent
            db_path = os.path.join(base_dir, "calendar.db")
        
        self.db_path = db_path
        self._initialize_db()
    
    def _initialize_db(self):
        """Create the database tables if they don't exist"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Create events table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS events (
                    event_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    description TEXT,
                    location TEXT,
                    start_time TIMESTAMP NOT NULL,
                    end_time TIMESTAMP,
                    all_day BOOLEAN DEFAULT 0,
                    recurrence TEXT,
                    privacy_level TEXT DEFAULT 'default',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create user_events association table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_events (
                    user_id TEXT NOT NULL,
                    event_id TEXT NOT NULL,
                    is_owner BOOLEAN DEFAULT 1,
                    FOREIGN KEY (event_id) REFERENCES events(event_id),
                    PRIMARY KEY (user_id, event_id)
                )
            ''')
            
            # Create reminders table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS reminders (
                    reminder_id TEXT PRIMARY KEY,
                    event_id TEXT NOT NULL,
                    reminder_time TIMESTAMP NOT NULL,
                    reminder_type TEXT DEFAULT 'notification',
                    FOREIGN KEY (event_id) REFERENCES events(event_id)
                )
            ''')
            
            # Create indices for better performance
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_events_start ON events(start_time)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_events ON user_events(user_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_reminders_time ON reminders(reminder_time)')
            
            conn.commit()
            
        except sqlite3.Error as e:
            print(f"Database initialization error: {e}")
        finally:
            if conn:
                conn.close()
    
    def _get_connection(self):
        """Get a connection to the SQLite database"""
        conn = sqlite3.connect(self.db_path)
        # Enable foreign key constraints
        conn.execute("PRAGMA foreign_keys = ON")
        # Configure for proper datetime handling
        conn.execute("PRAGMA datetime_format = 'ISO8601'")
        return conn
    
    def add_event(self, event_data, user_id):
        """
        Add a new event to the calendar
        
        Args:
            event_data (dict): Dictionary containing event details
            user_id (str): ID of the user creating the event
            
        Returns:
            str: ID of the created event or None if failed
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Generate a unique ID for the event
            event_id = str(uuid.uuid4())
            
            # Prepare SQL parameters
            params = {
                'event_id': event_id,
                'title': event_data.get('title', 'Untitled Event'),
                'description': event_data.get('description'),
                'location': event_data.get('location'),
                'start_time': event_data.get('start_time'),
                'end_time': event_data.get('end_time'),
                'all_day': 1 if event_data.get('all_day') else 0,
                'recurrence': json.dumps(event_data.get('recurrence')) if event_data.get('recurrence') else None,
                'privacy_level': event_data.get('privacy_level', 'default')
            }
            
            # Insert event
            cursor.execute('''
                INSERT INTO events (
                    event_id, title, description, location, 
                    start_time, end_time, all_day, recurrence, privacy_level
                ) VALUES (
                    :event_id, :title, :description, :location, 
                    :start_time, :end_time, :all_day, :recurrence, :privacy_level
                )
            ''', params)
            
            # Associate event with user
            cursor.execute('''
                INSERT INTO user_events (user_id, event_id, is_owner)
                VALUES (?, ?, 1)
            ''', (user_id, event_id))
            
            # Add reminders if provided
            if 'reminders' in event_data and event_data['reminders']:
                for reminder in event_data['reminders']:
                    reminder_id = str(uuid.uuid4())
                    cursor.execute('''
                        INSERT INTO reminders (reminder_id, event_id, reminder_time, reminder_type)
                        VALUES (?, ?, ?, ?)
                    ''', (
                        reminder_id, 
                        event_id, 
                        reminder.get('time'),
                        reminder.get('type', 'notification')
                    ))
            
            conn.commit()
            return event_id
            
        except sqlite3.Error as e:
            print(f"Error adding event: {e}")
            return None
        finally:
            if conn:
                conn.close()
    
    def update_event(self, event_id, event_data, user_id):
        """
        Update an existing event
        
        Args:
            event_id (str): ID of the event to update
            event_data (dict): Updated event details
            user_id (str): ID of the user making the update
            
        Returns:
            bool: True if update was successful, False otherwise
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Check if user is allowed to update this event
            cursor.execute('''
                SELECT is_owner FROM user_events
                WHERE user_id = ? AND event_id = ?
            ''', (user_id, event_id))
            
            result = cursor.fetchone()
            if not result:
                print(f"User {user_id} does not have access to event {event_id}")
                return False
            
            # Prepare SQL parameters with only the fields that are provided
            params = {'event_id': event_id}
            
            # Build dynamic update SQL
            update_fields = []
            
            if 'title' in event_data:
                params['title'] = event_data['title']
                update_fields.append('title = :title')
                
            if 'description' in event_data:
                params['description'] = event_data['description']
                update_fields.append('description = :description')
                
            if 'location' in event_data:
                params['location'] = event_data['location']
                update_fields.append('location = :location')
                
            if 'start_time' in event_data:
                params['start_time'] = event_data['start_time']
                update_fields.append('start_time = :start_time')
                
            if 'end_time' in event_data:
                params['end_time'] = event_data['end_time']
                update_fields.append('end_time = :end_time')
                
            if 'all_day' in event_data:
                params['all_day'] = 1 if event_data['all_day'] else 0
                update_fields.append('all_day = :all_day')
                
            if 'recurrence' in event_data:
                params['recurrence'] = json.dumps(event_data['recurrence']) if event_data['recurrence'] else None
                update_fields.append('recurrence = :recurrence')
                
            if 'privacy_level' in event_data:
                params['privacy_level'] = event_data['privacy_level']
                update_fields.append('privacy_level = :privacy_level')
            
            # Add modified timestamp
            params['modified_at'] = datetime.datetime.now().isoformat()
            update_fields.append('modified_at = :modified_at')
            
            # If there's nothing to update, return
            if not update_fields:
                return True
            
            # Execute update
            update_sql = f'''
                UPDATE events 
                SET {', '.join(update_fields)}
                WHERE event_id = :event_id
            '''
            
            cursor.execute(update_sql, params)
            
            # Update reminders if provided
            if 'reminders' in event_data:
                # Delete existing reminders
                cursor.execute('''
                    DELETE FROM reminders
                    WHERE event_id = ?
                ''', (event_id,))
                
                # Add new reminders
                for reminder in event_data['reminders']:
                    reminder_id = str(uuid.uuid4())
                    cursor.execute('''
                        INSERT INTO reminders (reminder_id, event_id, reminder_time, reminder_type)
                        VALUES (?, ?, ?, ?)
                    ''', (
                        reminder_id, 
                        event_id, 
                        reminder.get('time'),
                        reminder.get('type', 'notification')
                    ))
            
            conn.commit()
            return True
            
        except sqlite3.Error as e:
            print(f"Error updating event: {e}")
            return False
        finally:
            if conn:
                conn.close()
    
    def delete_event(self, event_id, user_id):
        """
        Delete an event from the calendar
        
        Args:
            event_id (str): ID of the event to delete
            user_id (str): ID of the user deleting the event
            
        Returns:
            bool: True if deletion was successful, False otherwise
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Check if user is the owner of this event
            cursor.execute('''
                SELECT is_owner FROM user_events
                WHERE user_id = ? AND event_id = ?
            ''', (user_id, event_id))
            
            result = cursor.fetchone()
            if not result or not result[0]:
                print(f"User {user_id} is not the owner of event {event_id}")
                return False
            
            # Delete reminders
            cursor.execute('''
                DELETE FROM reminders
                WHERE event_id = ?
            ''', (event_id,))
            
            # Delete user associations
            cursor.execute('''
                DELETE FROM user_events
                WHERE event_id = ?
            ''', (event_id,))
            
            # Delete event
            cursor.execute('''
                DELETE FROM events
                WHERE event_id = ?
            ''', (event_id,))
            
            conn.commit()
            return True
            
        except sqlite3.Error as e:
            print(f"Error deleting event: {e}")
            return False
        finally:
            if conn:
                conn.close()
    
    def get_event(self, event_id, user_id):
        """
        Get a specific event by ID
        
        Args:
            event_id (str): ID of the event to retrieve
            user_id (str): ID of the user requesting the event
            
        Returns:
            dict: Event data or None if not found or not authorized
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Check if user has access to this event
            cursor.execute('''
                SELECT e.*, ue.is_owner
                FROM events e
                JOIN user_events ue ON e.event_id = ue.event_id
                WHERE e.event_id = ? AND ue.user_id = ?
            ''', (event_id, user_id))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            event_data = {
                'event_id': row[0],
                'title': row[1],
                'description': row[2],
                'location': row[3],
                'start_time': row[4],
                'end_time': row[5],
                'all_day': bool(row[6]),
                'recurrence': json.loads(row[7]) if row[7] else None,
                'privacy_level': row[8],
                'created_at': row[9],
                'modified_at': row[10],
                'is_owner': bool(row[11])
            }
            
            # Get reminders
            cursor.execute('''
                SELECT reminder_id, reminder_time, reminder_type
                FROM reminders
                WHERE event_id = ?
            ''', (event_id,))
            
            reminders = []
            for reminder_row in cursor.fetchall():
                reminders.append({
                    'reminder_id': reminder_row[0],
                    'time': reminder_row[1],
                    'type': reminder_row[2]
                })
            
            event_data['reminders'] = reminders
            
            return event_data
            
        except sqlite3.Error as e:
            print(f"Error getting event: {e}")
            return None
        finally:
            if conn:
                conn.close()
    
    def get_events_by_daterange(self, user_id, start_date, end_date):
        """
        Get events within a specified date range
        
        Args:
            user_id (str): ID of the user requesting events
            start_date (str): Start of date range (ISO format)
            end_date (str): End of date range (ISO format)
            
        Returns:
            list: List of events within the date range
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT e.*, ue.is_owner
                FROM events e
                JOIN user_events ue ON e.event_id = ue.event_id
                WHERE ue.user_id = ? 
                  AND (
                    (e.start_time >= ? AND e.start_time <= ?) OR
                    (e.end_time >= ? AND e.end_time <= ?) OR
                    (e.start_time <= ? AND e.end_time >= ?)
                  )
                ORDER BY e.start_time
            ''', (user_id, start_date, end_date, start_date, end_date, start_date, start_date))
            
            events = []
            for row in cursor.fetchall():
                event_data = {
                    'event_id': row[0],
                    'title': row[1],
                    'description': row[2],
                    'location': row[3],
                    'start_time': row[4],
                    'end_time': row[5],
                    'all_day': bool(row[6]),
                    'recurrence': json.loads(row[7]) if row[7] else None,
                    'privacy_level': row[8],
                    'created_at': row[9],
                    'modified_at': row[10],
                    'is_owner': bool(row[11])
                }
                events.append(event_data)
            
            # Add reminders to events
            for event in events:
                cursor.execute('''
                    SELECT reminder_id, reminder_time, reminder_type
                    FROM reminders
                    WHERE event_id = ?
                ''', (event['event_id'],))
                
                reminders = []
                for reminder_row in cursor.fetchall():
                    reminders.append({
                        'reminder_id': reminder_row[0],
                        'time': reminder_row[1],
                        'type': reminder_row[2]
                    })
                
                event['reminders'] = reminders
            
            return events
            
        except sqlite3.Error as e:
            print(f"Error getting events by date range: {e}")
            return []
        finally:
            if conn:
                conn.close()
    
    def get_upcoming_events(self, user_id, days=7):
        """
        Get upcoming events for a user
        
        Args:
            user_id (str): ID of the user
            days (int): Number of days to look ahead
            
        Returns:
            list: List of upcoming events
        """
        today = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = (today + datetime.timedelta(days=days)).isoformat()
        
        return self.get_events_by_daterange(user_id, today.isoformat(), end_date)
    
    def share_event(self, event_id, owner_id, shared_user_id):
        """
        Share an event with another user
        
        Args:
            event_id (str): ID of the event to share
            owner_id (str): ID of the user sharing the event
            shared_user_id (str): ID of the user to share with
            
        Returns:
            bool: True if sharing was successful, False otherwise
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Check if owner has permission to share
            cursor.execute('''
                SELECT is_owner FROM user_events
                WHERE user_id = ? AND event_id = ?
            ''', (owner_id, event_id))
            
            result = cursor.fetchone()
            if not result or not result[0]:
                print(f"User {owner_id} is not the owner of event {event_id}")
                return False
            
            # Check if event is already shared with the user
            cursor.execute('''
                SELECT 1 FROM user_events
                WHERE user_id = ? AND event_id = ?
            ''', (shared_user_id, event_id))
            
            if cursor.fetchone():
                # Already shared, nothing to do
                return True
            
            # Share event
            cursor.execute('''
                INSERT INTO user_events (user_id, event_id, is_owner)
                VALUES (?, ?, 0)
            ''', (shared_user_id, event_id))
            
            conn.commit()
            return True
            
        except sqlite3.Error as e:
            print(f"Error sharing event: {e}")
            return False
        finally:
            if conn:
                conn.close()
    
    def get_pending_reminders(self, current_time=None):
        """
        Get reminders that are due to be delivered
        
        Args:
            current_time (str): Current time in ISO format (default: now)
            
        Returns:
            list: List of reminders to be delivered
        """
        if current_time is None:
            current_time = datetime.datetime.now().isoformat()
            
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT r.reminder_id, r.event_id, e.title, r.reminder_time, r.reminder_type,
                       ue.user_id
                FROM reminders r
                JOIN events e ON r.event_id = e.event_id
                JOIN user_events ue ON e.event_id = ue.event_id
                WHERE r.reminder_time <= ?
                ORDER BY r.reminder_time
            ''', (current_time,))
            
            reminders = []
            for row in cursor.fetchall():
                reminder = {
                    'reminder_id': row[0],
                    'event_id': row[1],
                    'event_title': row[2],
                    'reminder_time': row[3],
                    'reminder_type': row[4],
                    'user_id': row[5]
                }
                reminders.append(reminder)
            
            return reminders
            
        except sqlite3.Error as e:
            print(f"Error getting pending reminders: {e}")
            return []
        finally:
            if conn:
                conn.close()
    
    def mark_reminder_delivered(self, reminder_id):
        """
        Mark a reminder as delivered by removing it
        
        Args:
            reminder_id (str): ID of the reminder
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                DELETE FROM reminders
                WHERE reminder_id = ?
            ''', (reminder_id,))
            
            conn.commit()
            return True
            
        except sqlite3.Error as e:
            print(f"Error marking reminder as delivered: {e}")
            return False
        finally:
            if conn:
                conn.close()
    
    def is_time_available(self, user_id, proposed_time, duration_minutes=60):
        """
        Check if a user is available at a proposed time
        
        Args:
            user_id (str): ID of the user
            proposed_time (str): Proposed start time in ISO format
            duration_minutes (int): Duration of the proposed event in minutes
            
        Returns:
            bool: True if time is available, False if there's a conflict
        """
        try:
            proposed_start = datetime.datetime.fromisoformat(proposed_time)
            proposed_end = proposed_start + datetime.timedelta(minutes=duration_minutes)
            
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT COUNT(*) FROM events e
                JOIN user_events ue ON e.event_id = ue.event_id
                WHERE ue.user_id = ?
                  AND (
                    (e.start_time <= ? AND e.end_time > ?) OR
                    (e.start_time < ? AND e.end_time >= ?) OR
                    (e.start_time >= ? AND e.end_time <= ?)
                  )
            ''', (
                user_id, 
                proposed_end.isoformat(), proposed_start.isoformat(),
                proposed_end.isoformat(), proposed_start.isoformat(),
                proposed_start.isoformat(), proposed_end.isoformat()
            ))
            
            count = cursor.fetchone()[0]
            return count == 0
            
        except (sqlite3.Error, ValueError) as e:
            print(f"Error checking time availability: {e}")
            return False
        finally:
            if conn:
                conn.close()
