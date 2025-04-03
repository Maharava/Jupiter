import os
import json
import argparse
import datetime
from dotenv import load_dotenv
import time
import logging

from models.llm_client import LLMClient
from models.user_data_manager import UserDataManager
from utils.logger import Logger
from ui.terminal_interface import TerminalInterface
from ui.gui_interface import GUIInterface
from core.info_extractor import InfoExtractor
from core.chat_engine import ChatEngine
from io_wake_word.io_wake_word import WakeWordDetector

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
            "user_data_file": "user_data.json",
            "data_folder": "data"  # Add this line
        },
        "ui": {
            "jupiter_color": "yellow",
            "user_color": "magenta"
        }
    }

def main():
    """Main entry point for Jupiter Chat"""
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger = logging.getLogger("main")

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

    # Create wake word detector but don't start it yet
    detector = None
    discord_module = None
    
    try:
        # Initialize Discord if enabled
        if config.get('discord', {}).get('enabled', False):
            from utils.discord import DiscordModule
            
            discord_module = DiscordModule(
                chat_engine=chat_engine,
                user_data_manager=user_data_manager,
                logger=logger,
                config=config.get('discord', {})
            )
            discord_module.start()
        
        # Define wake word initialization function that runs after login
        def initialize_wake_word():
            nonlocal detector
            if config.get('voice', {}).get('enabled', False):
                try:
                    # Get wake word from current persona
                    from utils.config import get_current_persona
                    persona = get_current_persona(config)
                    wake_word = persona.get("wake_word", "jupiter")
                    
                    # Initialize wake word detector
                    model_path = f"models/{wake_word}-wake-word.pth"
                    # Fall back to default if model doesn't exist
                    if not os.path.exists(model_path):
                        model_path = "models/jupiter-wake-word.pth"
                        logger.warning(f"Wake word model for '{wake_word}' not found, using default model")
                        
                    detector = WakeWordDetector(model_path=model_path, device_index=0, threshold=0.85)
                    
                    # Define a useful callback that actually interacts with the chat engine
                    def on_wake_word_detected(confidence):
                        print(f"\nWake word detected! (confidence: {confidence:.4f})")
                        chat_engine.ui.prompt_for_input("How can I help you?")
                    
                    detector.register_detection_callback(on_wake_word_detected)
                    detector.start()
                    print("Listening for wake word... (Chat is still active)")
                except Exception as e:
                    print(f"Error initializing wake word: {e}")
        
        # Register the wake word initialization to happen after login
        chat_engine.register_login_callback(initialize_wake_word)
        
        # Run the chat engine (this is blocking)
        chat_engine.run()
        
    finally:
        # Ensure proper cleanup of resources
        if discord_module:
            try:
                discord_module.stop()
                logging.info("Discord client stopped")
            except Exception as e:
                logging.error(f"Error stopping Discord client: {e}")
                
        if detector:
            detector.stop()

if __name__ == "__main__":
    main()