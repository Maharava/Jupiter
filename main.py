import os
import json
import argparse
import datetime

from models.llm_client import LLMClient
from models.user_model import UserModel
from utils.logger import Logger
from ui.terminal_interface import TerminalInterface
from ui.gui_interface import GUIInterface
from core.info_extractor import InfoExtractor
from core.chat_engine import ChatEngine

def load_config():
    """Load configuration from file or use defaults"""
    config_path = "config/default_config.json"
    
    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    else:
        # Default configuration
        return {
            "llm": {
                "provider": "ollama",
                "api_url": "http://localhost:11434",
                "default_model": "gemma3",
                "chat_temperature": 0.7,
                "extraction_temperature": 0.2,
                "token_limit": 8192
            },
            "paths": {
                "prompt_folder": "prompts",
                "logs_folder": "logs",
                "user_data_file": "user_data.json"
            },
            "ui": {
                "jupiter_color": "yellow",
                "user_color": "magenta"
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
        test_mode=args.test  # Pass test mode flag to LLM client
    )
    
    user_model = UserModel(config['paths']['user_data_file'])
    
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
    
    # Create folders if they don't exist
    for folder in [config['paths']['prompt_folder'], config['paths']['logs_folder']]:
        os.makedirs(folder, exist_ok=True)
    
    # Display log processing message in GUI if using it
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
        user_model=user_model,
        logs_folder=config['paths']['logs_folder'],
        prompt_folder=config['paths']['prompt_folder'],
        ui=ui,  # Pass the UI object
        test_mode=args.test
    )
    
    # Process any unprocessed logs (skip in test mode)
    if not args.test:
        info_extractor.process_all_unprocessed_logs()
    
    # Initialize chat engine with test mode flag
    chat_engine = ChatEngine(
        llm_client=llm_client,
        user_model=user_model,
        logger=logger,
        ui=ui,
        config=config,
        test_mode=args.test
    )
    
    # Run chat interface
    chat_engine.run()

if __name__ == "__main__":
    main()