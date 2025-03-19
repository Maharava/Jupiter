class MockDiscordMessage:
    """Mock Discord message object"""
    
    def __init__(self, content, author=None, channel=None, guild=None):
        """Initialize with message content and metadata"""
        self.content = content
        self.author = author or MockDiscordUser()
        self.channel = channel or MockDiscordChannel()
        self.guild = guild
        self.created_at = None  # Could add datetime here if needed
        self.reactions = []
    
    async def add_reaction(self, emoji):
        """Mock adding a reaction to the message"""
        self.reactions.append(emoji)
    
    async def reply(self, content=None, **kwargs):
        """Mock replying to a message"""
        new_message = MockDiscordMessage(content)
        self.channel.messages.append(new_message)
        return new_message


class MockDiscordUser:
    """Mock Discord user object"""
    
    def __init__(self, id="123456789", name="TestUser", discriminator="1234"):
        """Initialize with user data"""
        self.id = id
        self.name = name
        self.discriminator = discriminator
        self.display_name = name
        self.bot = False
    
    def __eq__(self, other):
        """Compare users by ID"""
        if isinstance(other, MockDiscordUser):
            return self.id == other.id
        return False


class MockDiscordChannel:
    """Mock Discord channel object"""
    
    def __init__(self, id="987654321", name="test-channel"):
        """Initialize with channel data"""
        self.id = id
        self.name = name
        self.messages = []
        self.typing_active = False
    
    async def send(self, content=None, **kwargs):
        """Mock sending a message to the channel"""
        new_message = MockDiscordMessage(content)
        self.messages.append(new_message)
        return new_message
    
    async def typing(self):
        """Mock typing indicator context manager"""
        class MockTypingContextManager:
            def __init__(self, channel):
                self.channel = channel
            
            async def __aenter__(self):
                self.channel.typing_active = True
                return self.channel
            
            async def __aexit__(self, exc_type, exc_val, exc_tb):
                self.channel.typing_active = False
        
        return MockTypingContextManager(self)


class MockDiscordClient:
    """Mock Discord client for testing"""
    
    def __init__(self):
        """Initialize the mock Discord client"""
        self.user = MockDiscordUser(name="JupiterBot", bot=True)
        self.users = {}
        self.channels = {}
        self.guilds = {}
        self.messages = []
        self.callbacks = {
            "on_ready": [],
            "on_message": [],
            "on_error": []
        }
        self.is_ready = False
        self.is_running = False
        self.loop = None
    
    def add_callback(self, event_name, callback):
        """Register a callback for an event"""
        if event_name in self.callbacks:
            self.callbacks[event_name].append(callback)
    
    async def trigger_event(self, event_name, *args, **kwargs):
        """Trigger callbacks for an event"""
        if event_name in self.callbacks:
            for callback in self.callbacks[event_name]:
                await callback(*args, **kwargs)
    
    def add_user(self, user_id, name, discriminator="1234"):
        """Add a test user"""
        user = MockDiscordUser(id=user_id, name=name, discriminator=discriminator)
        self.users[user_id] = user
        return user
    
    def add_channel(self, channel_id, name):
        """Add a test channel"""
        channel = MockDiscordChannel(id=channel_id, name=name)
        self.channels[channel_id] = channel
        return channel
    
    async def process_message(self, content, user_id=None, channel_id=None):
        """Process a message as if it was received from Discord"""
        # Use default test IDs if not provided
        user_id = user_id or "123456789"
        channel_id = channel_id or "987654321"
        
        # Get or create user and channel
        user = self.users.get(user_id) or self.add_user(user_id, f"User{user_id}")
        channel = self.channels.get(channel_id) or self.add_channel(channel_id, f"channel-{channel_id}")
        
        # Create the message
        message = MockDiscordMessage(content, author=user, channel=channel)
        self.messages.append(message)
        
        # Trigger on_message callbacks
        await self.trigger_event("on_message", message)
        
        return message
    
    def run(self, token):
        """Mock starting the Discord bot"""
        self.is_running = True
        # In a real implementation, we would create an event loop here
    
    def close(self):
        """Mock stopping the Discord bot"""
        self.is_running = False


class MockDiscordModule:
    """Mock for the DiscordModule class"""
    
    def __init__(self, chat_engine=None, user_model=None, logger=None, config=None):
        """Initialize with dependencies"""
        self.chat_engine = chat_engine
        self.user_model = user_model
        self.logger = logger
        self.config = config or {"token": "mock_token"}
        self.client = MockDiscordClient()
        self.is_running = False
    
    def start(self):
        """Start the Discord bot"""
        self.is_running = True
        self.client.is_running = True
    
    def stop(self):
        """Stop the Discord bot"""
        self.is_running = False
        self.client.is_running = False
    
    async def process_test_message(self, content, user_id=None, channel_id=None):
        """Process a test message through the Discord bot"""
        if not self.is_running:
            self.start()
        
        return await self.client.process_message(content, user_id, channel_id)


# Exports
__all__ = [
    'MockDiscordMessage', 
    'MockDiscordUser', 
    'MockDiscordChannel', 
    'MockDiscordClient',
    'MockDiscordModule'
]
