import discord
import asyncio
import logging
import time
from typing import Dict, Any, List, Optional

class JupiterDiscordClient:
    """Discord client for Jupiter - handles connection and message processing"""
    
    def __init__(self, chat_engine, user_data_manager, config):
        """Initialize Discord client with dependencies"""
        self.chat_engine = chat_engine
        self.user_data_manager = user_data_manager
        self.config = config
        
        # Setup logger
        self.logger = logging.getLogger("jupiter.discord")
        if not self.logger.handlers:
            handler = logging.FileHandler('logs/discord.log')
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
        
        # Initialize Discord client
        intents = discord.Intents.default()
        intents.message_content = True
        self.client = discord.Client(intents=intents)
        
        # Channel monitoring state - {channel_id: expiry_timestamp}
        self.active_channels = {}
        
        # Setup event handlers
        self.setup_event_handlers()
        
        # Running state
        self.is_running = False
        
    def setup_event_handlers(self):
        """Set up Discord event handlers"""
        
        @self.client.event
        async def on_ready():
            """Handle Discord client ready event"""
            self.logger.info(f"Logged in as {self.client.user}")
            self.is_running = True
        
        @self.client.event
        async def on_message(message):
            """Handle incoming Discord messages"""
            # Skip messages from self
            if message.author == self.client.user:
                return
                
            # Check for commands
            if message.content.startswith('/'):
                await self.handle_command(message)
                return
                
            # Process regular message
            await self.process_message(message)
            
        @self.client.event
        async def on_error(event, *args, **kwargs):
            """Handle Discord client errors"""
            self.logger.error(f"Discord error in {event}")
            
    async def handle_command(self, message):
        """Handle Discord commands"""
        # Split the message into command and arguments
        parts = message.content.split(None, 1)
        command = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""
        
        # Handle ID command
        if command == '/id':
            await self.cmd_show_id(message)
            
        # Handle link command
        elif command == '/link':
            await self.cmd_link_identity(message, args)
            
        # Handle help command
        elif command == '/help':
            await self.cmd_show_help(message)
            
        # Unknown command
        else:
            # Forward unknown commands to Jupiter
            await self.process_message(message)
            
    async def cmd_show_id(self, message):
        """Show user's Jupiter ID information"""
        # Get Jupiter user data
        user = self._get_jupiter_user(message.author)
        
        if not user or 'user_id' not in user:
            await message.channel.send("You don't have a Jupiter ID yet. Try chatting with me first!")
            return
            
        # Format user information
        user_id = user.get('user_id', 'Unknown')
        name = user.get('name', message.author.name)
        platforms = user.get('platforms', {})
        platform_list = [p for p, enabled in platforms.items() if enabled]
        platform_str = ", ".join(platform_list) if platform_list else "discord only"
        
        # Create response
        response = f"""
**Your Jupiter ID Information**
ID: `{user_id}`
Name: {name}
Platforms: {platform_str}

This ID lets Jupiter recognize you across different platforms.
Use `/link [platform] [username]` to connect with other platforms.
"""
        await message.channel.send(response)
        
    async def cmd_link_identity(self, message, args):
        """Link user identity across platforms"""
        if not args:
            await message.channel.send(
                "Usage: `/link [platform] [username]`\n"
                "Example: `/link gui JohnDoe`\n\n"
                "Available platforms: gui, terminal"
            )
            return
            
        # Parse arguments
        parts = args.split(None, 1)
        if len(parts) < 2:
            await message.channel.send("Please specify both platform and username.")
            return
            
        platform, username = parts
        
        # Validate platform
        if platform.lower() not in ["gui", "terminal"]:
            await message.channel.send(f"Unknown platform '{platform}'. Supported platforms: gui, terminal")
            return
            
        # Get Discord user data
        discord_user = self._get_jupiter_user(message.author)
        
        if not discord_user or 'user_id' not in discord_user:
            await message.channel.send("You don't have a Jupiter ID yet. Try chatting with me first!")
            return
            
        # Attempt linking
        try:
            source_platform = "discord"
            source_name = message.author.name
            target_platform = platform.lower()
            target_name = username
            
            success, result_message = self.user_data_manager.link_platform_identities(
                source_platform, source_name,
                target_platform, target_name
            )
            
            if success:
                await message.channel.send(f"✅ Success! {result_message}")
            else:
                await message.channel.send(f"❌ Linking failed: {result_message}")
                
        except Exception as e:
            self.logger.error(f"Error linking identities: {str(e)}", exc_info=True)
            await message.channel.send("An error occurred while linking identities. Please try again later.")
            
    async def cmd_show_help(self, message):
        """Show help information"""
        help_text = """
**Jupiter Discord Commands**

`/id` - Show your Jupiter ID information
`/link [platform] [username]` - Link your identity with another platform
`/help` - Show this help message

You can chat with me in DMs anytime. In channels, just mention "Jupiter" and I'll respond!
"""
        await message.channel.send(help_text)
    
    async def process_message(self, message):
        """Process incoming Discord message"""
        try:
            # Check if we should process this message
            if not self._should_process_message(message):
                return
                
            # Get or create Jupiter user for this Discord user
            jupiter_user = self._get_jupiter_user(message.author)
            
            # Log the incoming message
            channel_type = "DM" if isinstance(message.channel, discord.DMChannel) else "Channel"
            channel_info = "Direct Message" if isinstance(message.channel, discord.DMChannel) else f"{message.guild.name}/{message.channel.name}"
            self.logger.info(f"[{channel_type}] {message.author.name}: {message.content} ({channel_info})")
            
            # Set typing indicator for better UX
            async with message.channel.typing():
                # Generate response through Jupiter's chat engine
                response = self._generate_response(jupiter_user, message.content)
                
                # Log Jupiter's response
                self.logger.info(f"[{channel_type}] Jupiter: {response[:100]}... ({channel_info})")
                
                # Send response
                if response:
                    await self._send_response(message.channel, response)
        
        except Exception as e:
            self.logger.error(f"Error processing Discord message: {str(e)}", exc_info=True)
    
    def _should_process_message(self, message) -> bool:
        """Determine if we should process this message"""
        # Always process DMs
        if isinstance(message.channel, discord.DMChannel):
            return True
            
        # Check if in allowed servers/channels
        if not self._is_allowed(message):
            return False
            
        # Check if message is in an active channel
        channel_id = message.channel.id
        is_active_channel = (channel_id in self.active_channels and 
                            self.active_channels[channel_id] > time.time())
        
        # Check if message mentions Jupiter
        mentions_jupiter = self._mentions_jupiter(message.content)
        
        # If it mentions Jupiter, make this channel active
        if mentions_jupiter:
            timeout = self.config.get("observation_timeout", 300)  # Default 5 minutes
            self.active_channels[channel_id] = time.time() + timeout
            self.logger.info(f"Activated channel {channel_id} for {timeout} seconds")
        
        return is_active_channel or mentions_jupiter
    
    def _is_allowed(self, message) -> bool:
        """Check if message is from an allowed server and channel"""
        allowed_servers = self.config.get("allowed_servers", [])
        allowed_channels = self.config.get("allowed_channels", [])
        
        # If lists are empty, allow all
        if not allowed_servers and not allowed_channels:
            return True
            
        # Check server
        if allowed_servers and message.guild and message.guild.id not in allowed_servers:
            return False
            
        # Check channel
        if allowed_channels and message.channel.id not in allowed_channels:
            return False
            
        return True
    
    def _mentions_jupiter(self, content) -> bool:
        """Check if message mentions Jupiter"""
        name_variations = self.config.get("name_variations", ["jupiter", "jup"])
        return any(name.lower() in content.lower() for name in name_variations)
    
    def _get_jupiter_user(self, discord_user) -> Dict[str, Any]:
        """Get or create Jupiter user for Discord user"""
        username = discord_user.name
        discord_id = str(discord_user.id)
        
        # Try to find existing user by platform-specific identifier
        user, user_id = self.user_data_manager.get_user_by_name(username, "discord")
        
        if not user:
            # Create new user through Jupiter's system
            user, _ = self.user_data_manager.identify_user(username, "discord")
            
            # Add Discord metadata
            if user:
                user["discord_id"] = discord_id
                self.user_data_manager.set_current_user(user)
                self.user_data_manager.save_current_user()
        
        return user
    
    def _generate_response(self, jupiter_user, message_text) -> str:
        """Generate a response from Jupiter's chat engine"""
        # Save current user state
        original_user = self.chat_engine.user_data_manager.current_user
        
        try:
            # Set Jupiter's current user to the Discord user
            self.chat_engine.user_data_manager.set_current_user(jupiter_user)
            
            # Prepare message for LLM (reusing Jupiter's own method)
            llm_message = self.chat_engine.prepare_message_for_llm(message_text)
            
            # Generate response
            response = self.chat_engine.llm_client.generate_chat_response(
                llm_message, 
                temperature=self.chat_engine.config['llm']['chat_temperature']
            )
            
            return response
            
        except Exception as e:
            self.logger.error(f"Error generating response: {str(e)}", exc_info=True)
            return "I'm having trouble responding right now. Please try again later."
            
        finally:
            # Restore original user
            self.chat_engine.user_data_manager.set_current_user(original_user)
    
    async def _send_response(self, channel, response):
        """Send response, handling multiple chunks if needed"""
        try:
            # Check if response is too long for a single message
            if len(response) > 2000:
                chunks = self._split_message(response)
                for chunk in chunks:
                    await channel.send(chunk)
                    # Small delay between chunks
                    await asyncio.sleep(0.5)
            else:
                await channel.send(response)
                
        except Exception as e:
            self.logger.error(f"Error sending Discord response: {str(e)}", exc_info=True)
    
    def _split_message(self, message, max_length=2000) -> List[str]:
        """Split message into chunks for Discord's message length limit"""
        chunks = []
        current_chunk = ""
        
        for line in message.split('\n'):
            # If adding this line would exceed limit, start a new chunk
            if len(current_chunk) + len(line) + 1 > max_length:
                chunks.append(current_chunk)
                current_chunk = line
            else:
                if current_chunk:
                    current_chunk += '\n' + line
                else:
                    current_chunk = line
        
        # Add the last chunk
        if current_chunk:
            chunks.append(current_chunk)
            
        return chunks
    
    def start(self):
        """Start the Discord client"""
        try:
            token = self.config.get("token", "")
            if not token:
                self.logger.error("No Discord token provided")
                return
                
            self.logger.info("Starting Discord client")
            self.client.run(token)
        except Exception as e:
            self.logger.error(f"Failed to start Discord client: {str(e)}", exc_info=True)
    
    def stop(self):
        """Stop the Discord client"""
        self.is_running = False
        
        # Close Discord client
        asyncio.run_coroutine_threadsafe(
            self.client.close(), self.client.loop
        )
        self.logger.info("Discord client stopped")