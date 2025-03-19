import datetime
from .calendar_manager import CalendarManager

class PromptEnhancer:
    """
    Enhances Jupiter system prompts with calendar information.
    This allows calendar awareness to be seamlessly integrated into conversations.
    """
    
    def __init__(self, calendar_manager=None):
        """Initialize with a calendar manager instance"""
        self.calendar_manager = calendar_manager or CalendarManager()
    
    def enhance_prompt(self, user_id, prompt, detail_level='normal'):
        """
        Add calendar context to a system prompt
        
        Args:
            user_id (str): ID of the user in the conversation
            prompt (str): The original system prompt
            detail_level (str): Level of detail to include ('minimal', 'normal', 'detailed')
            
        Returns:
            str: Enhanced system prompt with calendar context
        """
        if not user_id:
            return prompt
            
        calendar_context = self._get_calendar_context(user_id, detail_level)
        
        if not calendar_context:
            return prompt
            
        # Add the calendar information to the prompt
        if "## What You Know About The User" in prompt:
            # If the prompt already has a user section, add calendar as a separate section
            # after the user section
            parts = prompt.split("## What You Know About The User", 1)
            return parts[0] + "## What You Know About The User" + parts[1] + calendar_context
        else:
            # Otherwise, add it to the end of the prompt
            return prompt + calendar_context
    
    def _get_calendar_context(self, user_id, detail_level='normal'):
        """Get calendar context for the user based on detail level"""
        # Get today's date and end date based on detail level
        today = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        if detail_level == 'minimal':
            # Just today's events
            end_date = (today + datetime.timedelta(days=1) - datetime.timedelta(microseconds=1))
            days_to_check = 1
        elif detail_level == 'detailed':
            # Events for the next two weeks
            end_date = (today + datetime.timedelta(days=14) - datetime.timedelta(microseconds=1))
            days_to_check = 14
        else:  # 'normal'
            # Events for the next week
            end_date = (today + datetime.timedelta(days=7) - datetime.timedelta(microseconds=1))
            days_to_check = 7
        
        # Get upcoming events
        events = self.calendar_manager.get_events_by_daterange(user_id, today.isoformat(), end_date.isoformat())
        
        # Always start with the Calendar Information header
        calendar_context = "\n\n## Calendar Information\n"
        
        if not events:
            # If no events, just add the availability context
            calendar_context += self._get_availability_context(user_id, days_to_check)
            return calendar_context
            
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
        
        if not events_by_date:
            return self._get_availability_context(user_id, days_to_check)
            
        # Build the calendar context
        calendar_context = "\n\n## Calendar Information\n"
        
        # Add upcoming events section
        calendar_context += "### Upcoming Events\n"
        
        # Sort dates
        sorted_dates = sorted(events_by_date.keys())
        
        for date in sorted_dates:
            date_events = events_by_date[date]
            
            # Format the date
            date_str = date.strftime("%A, %B %d, %Y")
            if date == today.date():
                date_str = f"Today ({date_str})"
            elif date == (today + datetime.timedelta(days=1)).date():
                date_str = f"Tomorrow ({date_str})"
                
            calendar_context += f"**{date_str}**\n"
            
            # Sort events by time
            date_events.sort(key=lambda e: e['start_time'])
            
            for event in date_events:
                # Format time
                time_str = "All day" if event.get('all_day') else datetime.datetime.fromisoformat(event['start_time']).strftime("%I:%M %p")
                
                # Format location
                loc_str = f" at {event['location']}" if event.get('location') else ""
                
                # Format description (only include if detail_level is 'detailed')
                desc_str = ""
                if detail_level == 'detailed' and event.get('description'):
                    desc_str = f": {event['description']}"
                
                calendar_context += f"- {time_str}: {event['title']}{loc_str}{desc_str}\n"
            
            calendar_context += "\n"
        
        # Add schedule density
        calendar_context += self._get_availability_context(user_id, days_to_check)
        
        return calendar_context
    
    def _get_availability_context(self, user_id, days=7):
        """Get context about the user's schedule density"""
        # Get schedule density
        density = self.calendar_manager.get_schedule_density(user_id, days)
        
        if days == 1:
            time_period = "today"
        else:
            time_period = f"the next {days} days"
            
        if density > 0.8:
            return f"\n### Schedule Status\nThe user has a very busy schedule for {time_period}.\n"
        elif density > 0.5:
            return f"\n### Schedule Status\nThe user has a moderately busy schedule for {time_period}.\n"
        elif density > 0.2:
            return f"\n### Schedule Status\nThe user has a few events scheduled for {time_period}.\n"
        else:
            return f"\n### Schedule Status\nThe user has a relatively open schedule for {time_period}.\n"
    
    def get_event_by_reference(self, user_id, event_reference):
        """
        Try to find an event based on a natural language reference
        
        Args:
            user_id (str): User ID
            event_reference (str): Natural language reference like "my meeting tomorrow"
            
        Returns:
            dict or None: The matched event or None
        """
        # This is a placeholder for future implementation
        # Would use NLP to parse the reference and search for matching events
        return None


# Standalone function for easy integration with Jupiter
def enhance_prompt(user_id, prompt, detail_level='normal'):
    """
    Enhance a system prompt with calendar information
    
    Args:
        user_id (str): ID of the user in the conversation
        prompt (str): The original system prompt
        detail_level (str): Level of detail to include ('minimal', 'normal', 'detailed')
        
    Returns:
        str: Enhanced system prompt with calendar context
    """
    enhancer = PromptEnhancer()
    return enhancer.enhance_prompt(user_id, prompt, detail_level)
