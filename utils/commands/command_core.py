from .registry import Command, registry
import inspect
# Add Discord import
import discord

def id_command(ctx, args=None):
    """Show user ID information"""
    # Context contains platform-specific info
    platform = ctx.get("platform")
    user = ctx.get("user")
    ui = ctx.get("ui")
    user_manager = ctx.get("user_manager")
    
    # Implementation that works across platforms
    if not user or 'user_id' not in user:
        return "You don't have a Jupiter ID yet."
    
    user_id = user.get('user_id', 'Unknown')
    name = user.get('name', 'User')
    platforms = user.get('platforms', {})
    platform_list = [p for p, enabled in platforms.items() if enabled]
    
    return f"""
**Your Jupiter ID Information**
ID: {user_id}
Name: {name}
Platforms: {', '.join(platform_list) if platform_list else platform + " only"}
"""

def link_command(ctx, args=None):
    """Link user identity across platforms"""
    # Get components from context
    user_manager = ctx.get("user_manager")
    user = ctx.get("user")
    platform = ctx.get("platform")
    
    if not args:
        return ("Usage: `/link [platform] [username]`\n"
                "Example: `/link gui JohnDoe`\n\n"
                "Available platforms: gui, terminal")
    
    # Parse arguments - similar to your existing implementation
    parts = args.split(None, 1)
    if len(parts) < 2:
        return "Please specify both platform and username."
        
    target_platform, target_name = parts
    
    # Validate platform
    if target_platform.lower() not in ["gui", "terminal"]:
        return f"Unknown platform '{target_platform}'. Supported platforms: gui, terminal"
        
    # Attempt linking
    try:
        source_platform = platform
        source_name = user.get('name')
        
        success, result_message = user_manager.link_platform_identities(
            source_platform, source_name,
            target_platform.lower(), target_name
        )
        
        if success:
            return f"✅ Success! {result_message}"
        else:
            return f"❌ Linking failed: {result_message}"
            
    except Exception as e:
        return "An error occurred while linking identities. Please try again later."

def help_command(ctx, args=None):
    """Show help information"""
    platform = ctx.get("platform")
    # Platform-specific help formatting
    
    commands = registry.get_for_platform(platform)
    help_text = f"**Jupiter Commands for {platform.capitalize()}**\n\n"
    
    for cmd in commands:
        help_text += f"`{cmd.usage}` - {cmd.description}\n"
    
    # Add platform-specific instructions
    if platform == "discord":
        help_text += "\nYou can chat with me in DMs anytime. In channels, just mention \"Jupiter\" and I'll respond!"
    
    return help_text

def deaf_command(ctx, args=None):
    """Blacklist the current channel from Jupiter's monitoring"""
    platform = ctx.get("platform")
    client = ctx.get("client")
    
    # This command only works in channels (not DMs)
    if platform != "discord":
        return "This command is only available on Discord."
        
    # Get the message or interaction
    if "message" in ctx:
        message = ctx.get("message")
        channel_id = message.channel.id
        channel_name = message.channel.name if hasattr(message.channel, "name") else "Direct Message"
        guild_name = message.guild.name if message.guild else "DM"
    elif "interaction" in ctx:
        interaction = ctx.get("interaction") 
        channel_id = interaction.channel_id
        channel_name = interaction.channel.name if hasattr(interaction.channel, "name") else "Direct Message"
        guild_name = interaction.guild.name if interaction.guild else "DM"
    else:
        return "Cannot determine the current channel."
    
    # Don't blacklist DMs - FIXED THIS LINE
    if guild_name == "DM" or isinstance(message.channel if "message" in ctx else interaction.channel, discord.DMChannel):
        return "I cannot ignore direct messages, only server channels."
    
    # Safely access config - works with both dict and custom Config objects
    blacklisted_channels = []
    try:
        # Try to get existing blacklist
        if hasattr(client.config, "get"):
            # If it's a dict-like object with get method
            blacklisted_channels = client.config.get("blacklisted_channels", [])
        else:
            # If it's a custom object, try direct attribute access
            blacklisted_channels = getattr(client.config, "blacklisted_channels", [])
    except Exception:
        # If all else fails, start with empty list
        blacklisted_channels = []
    
    # Check if already blacklisted
    if channel_id in blacklisted_channels:
        return f"I'm already ignoring the #{channel_name} channel."
    
    # Add to blacklist - safely
    try:
        if hasattr(client.config, "get"):
            if "blacklisted_channels" not in client.config:
                client.config["blacklisted_channels"] = []
            client.config["blacklisted_channels"].append(channel_id)
        else:
            if not hasattr(client.config, "blacklisted_channels"):
                setattr(client.config, "blacklisted_channels", [])
            client.config.blacklisted_channels.append(channel_id)
    except Exception as e:
        return f"Error updating blacklist: {str(e)}"
    
    # Log the change
    client.logger.info(f"Added channel {channel_id} ({guild_name}/{channel_name}) to blacklist")
    
    # Save config to disk for persistence (non-blocking)
    if hasattr(client, "_save_config"):
        # For thread-safety, use regular save (it's now called from a thread pool)
        client._save_config()
    
    return f"I'll no longer respond to messages in #{channel_name} unless explicitly mentioned."

def listen_command(ctx, args=None):
    """Remove a channel from Jupiter's blacklist"""
    platform = ctx.get("platform")
    client = ctx.get("client")
    
    # This command only works in channels (not DMs)
    if platform != "discord":
        return "This command is only available on Discord."
        
    # Get the message or interaction
    if "message" in ctx:
        message = ctx.get("message")
        channel_id = message.channel.id
        channel_name = message.channel.name if hasattr(message.channel, "name") else "Direct Message"
        guild_name = message.guild.name if message.guild else "DM"
    elif "interaction" in ctx:
        interaction = ctx.get("interaction") 
        channel_id = interaction.channel_id
        channel_name = interaction.channel.name if hasattr(interaction.channel, "name") else "Direct Message"
        guild_name = interaction.guild.name if interaction.guild else "DM"
    else:
        return "Cannot determine the current channel."
    
    # Don't run in DMs - add this check for consistency
    if guild_name == "DM" or isinstance(message.channel if "message" in ctx else interaction.channel, discord.DMChannel):
        return "This command can only be used in server channels, not direct messages."
    
    # Safely access config - works with both dict and custom Config objects
    blacklisted_channels = []
    try:
        # Try to get existing blacklist
        if hasattr(client.config, "get"):
            # If it's a dict-like object with get method
            blacklisted_channels = client.config.get("blacklisted_channels", [])
        else:
            # If it's a custom object, try direct attribute access
            blacklisted_channels = getattr(client.config, "blacklisted_channels", [])
    except Exception:
        # If all else fails, assume empty list (nothing blacklisted)
        blacklisted_channels = []
    
    # Check if not in blacklist
    if channel_id not in blacklisted_channels:
        return f"I'm already listening to the #{channel_name} channel."
    
    # Remove from blacklist - safely
    try:
        if hasattr(client.config, "get"):
            client.config["blacklisted_channels"].remove(channel_id)
        else:
            client.config.blacklisted_channels.remove(channel_id)
    except Exception as e:
        return f"Error updating blacklist: {str(e)}"
    
    # Log the change
    client.logger.info(f"Removed channel {channel_id} ({channel_name}) from blacklist")
    
    # Save config to disk for persistence (non-blocking)
    if hasattr(client, "_save_config"):
        # For thread-safety, use regular save (it's now called from a thread pool)
        client._save_config()
    
    return f"I'll start monitoring #{channel_name} again."

def persona_command(ctx, args=None):
    """Change or display the current AI persona"""
    client = ctx.get("client")
    config = client.config
    
    # Get available personas
    ai_config = config.get("ai", {})
    personas = ai_config.get("personas", {})
    current = ai_config.get("current_persona", "jupiter")
    
    # If no args, show current and available personas
    if not args:
        response = f"Current persona: **{current}**\n\nAvailable personas:\n"
        for key, persona in personas.items():
            response += f"- **{key}**: {persona['name']} ({persona['color']})\n"
        return response
    
    # Try to change to requested persona
    requested = args.strip().lower()
    if requested in personas:
        # Update current persona
        if hasattr(config, "get"):
            config["ai"]["current_persona"] = requested
        else:
            config.ai.current_persona = requested
            
        # Save changes
        if hasattr(client, "_save_config"):
            client._save_config()
            
        new_name = personas[requested]["name"]
        return f"Changed persona to **{requested}** ({new_name}). This will take full effect on restart."
    else:
        return f"Unknown persona '{requested}'. Use '/persona' to see available options."

def todo_command(ctx, args=None):
    """Add an item to Jupiter's todo list"""
    import os
    import datetime
    
    # Get user info from context
    user = ctx.get("user", {})
    platform = ctx.get("platform", "unknown")
    user_name = user.get("name", "Unknown User")
    
    # Validate arguments
    if not args or not args.strip():
        return "Please provide a todo item. Usage: `/todo [description of task]`"
    
    todo_item = args.strip()
    
    # Create data directory if it doesn't exist
    os.makedirs("data", exist_ok=True)
    
    # Get timestamp
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Format the todo entry
    entry = f"[{timestamp}] [{platform}] [{user_name}] {todo_item}\n"
    
    try:
        # Append to todo file
        with open("data/todo.txt", "a", encoding="utf-8") as f:
            f.write(entry)
        
        return f"✅ Added to my todo list: '{todo_item}'"
    except Exception as e:
        return f"❌ Error saving todo item: {str(e)}"

def model_command(ctx, args=None):
    """Show information about the connected LLM model"""
    # Get LLM client from context
    llm_client = ctx.get("llm_client")
    
    if not llm_client:
        return "Error: Could not access LLM client information."
    
    # Get model information
    model_info = {
        "model": llm_client.default_model,
        "api_url": llm_client.api_url,
        "test_mode": llm_client.test_mode
    }
    
    # Format the response
    if model_info["test_mode"]:
        response = f"""
**LLM Connection: Test Mode**
• Model: {model_info["model"]} (simulated)
• API URL: {model_info["api_url"]} (not connected)
• Status: Operating in test mode with simulated responses
"""
    else:
        response = f"""
**LLM Connection: Active**
• Model: {model_info["model"]}
• API URL: {model_info["api_url"]}
• Status: Connected and operational
"""
    
    return response

def _handle_help_command(self, args):
    """Handle /help command"""
    help_text = "# Available Commands\n\n"
    
    help_text += "## General Commands\n"
    help_text += "- `/help` - Show this help message\n"
    help_text += "- `/name [new name]` - Change your name\n"
    help_text += "- `/memory` - Show what Jupiter remembers about you\n"
    
    help_text += "\n## Conversation Management\n"
    help_text += "- `/history [limit]` - Show your recent conversations\n"
    help_text += "- `/history with [username]` - Show conversations with a specific user\n"
    help_text += "- `/conversation [ID]` - View a specific conversation\n"
    help_text += "- `/conversation current` - View the current conversation\n"
    help_text += "- `/search [query]` - Search your conversations\n"
    
    help_text += "\n## Voice Commands\n"
    help_text += "- `/voice on|off` - Enable or disable voice recognition\n"
    
    if self.voice_manager and self.voice_manager.detector_available:
        help_text += "- `/debug voice` - Show voice recognition debug information\n"
    
    return help_text

# Register the command
registry.register(Command(
    name="todo",
    handler=todo_command,
    description="Add an item to Jupiter's todo list",
    usage="/todo [description of task]",
    platforms=["discord", "terminal", "gui"]  # Available on all platforms
))

# Register the command
registry.register(Command(
    name="persona",
    handler=persona_command,
    description="Change or view AI persona",
    usage="/persona [name]",
    platforms=["discord", "terminal", "gui"]
))

# Register the command
registry.register(Command(
    name="model",
    handler=model_command,
    description="Show information about the connected LLM model",
    usage="/model",
    platforms=["discord", "terminal", "gui"]  # Available on all platforms
))

# Register commands
registry.register(Command(
    name="id",
    handler=id_command,
    description="Display your Jupiter ID information"
))

registry.register(Command(
    name="link",
    handler=link_command,
    description="Link your identity with another platform",
    usage="/link [platform] [username]"
))

registry.register(Command(
    name="help",
    handler=help_command,
    description="Show available commands"
))

registry.register(Command(
    name="deaf",
    handler=deaf_command,
    description="Make Jupiter stop listening in the current channel",
    platforms=["discord"]  # Only available on Discord
))

registry.register(Command(
    name="listen",
    handler=listen_command,
    description="Make Jupiter start listening in the current channel again",
    platforms=["discord"]  # Only available on Discord
))

# Add other common commands...