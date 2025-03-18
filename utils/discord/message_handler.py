import asyncio
import re
import discord

class MessageHandler:
    """Processes incoming Discord messages and determines Jupiter's responses"""
    
     def __init__(self, chat_engine, user_mapper, config, client=None):
        self.chat_engine = chat_engine
        self.user_mapper = user_mapper
        self.config = config
        self.client = client
        
        # Track active conversations per channel
        self.active_channels = {}
        # Track message history per channel
        self.channel_history = {}
        
        # Compile regex for name mentions
        self.name_pattern = re.compile(
            fr'\b({"|".join(re.escape(name) for name in config["name_variations"])})\b', 
            re.IGNORECASE
        )
    
    async def handle_message(self, message):
        """Process incoming Discord message and determine if Jupiter should respond"""
        # Skip if message is from a disallowed server or channel
        if not self._is_allowed(message):
            return
            
        # Get or create Jupiter user for this Discord user
        jupiter_user = self.user_mapper.get_jupiter_user(message.author)
        
        # Add message to channel history
        self._add_to_history(message)
        
        # Determine if Jupiter should respond
        should_respond = self._should_respond(message)
        
        if should_respond:
            # Mark channel as active
            self.active_channels[message.channel.id] = {
                'timestamp': asyncio.get_event_loop().time(),
                'timeout': self.config["observation_timeout"]
            }
            
            # Send typing indicator
            async with message.channel.typing():
                # Format message for Jupiter
                user_input = message.content
                
                # Generate response through Jupiter's chat engine
                response = await self._get_jupiter_response(jupiter_user, user_input)
                
                # CHANGED: Use _send_response method instead of direct send
                # This handles multi-chunk messages properly
                await self._send_response(message.channel, response)
                # OLD: await message.channel.send(response)
        }
    
    def _is_allowed(self, message):
        """Check if message is from an allowed server and channel"""
        allowed_servers = self.config["allowed_servers"]
        allowed_channels = self.config["allowed_channels"]
        
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
    
    def _add_to_history(self, message):
        """Add message to channel history"""
        channel_id = message.channel.id
        
        if channel_id not in self.channel_history:
            self.channel_history[channel_id] = []
            
        # Add message to history
        self.channel_history[channel_id].append({
            'author': message.author.name,
            'content': message.content,
            'timestamp': message.created_at
        })
        
        # Trim history if needed
        max_history = self.config["max_history_per_channel"]
        if len(self.channel_history[channel_id]) > max_history:
            self.channel_history[channel_id] = self.channel_history[channel_id][-max_history:]
    
    def _should_respond(self, message):
        """Determine if Jupiter should respond to this message"""
        # Always respond in DMs
        if isinstance(message.channel, discord.DMChannel):
            return True
            
        # Check if Jupiter was directly mentioned
        if self.name_pattern.search(message.content):
            return True
            
        # Check if this is an active channel
        channel_id = message.channel.id
        if channel_id in self.active_channels:
            # Check if the timeout has expired
            current_time = asyncio.get_event_loop().time()
            active_info = self.active_channels[channel_id]
            
            if current_time - active_info['timestamp'] < active_info['timeout']:
                # Channel is still active, decide based on context
                return True
            else:
                # Timeout expired, remove from active channels
                del self.active_channels[channel_id]
                
        return False
    
    async def _get_jupiter_response(self, jupiter_user, user_input):
        """Get response from Jupiter in a non-blocking way"""
        loop = asyncio.get_event_loop()
        
        def _call_jupiter():
            # Use the client directly, avoiding circular imports
            return self.client.generate_response(jupiter_user, user_input)
        
        # Run Jupiter's processing in a thread pool
        response = await loop.run_in_executor(None, _call_jupiter)
        return response
        
    async def _send_response(self, channel, response):
        """Send response, handling multiple chunks if needed"""
        if isinstance(response, list):
            # Send each chunk as a separate message
            for chunk in response:
                await channel.send(chunk)
                # Small delay between chunks
                await asyncio.sleep(1)
        else:
            # Send as a single message
            await channel.send(response)