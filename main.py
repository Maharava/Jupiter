import os
import json
import argparse
import datetime
from dotenv import load_dotenv
import time

# Add io-wake-word to imports
from models.llm_client import LLMClient
from models.user_data_manager import UserDataManager
from utils.logger import Logger
from ui.terminal_interface import TerminalInterface
from ui.gui_interface import GUIInterface
from core.info_extractor import InfoExtractor
from core.chat_engine import ChatEngine

load_dotenv()

def load_config():
    """Load configuration from file or use defaults"""
    config_path = "config/default_config.json"
    
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                
                # Inject Discord token from environment if available
                if 'discord' in config and os.getenv('JUPITER_DISCORD_TOKEN'):
                    config['discord']['token'] = os.getenv('JUPITER_DISCORD_TOKEN')
                    
                return config
        except Exception as e:
            print(f"Error loading configuration: {e}")
    
    # Default configuration (fallback)
    return {
        "llm": {
            "provider": "ollama",
            "api_url": "http://localhost:11434",
            "default_model": "gemma3",
            "chat_temperature": 0.7,
            "extraction_temperature": 0.2,
            "token_limit": 8192
        },
        "chat": {
            "max_history_messages": 100
        },
        "paths": {
            "prompt_folder": "prompts",
            "logs_folder": "logs",
            "user_data_file": "user_data.json"
        },
        "ui": {
            "jupiter_color": "yellow",
            "user_color": "magenta"
        },
        "voice": {
            "enabled": True,
            "wake_word_model": "jupiter-wake-word.pth",  # This should point to your Io model
            "stt_model_size": "tiny"
        }
    }

def main():
    """Main entry point for Jupiter Chat"""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Jupiter Chat")
    parser.add_argument("--gui", action="store_true", help="Use GUI interface instead of terminal")
    parser.add_argument("--test", action="store_true", help="Run in offline test mode without LLM backend")
    args = parser.parse_args()
    
    # Load configuration
    config = load_config()
    
    # Initialize components
    llm_client = LLMClient(
        api_url=config['llm']['api_url'],
        default_model=config['llm']['default_model'],
        test_mode=args.test
    )
    
    # Create unified user data manager
    user_data_manager = UserDataManager(config['paths']['user_data_file'])
    
    logger = Logger(config['paths']['logs_folder'])
    
    # Choose interface based on argument
    if args.gui:
        ui = GUIInterface(
            jupiter_color=config['ui']['jupiter_color'],
            user_color=config['ui']['user_color']
        )
    else:
        ui = TerminalInterface(
            jupiter_color=config['ui']['jupiter_color'],
            user_color=config['ui']['user_color']
        )
    
    # Create necessary folders
    for folder in [config['paths']['prompt_folder'], config['paths']['logs_folder']]:
        os.makedirs(folder, exist_ok=True)
    
    # Display startup message
    if args.test:
        if args.gui and hasattr(ui, 'set_status'):
            ui.set_status("Running in TEST MODE - No LLM connection", True)
        else:
            print("⚠️ Running in TEST MODE - No LLM connection")
    else:
        if args.gui and hasattr(ui, 'set_status'):
            ui.set_status("Processing previous conversation logs...", True)
        else:
            print("Processing previous conversation logs...")
        
    # Initialize info extractor
    info_extractor = InfoExtractor(
        llm_client=llm_client,
        user_data_manager=user_data_manager,
        logs_folder=config['paths']['logs_folder'],
        prompt_folder=config['paths']['prompt_folder'],
        ui=ui,
        test_mode=args.test
    )
    
    # Process any unprocessed logs (skip in test mode)
    if not args.test:
        info_extractor.process_all_unprocessed_logs()
    
    # Initialize chat engine
    chat_engine = ChatEngine(
        llm_client=llm_client,
        user_data_manager=user_data_manager,
        logger=logger,
        ui=ui,
        config=config,
        test_mode=args.test
    )

    # Initialize calendar notification system if enabled
    if config.get('calendar', {}).get('enable_notifications', True):
        from utils.calendar import initialize_calendar_daemon
        
        if args.gui:
            # For GUI mode, set up later with root window
            pass
        else:
            # For terminal mode, pass the terminal UI
            initialize_calendar_daemon(gui_root=None, terminal_ui=ui, enable_voice=True)

    # Add Discord integration if enabled
    if config.get('discord', {}).get('enabled', False):
        from utils.discord import DiscordModule
        
        # Initialize Discord module
        discord_module = DiscordModule(
            chat_engine=chat_engine,
            user_data_manager=user_data_manager,
            logger=logger,
            config=config.get('discord', {})
        )
        
        # Start in a separate thread
        import threading
        discord_thread = threading.Thread(target=discord_module.start, daemon=True)
        discord_thread.start()
        
        time.sleep(2)  # Give Discord client time to connect
        if discord_module.is_running():
            print("✅ Discord connection successful")
        else:
            print("⚠️ Discord failed to connect - check logs/discord.log for details")

    # Run chat interface
    chat_engine.run()

if __name__ == "__main__":
    main()