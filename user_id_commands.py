import time
import logging

logger = logging.getLogger("jupiter.commands")

class UserIDCommands:
    """Command handlers for user ID functionality"""
    
    def __init__(self, chat_engine):
        """Initialize with reference to chat engine"""
        self.chat_engine = chat_engine
    
    def handle_id_command(self, platform):
        """Handle /id command - show user ID information"""
        user_data_manager = self.chat_engine.user_data_manager
        current_user = user_data_manager.current_user
        
        if not current_user or 'user_id' not in current_user:
            return "Your user ID information is not available."
        
        user_id = current_user.get('user_id')
        name = current_user.get('name', 'Unknown')
        platforms = current_user.get('platforms', {})
        created_timestamp = current_user.get('created_at', 0)
        
        # Format platform information
        platform_list = [p for p, enabled in platforms.items() if enabled]
        platform_str = ", ".join(platform_list) if platform_list else "none"
        
        # Format creation date
        created_date = "unknown"
        if created_timestamp > 0:
            try:
                created_date = time.strftime("%Y-%m-%d", time.localtime(created_timestamp))
            except:
                pass
        
        # Build response
        response = f"""
Your Jupiter ID Information:
---------------------------
User ID: {user_id}
Name: {name}
Platforms: {platform_str}
Created: {created_date}

This ID lets Jupiter recognize you across different platforms.
"""
        
        return response
    
    def handle_link_command(self, arguments, current_platform):
        """Handle /link command - link platform identities"""
        if not arguments:
            return """
Usage: /link [platform] [username]
Example: /link discord YourDiscordName
         /link gui YourGUIName

This links your current identity with another platform identity.
"""
        
        user_data_manager = self.chat_engine.user_data_manager
        current_user = user_data_manager.current_user
        
        if not current_user or 'user_id' not in current_user:
            return "You must have a valid user profile to link identities."
        
        # Parse arguments
        args = arguments.strip().split()
        if len(args) < 2:
            return "Please specify both platform and username. Example: /link discord YourDiscordName"
        
        target_platform = args[0].lower()
        target_name = " ".join(args[1:])
        
        # Validate platform
        if target_platform not in ["gui", "discord", "terminal"]:
            return f"Unknown platform '{target_platform}'. Supported platforms: gui, discord, terminal"
        
        # Get current user info
        source_platform = current_platform
        source_name = current_user.get('name', 'Unknown')
        
        # Perform linking
        success, message = user_data_manager.link_platform_identities(
            source_platform, source_name, 
            target_platform, target_name
        )
        
        if success:
            # If successful, reload current user data
            new_user, _ = user_data_manager.get_user_by_name(source_name, source_platform)
            if new_user:
                user_data_manager.set_current_user(new_user)
            return f"Success! {message}"
        else:
            return f"Linking failed: {message}"
    
    def handle_cleanup_command(self, arguments, is_admin=False):
        """Handle /cleanup command - clean up old user profiles"""
        if not is_admin:
            return "This command is only available to administrators."
        
        user_data_manager = self.chat_engine.user_data_manager
        
        # Parse arguments
        max_age_days = 180  # Default
        if arguments:
            try:
                max_age_days = int(arguments.strip())
                if max_age_days < 1:
                    return "Age must be at least 1 day."
            except ValueError:
                return "Please specify a valid number of days. Example: /cleanup 180"
        
        # Perform cleanup
        removed_count = user_data_manager.cleanup_old_users(max_age_days)
        
        if removed_count > 0:
            return f"Cleaned up {removed_count} user profiles older than {max_age_days} days."
        else:
            return f"No user profiles older than {max_age_days} days found."


# Extension to the chat engine's handle_user_commands method
def handle_id_commands(chat_engine, user_input):
    """Handle ID-related commands for the chat engine"""
    # Create command handler if needed
    if not hasattr(chat_engine, 'id_commands'):
        chat_engine.id_commands = UserIDCommands(chat_engine)
    
    # Handle /id command
    if user_input.strip().lower() == '/id':
        platform = "gui"  # Default
        if hasattr(chat_engine, 'current_platform'):
            platform = chat_engine.current_platform
        return chat_engine.id_commands.handle_id_command(platform)
    
    # Handle /link command
    if user_input.lower().startswith('/link'):
        platform = "gui"  # Default
        if hasattr(chat_engine, 'current_platform'):
            platform = chat_engine.current_platform
        arguments = user_input[5:].strip()
        return chat_engine.id_commands.handle_link_command(arguments, platform)
    
    # Handle /cleanup command
    if user_input.lower().startswith('/cleanup'):
        arguments = user_input[8:].strip()
        # Check if admin (you'll need to implement this check)
        is_admin = getattr(chat_engine, 'is_admin', False)
        return chat_engine.id_commands.handle_cleanup_command(arguments, is_admin)
    
    # Not an ID command
    return None
