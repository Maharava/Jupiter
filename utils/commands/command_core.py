from .registry import Command, registry
import inspect
import logging
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
    """Link two user accounts together"""
    user_manager = ctx.get("user_manager")
    current_user = ctx.get("user")
    platform = ctx.get("platform", "unknown")
    
    # Setup logging
    logger = logging.getLogger("jupiter.commands")
    logger.info(f"Link command called from platform: {platform}")
    
    if not args or not args.strip():
        return "Please provide a username to link with. Usage: `/link [username]`"
    
    target_username = args.strip()
    logger.info(f"Looking for target user: '{target_username}'")
    
    # Check if current user exists
    if not current_user or 'user_id' not in current_user:
        logger.warning("Current user not registered")
        return "You need to be registered first."
    
    logger.info(f"Current user: {current_user.get('name')} (ID: {current_user.get('user_id')})")
    
    # Get target user - search across all platforms
    target_user = user_manager.get_user(target_username, platform="all")
    
    logger.info(f"Target user found: {target_user is not None}")
    if target_user:
        logger.info(f"Target user: {target_user.get('name')} (ID: {target_user.get('user_id')})")
    
    if not target_user or 'user_id' not in target_user:
        return f"User '{target_username}' not found. Make sure the username is correct."
    
    # Don't link to self
    if current_user['user_id'] == target_user['user_id']:
        return "You can't link your account to itself."
    
    # Link accounts
    success = user_manager.link_accounts(current_user['user_id'], target_user['user_id'])
    
    if success:
        return f"Successfully linked your account with '{target_user.get('name')}' (ID: {target_user.get('user_id')}). All your data has been merged."
    else:
        return f"Failed to link accounts. Please try again or contact an administrator."

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

def name_command(ctx, args=None):
    """Change your display name"""
    user_manager = ctx.get("user_manager")
    user = ctx.get("user")
    
    if not args or not args.strip():
        return "Please provide a new name. Usage: `/name [new name]`"
    
    new_name = args.strip()
    
    # Check if user exists
    if not user or 'user_id' not in user:
        return "You need to be registered first."
    
    # Update the name
    user_id = user['user_id']
    old_name = user.get('name')
    user['name'] = new_name
    
    # Save the change
    success = user_manager.update_user(user_id, user)
    
    if success:
        return f"Your name has been updated to **{new_name}**"
    else:
        return "There was an error updating your name."

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
    description="Link your account with another user's account",
    usage="/link [username]",
    platforms=["discord", "terminal", "gui"]
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

def prompt_command(ctx, args=None):
    """Show the current system prompt that guides Jupiter's behavior"""
    import os
    
    # Try to get the path to the system prompt
    prompt_path = None
    
    # Method 1: Try to get from conversation_manager config
    conversation_manager = ctx.get("conversation_manager")
    if conversation_manager and hasattr(conversation_manager, "config"):
        config = conversation_manager.config
        if isinstance(config, dict) and 'paths' in config and 'prompt_folder' in config['paths']:
            prompt_path = os.path.join(config['paths']['prompt_folder'], "system_prompt.txt")
    
    # Method 2: Try to get from client config
    if not prompt_path or not os.path.exists(prompt_path):
        client = ctx.get("client")
        if client and hasattr(client, "config"):
            config = client.config
            if hasattr(config, "paths") and hasattr(config.paths, "prompt_folder"):
                prompt_path = os.path.join(config.paths.prompt_folder, "system_prompt.txt")
            elif isinstance(config, dict) and 'paths' in config and 'prompt_folder' in config['paths']:
                prompt_path = os.path.join(config['paths']['prompt_folder'], "system_prompt.txt")
    
    # Method 3: Try some common paths
    if not prompt_path or not os.path.exists(prompt_path):
        possible_paths = [
            "prompts/system_prompt.txt",
            "data/prompts/system_prompt.txt",
            "config/prompts/system_prompt.txt",
            os.path.join("data", "prompts", "system_prompt.txt"),
            os.path.join("config", "prompts", "system_prompt.txt")
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                prompt_path = path
                break
    
    # Failed to find the path
    if not prompt_path or not os.path.exists(prompt_path):
        return "Could not locate system prompt file."
    
    # Read the system prompt
    try:
        with open(prompt_path, 'r', encoding='utf-8') as f:
            system_prompt = f.read()
    except Exception as e:
        return f"Error reading system prompt: {e}"
    
    # Format the response
    response = "## Current System Prompt\n\n```\n"
    response += system_prompt
    response += "\n```\n\nThis is the system prompt that guides my behavior and capabilities."
    
    return response

# Register the prompt command
registry.register(Command(
    name="prompt",
    handler=prompt_command,
    description="Display the current system prompt",
    usage="/prompt",
    platforms=["discord", "terminal", "gui"]  # Available on all platforms
))
