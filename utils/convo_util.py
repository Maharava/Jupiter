import os
import json 
from datetime import datetime 
from config import * 

def log_conversation(conversation_file, user_input, response):
    # Load existing conversation data if the file exists and is not empty
    if os.path.exists(conversation_file) and os.path.getsize(conversation_file) > 0:
        with open(conversation_file, 'r') as file:
            conversation_data = json.load(file)
    else:
        conversation_data = []

    # Append new conversation entry
    entry = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "user": user_input,
        f"{config.ai_name}": response
    }
    conversation_data.append(entry)

    # Save the updated conversation data back to the JSON file
    with open(conversation_file, 'w') as file:
        json.dump(conversation_data, file, indent=4)

def fetch_context(conversation_file):
    try:
        with open(conversation_file, 'r') as file:
            return file.read().strip()
    except FileNotFoundError:
        print(f"Conversation file {conversation_file} not found.")
        return ""
    except IOError as e:
        print(f"Error reading conversation file: {e}")
        return ""

def load_prompts_and_user_info():
    base_path = os.path.dirname(os.path.abspath(__file__))
    info_path = os.path.join(base_path, '..', 'info')  # Adjust the path to point to the 'info' folder in the root directory
    prompt_name = 'jupiter.txt'
    if not config.jupiter:
        prompt_name = 'saturn.txt'
    with open(os.path.join(info_path, prompt_name), 'r') as file:
        print(prompt_name)
        core_prompt = file.read().strip()
        print(core_prompt)
    with open(os.path.join(info_path, 'user_info.txt'), 'r') as file:
        user_info = file.read().strip()
    return core_prompt, user_info