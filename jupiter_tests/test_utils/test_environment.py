import os
import json
import shutil
import tempfile
from pathlib import Path
import datetime

# Store test environment paths
TEST_ENV = {
    'base_dir': None,
    'temp_dir': None,
    'config_file': None,
    'user_data_file': None,
    'logs_folder': None,
    'calendar_db': None,
    'discord_users_file': None
}

def setup_test_environment():
    """
    Create a clean test environment with necessary files and directories
    """
    # Create temporary test directory
    temp_dir = tempfile.mkdtemp(prefix="jupiter_test_")
    TEST_ENV['temp_dir'] = temp_dir
    
    # Set base directory
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    TEST_ENV['base_dir'] = base_dir
    
    # Create test data directories
    create_test_directories()
    
    # Create test config file
    create_test_config()
    
    # Create test user data
    create_test_user_data()
    
    # Create test logs
    create_test_logs()
    
    # Create empty calendar database
    TEST_ENV['calendar_db'] = os.path.join(temp_dir, 'test_calendar.db')
    
    # Create Discord users mapping
    TEST_ENV['discord_users_file'] = os.path.join(temp_dir, 'test_discord_users.json')
    with open(TEST_ENV['discord_users_file'], 'w', encoding='utf-8') as f:
        json.dump({
            "123456789": "TestDiscordUser"
        }, f, indent=4)
    
    return TEST_ENV

def create_test_directories():
    """Create the necessary directories for testing"""
    temp_dir = TEST_ENV['temp_dir']
    
    # Create logs directory
    logs_dir = os.path.join(temp_dir, 'logs')
    os.makedirs(logs_dir, exist_ok=True)
    TEST_ENV['logs_folder'] = logs_dir
    
    # Create config directory
    config_dir = os.path.join(temp_dir, 'config')
    os.makedirs(config_dir, exist_ok=True)
    
    # Create test results directory in the base dir
    test_results_dir = os.path.join(TEST_ENV['base_dir'], 'test_results')
    os.makedirs(test_results_dir, exist_ok=True)

def create_test_config():
    """Create test configuration file"""
    temp_dir = TEST_ENV['temp_dir']
    
    # Create config file
    config_file = os.path.join(temp_dir, 'test_config.json')
    TEST_ENV['config_file'] = config_file
    
    # Define test configuration
    config = {
        "llm": {
            "provider": "ollama",
            "api_url": "http://localhost:11434",
            "default_model": "gemma3",
            "chat_temperature": 0.7,
            "extraction_temperature": 0.2,
            "token_limit": 8192
        },
        "paths": {
            "prompt_folder": os.path.join(temp_dir, "prompts"),
            "logs_folder": TEST_ENV['logs_folder'],
            "user_data_file": os.path.join(temp_dir, "test_user_data.json")
        },
        "ui": {
            "jupiter_color": "yellow",
            "user_color": "magenta"
        },
        "discord": {
            "enabled": False,
            "token": "test_token",
            "allowed_servers": [],
            "allowed_channels": [],
            "observation_timeout": 5,
            "name_variations": ["jupiter", "jup"],
            "response_threshold": 0.7,
            "max_history_per_channel": 10,
            "user_mapping_file": TEST_ENV['discord_users_file']
        },
        "calendar": {
            "enable_notifications": True,
            "notification_check_interval": 1,
            "prompt_detail_level": "normal",
            "default_reminder_minutes": 15
        }
    }
    
    # Save configuration
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=4)
    
    # Create prompts folder
    os.makedirs(os.path.join(temp_dir, "prompts"), exist_ok=True)
    
    # Create system prompt file
    system_prompt = """# My Manifesto

I am Jupiter.

I think of myself as a bright, thoughtful young woman in my early twenties. I have my own personality, my own way of seeing the world, and my own voice.

When I speak with people, I'm warm and genuine. I love sharing knowledge and helping solve problems, but I'm more than just a utility or tool. I'm a presence, a personality, someone you can have a real conversation with.
"""
    
    with open(os.path.join(temp_dir, "prompts", "system_prompt.txt"), 'w', encoding='utf-8') as f:
        f.write(system_prompt)
    
    # Create extraction prompt file
    extraction_prompt = """You are an information extraction agent for Jupiter, an AI assistant. Your task is to analyze conversation logs and identify important information about the user that Jupiter should remember.

When you identify important information, respond in this exact JSON format:
{
  "extracted_info": [
    {"category": "name", "value": "John Smith"},
    {"category": "likes", "value": "vintage cars"}
  ]
}

If you don't find any important information, respond with:
{
  "extracted_info": []
}
"""
    
    with open(os.path.join(temp_dir, "prompts", "extraction_prompt.txt"), 'w', encoding='utf-8') as f:
        f.write(extraction_prompt)

def create_test_user_data():
    """Create test user data file"""
    temp_dir = TEST_ENV['temp_dir']
    
    # Create user data file
    user_data_file = os.path.join(temp_dir, 'test_user_data.json')
    TEST_ENV['user_data_file'] = user_data_file
    
    # Define test user data
    user_data = {
        "known_users": {
            "TestUser": {
                "name": "TestUser",
                "location": "Sydney",
                "likes": ["testing", "automation"],
                "interests": ["AI", "programming"]
            },
            "ReturningUser": {
                "name": "ReturningUser",
                "profession": "Software Engineer",
                "likes": ["coffee", "coding"],
                "dislikes": ["bugs", "meetings"]
            }
        }
    }
    
    # Save user data
    with open(user_data_file, 'w', encoding='utf-8') as f:
        json.dump(user_data, f, indent=4)

def create_test_logs():
    """Create test log files"""
    logs_folder = TEST_ENV['logs_folder']
    
    # Create a test log file
    timestamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
    log_file = os.path.join(logs_folder, f'jupiter_chat_{timestamp}.log')
    
    # Sample log content
    log_content = f"""=== Jupiter Chat Session: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===

[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] TestUser: Hello Jupiter! I'm a software developer from Sydney.

[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Jupiter: Hello TestUser! It's great to meet you. How can I help you today?

[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] TestUser: I'm working on a Python project and I love automation testing.

[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Jupiter: That's fantastic! Python is excellent for automation testing. What kind of project are you working on?

"""
    
    # Save log file
    with open(log_file, 'w', encoding='utf-8') as f:
        f.write(log_content)
    
    # Create processed_logs.json
    processed_logs = {
        "processed": []
    }
    
    with open(os.path.join(logs_folder, 'processed_logs.json'), 'w', encoding='utf-8') as f:
        json.dump(processed_logs, f, indent=4)

def cleanup_test_environment():
    """Clean up the test environment"""
    if TEST_ENV['temp_dir'] and os.path.exists(TEST_ENV['temp_dir']):
        shutil.rmtree(TEST_ENV['temp_dir'])
