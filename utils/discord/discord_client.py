import discord
import asyncio
import traceback
import threading
import queue
from .message_handler import MessageHandler
from .user_mapper import UserMapper
from .response_formatter import ResponseFormatter
from .discord_logger import DiscordLogger

class DiscordClient:
    """Handles Discord connection and events"""
    
    def __init__(self, chat_engine, user_data_manager, logger, config):
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
        self.user_mapper = UserMapper(user_data_manager, config)
        self.response_formatter = ResponseFormatter()
        
        # Create message handler with client reference
        self.message_handler = MessageHandler(
            chat_engine=chat_engine,
            user_mapper=self.user_mapper,
            config=config,
            client=self
        )
        
        # Add thread safety with a request queue and lock
        self.request_queue = queue.Queue()
        self.user_lock = threading.Lock()
        self.processing_thread = None
        
        # Set up event handlers
        self.setup_event_handlers()
    
    def setup_event_handlers(self):
        @self.client.event
        async def on_ready():
            self.discord_logger.log_info(f"Logged in as {self.client.user}")
            self.is_running = True
            
            # Start the request processing thread when Discord is ready
            self.start_processing_thread()
        
        @self.client.event
        async def on_message(message):
            try:
                # Skip messages from self
                if message.author == self.client.user:
                    return
                
                # Instead of processing directly, add to queue
                self.request_queue.put(message)
                
            except Exception as e:
                self.discord_logger.log_error(
                    f"Error queuing message: {message.content}", e
                )
                traceback.print_exc()
        
        @self.client.event
        async def on_error(event, *args, **kwargs):
            self.discord_logger.log_error(f"Discord error in {event}")
    
    def start_processing_thread(self):
        """Start a thread to process messages from the queue"""
        if self.processing_thread is None or not self.processing_thread.is_alive():
            self.processing_thread = threading.Thread(
                target=self._process_message_queue,
                daemon=True,
                name="DiscordMessageProcessor"
            )
            self.processing_thread.start()
            self.discord_logger.log_info("Started Discord message processing thread")
    
    def _process_message_queue(self):
        """Process messages from the queue sequentially"""
        while self.is_running:
            try:
                # Get message from queue (with timeout to allow checking is_running)
                try:
                    message = self.request_queue.get(timeout=0.5)
                except queue.Empty:
                    continue
                
                # Process the message with exclusive access to user data
                self._process_single_message(message)
                
                # Mark task as done
                self.request_queue.task_done()
                
            except Exception as e:
                self.discord_logger.log_error(f"Error in message queue processor: {e}")
                
    def _process_single_message(self, message):
        """Process a single Discord message with proper locking"""
        try:
            # Use a lock to ensure exclusive access to user data
            with self.user_lock:
                # Let the message handler process the message
                # This will be run in our dedicated thread, not the Discord event loop
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                try:
                    loop.run_until_complete(self.message_handler.handle_message(message))
                finally:
                    loop.close()
                    
        except Exception as e:
            self.discord_logger.log_error(
                f"Error processing Discord message: {message.content}", e
            )
            traceback.print_exc()
    
    def generate_response(self, jupiter_user, message_text):
        """Generate a response from Jupiter without modifying its core"""
        # Save current user state
        original_user = self.chat_engine.user_data_manager.current_user
        
        try:
            # Set Jupiter's current user to the Discord user
            with self.user_lock:  # Add lock to prevent user switching conflicts
                self.chat_engine.user_data_manager.set_current_user(jupiter_user)
                
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
            with self.user_lock:
                self.chat_engine.user_data_manager.set_current_user(original_user)
    
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
        
        # Wait for processing thread to finish
        if self.processing_thread and self.processing_thread.is_alive():
            self.processing_thread.join(timeout=2.0)
        
        # Stop Discord client
        asyncio.run_coroutine_threadsafe(
            self.client.close(), self.client.loop
        )
        self.discord_logger.log_info("Discord bot stopped")