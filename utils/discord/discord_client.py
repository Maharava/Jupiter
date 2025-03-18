# Update discord_client.py to include better error handling

import discord
import asyncio
import traceback
from .message_handler import MessageHandler
from .user_mapper import UserMapper
from .response_formatter import ResponseFormatter
from .discord_logger import DiscordLogger

class DiscordClient:
    """Handles Discord connection and events"""
    
    def __init__(self, chat_engine, user_model, logger, config):
        self.chat_engine = chat_engine
        self.config = config
        self.is_running = False
        
        # Set up Discord-specific logger
        self.discord_logger = DiscordLogger(logger)
        
        # Create Discord client
        intents = discord.Intents.default()
        intents.message_content = True
        self.client = discord.Client(intents=intents)
        
        # Create components
        self.user_mapper = UserMapper(user_model, config)
        self.response_formatter = ResponseFormatter()
        
        # Create message handler with client reference (self)
        self.message_handler = MessageHandler(
            chat_engine=chat_engine,
            user_mapper=self.user_mapper,
            config=config,
            client=self  # Pass self reference
        )
        
        # Set up event handlers
        self.setup_event_handlers()
    
    def setup_event_handlers(self):
        @self.client.event
        async def on_ready():
            self.discord_logger.log_info(f"Logged in as {self.client.user}")
            self.is_running = True
        
        @self.client.event
        async def on_message(message):
            try:
                # Skip messages from self
                if message.author == self.client.user:
                    return
                
                # Process the message
                await self.message_handler.handle_message(message)
            except Exception as e:
                self.discord_logger.log_error(
                    f"Error processing message: {message.content}", e
                )
                traceback.print_exc()
        
        @self.client.event
        async def on_error(event, *args, **kwargs):
            self.discord_logger.log_error(f"Discord error in {event}")
    
    def generate_response(self, jupiter_user, message_text):
        """Generate a response from Jupiter without modifying its core"""
        # Save current user state
        original_user = self.chat_engine.user_model.current_user
        
        try:
            # Set Jupiter's current user to the Discord user
            self.chat_engine.user_model.set_current_user(jupiter_user)
            
            # Prepare message for LLM (reusing Jupiter's own method)
            llm_message = self.chat_engine.prepare_message_for_llm(message_text)
            
            # Generate response using Jupiter's LLM client
            response = self.chat_engine.llm_client.generate_chat_response(
                llm_message, 
                temperature=self.chat_engine.config['llm']['chat_temperature']
            )
            
            # Format response for Discord
            formatted_response = self.response_formatter.format_response(response)
            return formatted_response
        
        except Exception as e:
            self.discord_logger.log_error("Error generating response", e)
            return "I'm having trouble responding right now. Please try again later."
        
        finally:
            # Restore original user
            self.chat_engine.user_model.set_current_user(original_user)
    
    def start(self):
        """Start the Discord bot"""
        try:
            token = self.config["token"]
            if not token:
                self.discord_logger.log_error("No Discord token provided")
                return
                
            self.discord_logger.log_info("Starting Discord bot")
            self.client.run(token)
        except Exception as e:
            self.discord_logger.log_error("Failed to start Discord bot", e)
    
    def stop(self):
        """Stop the Discord bot"""
        self.is_running = False
        asyncio.run_coroutine_threadsafe(
            self.client.close(), self.client.loop
        )
        self.discord_logger.log_info("Discord bot stopped")