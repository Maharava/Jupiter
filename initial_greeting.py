import os
import json

def initial_greeting(jupiter):
    """Handle initial greeting and user identification"""
    
    # Check if any users exist in the system
    if os.path.exists(jupiter.user_data_file):
        with open(jupiter.user_data_file, 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
                # Check if there are any known users
                if data and 'known_users' in data and data['known_users']:
                    # We have returning users, ask if they're returning
                    print(f"{jupiter.JUPITER_COLOR}Jupiter:{jupiter.Style.RESET_ALL} Hi there! Have we talked before? (yes/no)")
                    response = input(f"{jupiter.USER_COLOR}User:{jupiter.Style.RESET_ALL} ").strip().lower()
                    
                    if response in ['yes', 'y', 'yeah', 'yep', 'yup']:
                        # Ask for name to identify returning user
                        print(f"{jupiter.JUPITER_COLOR}Jupiter:{jupiter.Style.RESET_ALL} Great to see you again! What's your name so I can load your information?")
                        name = input(f"{jupiter.USER_COLOR}User:{jupiter.Style.RESET_ALL} ").strip()
                        
                        # Try to find user in known_users
                        if 'known_users' in data and name.lower() in [u.lower() for u in data['known_users']]:
                            # Find the proper capitalization of the name
                            for user_name in data['known_users']:
                                if user_name.lower() == name.lower():
                                    name = user_name
                                    break
                            
                            # Load user data
                            jupiter.user_data = data['known_users'][name]
                            jupiter.user_data['name'] = name
                            
                            # Update curiosity with loaded data
                            jupiter.curiosity.update_known_info()
                            
                            print(f"{jupiter.JUPITER_COLOR}Jupiter:{jupiter.Style.RESET_ALL} Welcome back, {name}! It's great to chat with you again.")
                            return
                        else:
                            print(f"{jupiter.JUPITER_COLOR}Jupiter:{jupiter.Style.RESET_ALL} I don't seem to have a record for that name. Let's start fresh!")
                            # Continue to new user flow
                    else:
                        print(f"{jupiter.JUPITER_COLOR}Jupiter:{jupiter.Style.RESET_ALL} No problem! Let's get to know each other.")
                        # Continue to new user flow
            except json.JSONDecodeError:
                # Empty or invalid file, treat as new user
                pass
    
    # New user flow - ask basic questions
    print(f"{jupiter.JUPITER_COLOR}Jupiter:{jupiter.Style.RESET_ALL} I'm Jupiter, your AI assistant. What's your name?")
    name = input(f"{jupiter.USER_COLOR}User:{jupiter.Style.RESET_ALL} ").strip()
    
    # Initialize new user data
    jupiter.user_data = {'name': name}
    
    # If known_users doesn't exist in the file, create it
    data = jupiter.load_user_data()
    if 'known_users' not in data:
        data['known_users'] = {}
    
    # Add user to known_users
    data['known_users'][name] = jupiter.user_data
    
    # Save updated data
    with open(jupiter.user_data_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)
    
    # Update curiosity
    jupiter.curiosity.update_known_info()
    
    print(f"{jupiter.JUPITER_COLOR}Jupiter:{jupiter.Style.RESET_ALL} Nice to meet you, {name}! I'll remember you for next time.")
    
    # Ask about location
    print(f"{jupiter.JUPITER_COLOR}Jupiter:{jupiter.Style.RESET_ALL} Where are you messaging me from today?")
    location = input(f"{jupiter.USER_COLOR}{name}:{jupiter.Style.RESET_ALL} ").strip()
    
    # Save location
    jupiter.user_data['location'] = location
    data['known_users'][name] = jupiter.user_data
    
    with open(jupiter.user_data_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)
    
    # Update curiosity
    jupiter.curiosity.update_known_info()
    
    print(f"{jupiter.JUPITER_COLOR}Jupiter:{jupiter.Style.RESET_ALL} {location} - that's great! How can I help you today?")
