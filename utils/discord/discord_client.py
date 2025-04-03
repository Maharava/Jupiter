import discord
import asyncio
import logging
import time
import json
import os
from typing import Dict, Any, List, Optional
from utils.commands.discord_adapter import handle_discord_command
# Important: Add this import to ensure commands are registered
import utils.commands.command_core
from discord import app_commands

class JupiterDiscordClient:
    """Discord client for Jupiter - handles connection and message processing"""
    
    def __init__(self, chat_engine, user_data_manager, config):
        """Initialize Discord client with dependencies"""
        self.chat_engine = chat_engine
        self.user_data_manager = user_data_manager
        self.config = config
        
        # Get current persona information
        from utils.config import get_current_persona
        self.persona = get_current_persona(chat_engine.config)  # Need full config
        
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
        self.tree = app_commands.CommandTree(self.client)
        
        # Channel monitoring state - {channel_id: expiry_timestamp}
        self.active_channels = {}
        
        # Setup event handlers
        self.setup_event_handlers()
        
        # Register slash commands
        self._register_slash_commands()
        
        # Running state
        self.is_running = False
        
        # Load blacklisted channels from main config if available
        if "blacklisted_channels" in chat_engine.config.get("discord", {}):
            if isinstance(self.config, dict):
                self.config["blacklisted_channels"] = chat_engine.config["discord"]["blacklisted_channels"]
            else:
                setattr(self.config, "blacklisted_channels", chat_engine.config["discord"]["blacklisted_channels"])
        
    def _register_slash_commands(self):
        """Register slash commands with Discord"""
        # Import necessary modules
        from utils.commands.registry import registry
        import discord
        
        # Register ID command (removing guild_only parameter)
        @self.tree.command(name="id", description="Display your Jupiter ID information")
        async def id_command(interaction: discord.Interaction):
            cmd = registry.get("id")
            ctx = {
                "platform": "discord",
                "user": self._get_jupiter_user(interaction.user),
                "user_manager": self.user_data_manager,
                "interaction": interaction,
                "client": self
            }
            response = cmd.handler(ctx)
            await interaction.response.send_message(response)
        
        # Register help command (removing guild_only parameter)
        @self.tree.command(name="help", description="Show available commands")
        async def help_command(interaction: discord.Interaction):
            cmd = registry.get("help")
            ctx = {
                "platform": "discord",
                "user": self._get_jupiter_user(interaction.user),
                "user_manager": self.user_data_manager,
                "interaction": interaction,
                "client": self
            }
            response = cmd.handler(ctx)
            await interaction.response.send_message(response)
        
        # Register deaf command (removing guild_only parameter)
        @self.tree.command(name="deaf", description="Make Jupiter stop listening in the current channel")
        async def deaf_command(interaction: discord.Interaction):
            cmd = registry.get("deaf")
            ctx = {
                "platform": "discord",
                "user": self._get_jupiter_user(interaction.user),
                "user_manager": self.user_data_manager,
                "interaction": interaction,
                "client": self
            }
            response = cmd.handler(ctx)
            await interaction.response.send_message(response)
        
        # Register listen command (removing guild_only parameter)
        @self.tree.command(name="listen", description="Make Jupiter start listening in the current channel again")
        async def listen_command(interaction: discord.Interaction):
            cmd = registry.get("listen")
            ctx = {
                "platform": "discord",
                "user": self._get_jupiter_user(interaction.user),
                "user_manager": self.user_data_manager,
                "interaction": interaction,
                "client": self
            }
            response = cmd.handler(ctx)
            await interaction.response.send_message(response)
        
        # Add this to the _register_slash_commands method
        @self.tree.command(name="name", description="Change your display name")
        async def name_command(interaction: discord.Interaction, new_name: str):
            cmd = registry.get("name")
            ctx = {
                "platform": "discord",
                "user": self._get_jupiter_user(interaction.user),
                "user_manager": self.user_data_manager,
                "interaction": interaction,
                "client": self
            }
            response = cmd.handler(ctx, new_name)
            await interaction.response.send_message(response)
        
        @self.tree.command(name="link", description="Link your account with another user")
        async def link_command(interaction: discord.Interaction, username: str):
            cmd = registry.get("link")
            ctx = {
                "platform": "discord",
                "user": self._get_jupiter_user(interaction.user),
                "user_manager": self.user_data_manager,
                "interaction": interaction,
                "client": self
            }
            response = cmd.handler(ctx, username)
            await interaction.response.send_message(response)
        
    def setup_event_handlers(self):
        """Set up Discord event handlers"""
        
        @self.client.event
        async def on_ready():
            """Handle Discord client ready event"""
            self.logger.info(f"Logged in as {self.client.user}")
            self.is_running = True
            
            # Start initial status as Away
            await self.client.change_presence(status=discord.Status.idle)
            
            # Start periodic status update task
            self.client.loop.create_task(self._periodic_status_updates())
            
            # Clear and sync slash commands with Discord - GUILD ONLY
            try:
                # Log start of synchronization
                self.logger.info(f"Starting command synchronization for {len(self.client.guilds)} guilds")
                
                # Sync commands to each guild individually
                for guild in self.client.guilds:
                    try:
                        guild_id = guild.id
                        
                        # Clear existing commands to avoid duplicates
                        self.tree.clear_commands(guild=discord.Object(id=guild_id))
                        
                        # Sync commands to this guild
                        await self.tree.sync(guild=discord.Object(id=guild_id))
                        
                        self.logger.info(f"Synced slash commands to guild: {guild.name} (ID: {guild_id})")
                    except Exception as e:
                        self.logger.error(f"Error syncing commands to guild {guild.name}: {str(e)}")
                
                self.logger.info(f"Completed syncing slash commands to {len(self.client.guilds)} guilds")
            except Exception as e:
                self.logger.error(f"Error during command sync process: {str(e)}", exc_info=True)
            
            self.logger.info("Starting to send greetings to DM users")
            self.client.loop.create_task(self._send_dm_greeting())
        
        @self.client.event
        async def on_message(message):
            """Handle incoming Discord messages"""
            # Skip messages from self
            if message.author == self.client.user:
                return
            
            # Handle DM channels
            if isinstance(message.channel, discord.DMChannel):
                # Add to temporary active channels for status updates
                timeout = self.config.get("observation_timeout", 300)
                self.active_channels[message.channel.id] = time.time() + timeout
                
                # Save DM information to persistent storage
                self._save_dm_info(
                    message.channel.id,
                    message.author.name
                )
            
            # Check for commands
            if message.content.startswith('/'):
                await self.handle_command(message)
                return
                
            # Process regular message
            await self.process_message(message)
            
        @self.client.event
        async def on_error(event, *args, **kwargs):
            """Handle Discord client errors"""
            import traceback
            error = traceback.format_exc()
            self.logger.error(f"Discord error in {event}: {error}")
            
    async def handle_command(self, message):
        """Handle Discord commands using the common registry"""
        # Check if it's a command
        if not message.content.startswith('/'):
            return False
            
        # Use the adapter
        handled = await handle_discord_command(self, message)
        
        # If not handled by registry, process as a regular message
        if not handled:
            await self.process_message(message)
        
        return True
            
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
                # Use the async version instead
                response = await self._generate_response_async(jupiter_user, message.content)
                
                # Log Jupiter's response
                self.logger.info(f"[{channel_type}] Jupiter: {response[:100]}... ({channel_info})")
                
                # Send response
                if response:
                    await self._send_response(message.channel, response)
        
        except Exception as e:
            self.logger.error(f"Error processing Discord message: {str(e)}", exc_info=True)
    
    def _should_process_message(self, message) -> bool:
        """Determine if we should process this message"""
        # Always process DMs and make the channel active
        if isinstance(message.channel, discord.DMChannel):
            # Add DM channel to active channels for immediate processing
            timeout = self.config.get("observation_timeout", 300)
            self.active_channels[message.channel.id] = time.time() + timeout
            
            self.logger.info(f"Activated DM channel {message.channel.id} for {timeout} seconds")
            
            # Update Discord status to reflect active listening
            asyncio.create_task(self._update_discord_status())
            return True
            
        # Rest of the method remains unchanged
        # Check if in allowed servers/channels
        if not self._is_allowed(message):
            return False
        
        # Check if message is in an active channel
        channel_id = message.channel.id
        is_active_channel = (channel_id in self.active_channels and 
                            self.active_channels[channel_id] > time.time())
        
        # Check if message mentions Jupiter
        mentions_ai = self._mentions_ai(message.content)
        
        # If it mentions Jupiter, make this channel active
        if mentions_ai:
            timeout = self.config.get("observation_timeout", 300)  # Default 5 minutes
            self.active_channels[channel_id] = time.time() + timeout
            self.logger.info(f"Activated channel {channel_id} for {timeout} seconds")
            
            # Update Discord status to reflect active listening
            asyncio.create_task(self._update_discord_status())
        
        return is_active_channel or mentions_ai
    
    def _is_allowed(self, message) -> bool:
        """Check if message is from an allowed server and channel"""
        allowed_servers = self.config.get("allowed_servers", [])
        allowed_channels = self.config.get("allowed_channels", [])
        blacklisted_channels = self.config.get("blacklisted_channels", [])
        
        # Check blacklist first - these override any allows
        if message.channel.id in blacklisted_channels:
            return False
            
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
    
    def _mentions_ai(self, content) -> bool:
        """Check if message mentions the AI by its current name"""
        # Use name variations from current persona with fallbacks
        name_variations = self.persona.get("name_variations", 
                     self.config.get("name_variations", ["jupiter", "jup"]))
        
        # Also add the main name if not already in variations
        ai_name = self.persona.get("name", "Jupiter").lower()
        if ai_name not in name_variations:
            name_variations = [ai_name] + name_variations
            
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
    
    async def _generate_response_async(self, jupiter_user, message_text) -> str:
        """Generate a response from Jupiter's chat engine asynchronously"""
        loop = asyncio.get_event_loop()
        
        # Run the synchronous function in a thread pool
        return await loop.run_in_executor(
            None,  # Use default executor
            self._generate_response,  # The function to run
            jupiter_user, message_text  # Arguments to the function
        )

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
    
    async def _update_discord_status(self):
        """Update Discord status based on active channels"""
        # Check if any channels are active
        current_time = time.time()
        active_channels = {ch_id: expiry for ch_id, expiry in self.active_channels.items() 
                          if expiry > current_time}
        
        # Update the stored active channels (removes expired ones)
        self.active_channels = active_channels
        
        # Set status based on whether any channels are active
        if active_channels:
            await self.client.change_presence(status=discord.Status.online)
            self.logger.debug("Set Discord status to Online")
        else:
            await self.client.change_presence(status=discord.Status.idle)
            self.logger.debug("Set Discord status to Away")
    
    async def _periodic_status_updates(self):
        """Periodically update status to handle expired channels"""
        while self.is_running:
            await self._update_discord_status()
            await asyncio.sleep(60)  # Check every minute
    
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
        
        # Set status to invisible before closing
        if self.client.loop and self.client.is_ready():
            asyncio.run_coroutine_threadsafe(
                self.client.change_presence(status=discord.Status.invisible),
                self.client.loop
            )
        
        # Close Discord client
        asyncio.run_coroutine_threadsafe(
            self.client.close(), self.client.loop
        )

    async def _send_dm_greeting(self):
        """
        Send a personalized LLM-generated greeting to all DM channels
        
        Returns:
            tuple: (success_count, fail_count, error_details)
        """
        success_count = 0
        fail_count = 0
        error_details = []
        
        try:
            # Check if file exists
            dm_file_path = 'data/discord/dm_channels.json'
            if not os.path.exists(dm_file_path):
                self.logger.warning("DM channels file doesn't exist")
                return 0, 0, ["DM channels file doesn't exist"]
            
            # Load DM data
            with open(dm_file_path, 'r', encoding='utf-8') as f:
                dm_data = json.load(f)
                
            if not dm_data:
                self.logger.info("No DM channels found in storage")
                return 0, 0, ["No DM channels found in storage"]
            
            # Send greeting to each DM channel
            for channel_id_str, data in dm_data.items():
                try:
                    # Convert string ID to integer
                    channel_id = int(channel_id_str)
                    username = data.get('username', 'User')
                    
                    # Try to fetch the channel
                    channel = self.client.get_channel(channel_id)
                    
                    # If channel not found, try to fetch as private channel
                    if channel is None:
                        try:
                            channel = await self.client.fetch_channel(channel_id)
                        except Exception as e:
                            error_msg = f"Could not fetch channel {channel_id}: {str(e)}"
                            self.logger.warning(error_msg)
                            error_details.append(error_msg)
                            fail_count += 1
                            continue
                    
                    # Create a temporary user object for the LLM
                    temp_user = self._get_jupiter_user(await self.client.fetch_user(channel.recipient.id))
                    
                    # Generate personalized greeting through the LLM
                    greeting_prompt = f"You have come back online. Please greet {username}"
                    greeting = await self._generate_response_async(temp_user, greeting_prompt)
                    
                    # Send the greeting
                    await channel.send(greeting)
                    success_count += 1
                    self.logger.info(f"Sent greeting to {username} in DM channel {channel_id}: {greeting[:50]}...")
                    
                except Exception as e:
                    error_msg = f"Error sending greeting to {channel_id_str} ({data.get('username', 'Unknown')}): {str(e)}"
                    self.logger.error(error_msg)
                    error_details.append(error_msg)
                    fail_count += 1
            
            return success_count, fail_count, error_details
            
        except Exception as e:
            error_msg = f"Error in _send_dm_greeting: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return 0, 0, [error_msg]

    def _save_dm_info(self, channel_id, username):
        """Save DM channel information to persistent storage"""
        try:
            # Ensure directory exists
            os.makedirs('data/discord', exist_ok=True)
            
            # Load existing data if available
            dm_file_path = 'data/discord/dm_channels.json'
            dm_data = {}
            
            if os.path.exists(dm_file_path):
                try:
                    with open(dm_file_path, 'r', encoding='utf-8') as f:
                        dm_data = json.load(f)
                except json.JSONDecodeError:
                    self.logger.warning(f"Could not parse DM channels file, creating new one")
            
            # Update with new data
            channel_id_str = str(channel_id)  # Convert to string for JSON keys
            dm_data[channel_id_str] = {
                'username': username,
                'last_active': time.time()
            }
            
            # Save updated data
            with open(dm_file_path, 'w', encoding='utf-8') as f:
                json.dump(dm_data, f, indent=2)
                
            self.logger.debug(f"Saved DM info for channel {channel_id} ({username})")
            
        except Exception as e:
            self.logger.error(f"Error saving DM info: {str(e)}", exc_info=True)
