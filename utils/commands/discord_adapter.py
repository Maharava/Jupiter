from .registry import registry
import logging
import asyncio

# Add logger
logger = logging.getLogger("jupiter.commands")

async def handle_discord_command(client, message):
    """Handle a Discord command using the common registry"""
    try:
        # Parse command name from message
        parts = message.content.split(None, 1)
        command_name = parts[0][1:].lower()  # Remove the slash
        args = parts[1] if len(parts) > 1 else ""
        
        # Look up command
        command = registry.get(command_name)
        if not command or "discord" not in command.platforms:
            # Unknown command or not available on Discord
            logger.info(f"Unknown command or not available on Discord: {command_name}")
            return False
            
        # Build context with Discord-specific info
        ctx = {
            "platform": "discord",
            "user": client._get_jupiter_user(message.author),
            "user_manager": client.user_data_manager,
            "message": message,
            "client": client,
            "ui": None  # Discord has no UI object
        }
        
        # Execute command in a thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, command.handler, ctx, args)
        
        # Send response
        if response:
            await message.channel.send(response)
        
        return True
    except Exception as e:
        logger.error(f"Error handling command: {e}", exc_info=True)
        await message.channel.send("I encountered an error processing that command.")
        return True