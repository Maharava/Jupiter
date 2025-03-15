import datetime
import random
import re
import json

class CuriosityManager:
    """Manages Jupiter's curiosity about user information."""
    
    def __init__(self, jupiter_chat):
        self.jupiter = jupiter_chat
        
        # Define all knowledge goals with metadata
        self.knowledge_goals = {
            # Basic Identity
            'name': {
                'known': False, 
                'priority': 5, 
                'last_asked': None,
                'ask_method': 'direct',
                'min_trust': 1
            },
            'gender': {
                'known': False, 
                'priority': 2, 
                'last_asked': None,
                'ask_method': 'infer',
                'min_trust': 3
            },
            'age': {
                'known': False, 
                'priority': 2, 
                'last_asked': None,
                'ask_method': 'infer',
                'min_trust': 4
            },
            
            # Location Context
            'location': {
                'known': False, 
                'priority': 4, 
                'last_asked': None,
                'ask_method': 'direct',
                'min_trust': 2
            },
            'nationality': {
                'known': False, 
                'priority': 2, 
                'last_asked': None,
                'ask_method': 'direct',
                'min_trust': 3
            },
            
            # Professional Context
            'professional_field': {
                'known': False, 
                'priority': 4, 
                'last_asked': None,
                'ask_method': 'llm',
                'min_trust': 2
            },
            'technical_proficiency': {
                'known': False, 
                'priority': 3, 
                'last_asked': None,
                'ask_method': 'infer',
                'min_trust': 2
            },
            
            # Communication Preferences
            'communication_style': {
                'known': False, 
                'priority': 5, 
                'last_asked': None,
                'ask_method': 'infer',
                'min_trust': 2
            },
            'humor_level': {
                'known': False, 
                'priority': 3, 
                'last_asked': None,
                'ask_method': 'infer',
                'min_trust': 3
            },
            
            # Temporal Information
            'important_dates': {
                'known': False, 
                'priority': 3, 
                'last_asked': None,
                'ask_method': 'follow_up',
                'min_trust': 4
            },
            
            # Project Information
            'active_projects': {
                'known': False, 
                'priority': 4, 
                'last_asked': None,
                'ask_method': 'llm',
                'min_trust': 3
            },
            'goals': {
                'known': False, 
                'priority': 4, 
                'last_asked': None,
                'ask_method': 'llm',
                'min_trust': 4
            },
            'challenges': {
                'known': False, 
                'priority': 4, 
                'last_asked': None,
                'ask_method': 'llm',
                'min_trust': 5
            },
            
            # Interests & Preferences
            'topics_of_interest': {
                'known': False, 
                'priority': 4, 
                'last_asked': None,
                'ask_method': 'infer',
                'min_trust': 2
            },
            'topics_to_avoid': {
                'known': False, 
                'priority': 5, 
                'last_asked': None,
                'ask_method': 'infer',
                'min_trust': 2
            },
            
            # Relationship Metrics
            'family': {
                'known': False, 
                'priority': 3, 
                'last_asked': None,
                'ask_method': 'direct',
                'min_trust': 4
            }
        }
        
        # Curiosity settings
        self.min_messages_between_questions = 3
        self.messages_since_last_question = 0
        self.max_questions_per_session = 2
        self.questions_this_session = 0
        
        # Trust metric - starts at 3, ranges from 1-10
        self.trust_level = 3 if 'trust_level' not in self.jupiter.user_data else self.jupiter.user_data['trust_level']
        
        # Update known information
        self.update_known_info()
    
    def update_known_info(self):
        """Update which information is already known"""
        user_data = self.jupiter.user_data
        
        # Basic identity
        if 'name' in user_data and user_data['name']:
            self.knowledge_goals['name']['known'] = True
        if 'gender' in user_data and user_data['gender']:
            self.knowledge_goals['gender']['known'] = True
        if 'age' in user_data and user_data['age']:
            self.knowledge_goals['age']['known'] = True
        
        # Location context
        if 'location' in user_data and user_data['location']:
            self.knowledge_goals['location']['known'] = True
        if 'nationality' in user_data and user_data['nationality']:
            self.knowledge_goals['nationality']['known'] = True
        
        # Professional context
        if 'professional_field' in user_data and user_data['professional_field']:
            self.knowledge_goals['professional_field']['known'] = True
        if 'technical_proficiency' in user_data and user_data['technical_proficiency']:
            self.knowledge_goals['technical_proficiency']['known'] = True
        
        # Communication preferences
        if 'communication_style' in user_data and user_data['communication_style']:
            self.knowledge_goals['communication_style']['known'] = True
        if 'humor_level' in user_data and user_data['humor_level']:
            self.knowledge_goals['humor_level']['known'] = True
        
        # Temporal information
        if 'important_dates' in user_data and user_data['important_dates']:
            self.knowledge_goals['important_dates']['known'] = True
        
        # Project information
        if 'active_projects' in user_data and user_data['active_projects']:
            self.knowledge_goals['active_projects']['known'] = True
        if 'goals' in user_data and user_data['goals']:
            self.knowledge_goals['goals']['known'] = True
        if 'challenges' in user_data and user_data['challenges']:
            self.knowledge_goals['challenges']['known'] = True
        
        # Interests & preferences
        if 'topics_of_interest' in user_data and user_data['topics_of_interest']:
            self.knowledge_goals['topics_of_interest']['known'] = True
        if 'topics_to_avoid' in user_data and user_data['topics_to_avoid']:
            self.knowledge_goals['topics_to_avoid']['known'] = True
        
        # Relationship metrics
        if 'family' in user_data and user_data['family']:
            self.knowledge_goals['family']['known'] = True
    
    def should_ask_question(self):
        """Check if it's time to ask a curious question"""
        # Don't ask questions too frequently
        if self.messages_since_last_question < self.min_messages_between_questions:
            return False
        
        # Don't ask too many questions per session
        if self.questions_this_session >= self.max_questions_per_session:
            return False
        
        # Only ask if there's unknown information
        unknown_info = self.get_askable_unknown_info()
        return len(unknown_info) > 0
    
    def get_askable_unknown_info(self):
        """Get list of unknown information that can be directly asked about"""
        # Filter for information types that are:
        # 1. Unknown
        # 2. Use 'direct' ask method
        # 3. Trust level is sufficient
        unknown_info = []
        
        for info_type, info in self.knowledge_goals.items():
            if (not info['known'] and 
                info['ask_method'] == 'direct' and
                self.trust_level >= info['min_trust']):
                unknown_info.append((info_type, info))
        
        return unknown_info
    
    def get_llm_query_info(self):
        """Get unknown information that should be queried by the LLM"""
        unknown_info = []
        
        for info_type, info in self.knowledge_goals.items():
            if (not info['known'] and 
                info['ask_method'] == 'llm' and
                self.trust_level >= info['min_trust']):
                unknown_info.append((info_type, info))
        
        return unknown_info
    
    def get_llm_curiosity_prompt(self):
        """Generate a prompt for the LLM to express curiosity about missing information"""
        # Get top priority unknown info that should be asked via LLM
        llm_query_info = self.get_llm_query_info()
        
        if not llm_query_info:
            return ""
        
        # Sort by priority
        llm_query_info.sort(key=lambda x: x[1]['priority'], reverse=True)
        
        # Take the highest priority item
        top_info = llm_query_info[0]
        info_type, info = top_info
        
        # Update last asked timestamp
        self.knowledge_goals[info_type]['last_asked'] = datetime.datetime.now()
        
        # Generate appropriate prompts based on info type
        prompts = {
            'professional_field': "During your response, find a natural opportunity to ask what field or profession the user works in.",
            'active_projects': "If appropriate in context, ask what the user is currently working on or what projects they're involved with.",
            'goals': "Try to understand what the user is hoping to accomplish. Ask about their goals in a natural way.",
            'challenges': "Show empathy by asking what challenges the user is facing that you might be able to help with."
        }
        
        return prompts.get(info_type, "")
    
    def generate_direct_question(self):
        """Create a natural question about missing information using direct questioning"""
        # Reset counter and increment session questions
        self.messages_since_last_question = 0
        self.questions_this_session += 1
        
        # Find highest priority unknown information for direct asking
        unknown_info = self.get_askable_unknown_info()
        if not unknown_info:
            return None
        
        # Sort by priority (highest first)
        unknown_info.sort(key=lambda x: x[1]['priority'], reverse=True)
        
        # Add some randomness - 80% chance of picking highest priority, 20% chance of picking another
        if len(unknown_info) > 1 and random.random() < 0.2:
            info_type, info = unknown_info[1]  # Pick second highest
        else:
            info_type, info = unknown_info[0]  # Pick highest priority
        
        # Mark as asked
        self.knowledge_goals[info_type]['last_asked'] = datetime.datetime.now()
        
        # Natural-sounding questions for direct asking
        questions = {
            'name': [
                "By the way, I don't think I caught your name yet. What should I call you?",
                "I'd love to address you properly. What's your name?",
                "I just realized I don't know your name yet. Would you mind telling me?"
            ],
            'location': [
                "I'm curious, where are you messaging me from?",
                "Which part of the world are you in, if you don't mind me asking?",
                "It helps me to know what area you're in. Where are you located?"
            ],
            'nationality': [
                "I'm interested in learning about different cultures. Where are you originally from?",
                "What's your cultural background, if you don't mind sharing?",
                "Do you identify with a particular nationality or cultural heritage?"
            ],
            'family': [
                "Do you have family around you? I'm just curious about who you might be talking with me about.",
                "Is there anyone in your family who you might share our conversations with?",
                "Are you using me to help just yourself, or is this something for your family too?"
            ],
        }
        
        # Pick a random variant of the question for variety
        return random.choice(questions.get(info_type, ["Tell me more about yourself."]))
    
    def check_for_date_mentions(self, message):
        """Check if the user mentioned a date that should be remembered"""
        # Look for date patterns
        date_patterns = [
            r"(?:on|by) (?:the )?((?:January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec) \d{1,2}(?:st|nd|rd|th)?(?:,? \d{4})?)",
            r"(?:on|by) (?:the )?(\d{1,2}(?:st|nd|rd|th)? (?:of )?(?:January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)(?:,? \d{4})?)",
            r"(?:on|by) (\d{1,2}/\d{1,2}(?:/\d{2,4})?)"
        ]
        
        for pattern in date_patterns:
            date_match = re.search(pattern, message, re.IGNORECASE)
            if date_match:
                return date_match.group(1)
        
        return None
    
    def generate_date_follow_up(self, date_str):
        """Generate a follow-up question about an important date"""
        follow_ups = [
            f"I noticed you mentioned {date_str}. Would you like me to remember that date for you?",
            f"Is {date_str} an important date I should keep track of for you?",
            f"Would it be helpful if I remembered {date_str} for future reference?"
        ]
        
        return random.choice(follow_ups)
    
    def update_trust_level(self, message_length, personal_info_shared):
        """Update trust level based on interaction patterns"""
        # Longer messages generally indicate more trust
        if message_length > 200:
            self.trust_level = min(10, self.trust_level + 0.2)
        
        # Sharing personal information is a strong trust indicator
        if personal_info_shared:
            self.trust_level = min(10, self.trust_level + 0.5)
        
        # Ensure trust level stays within bounds
        self.trust_level = max(1, min(10, self.trust_level))
        
        # Round to nearest tenth for storage
        self.trust_level = round(self.trust_level, 1)
        
        # Save to user data
        self.jupiter.user_data['trust_level'] = self.trust_level
        self.jupiter.save_user_data()