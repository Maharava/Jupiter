import discord
import logging
from discord import app_commands
from discord.ext import commands

logger = logging.getLogger("jupiter.discord.commands")

class IDCommands(commands.Cog):
    """Discord commands for Jupiter ID system"""
    
    def __init__(self, bot, user_mapper):
        self.bot = bot
        self.user_mapper = user_mapper
        
    @app_commands.command(name="id", description="Show your Jupiter ID information")
    async def id_command(self, interaction: discord.Interaction):
        """Command to show user ID information"""
        try:
            # Get Jupiter user data
            jupiter_user = self.user_mapper.get_user_id_info(interaction.user)
            
            if not jupiter_user or 'user_id' not in jupiter_user:
                await interaction.response.send_message(
                    "You don't have a Jupiter ID yet. Try chatting with me first!",
                    ephemeral=True
                )
                return
            
            # Format user information
            user_id = jupiter_user.get('user_id', 'Unknown')
            name = jupiter_user.get('name', interaction.user.name)
            platforms = jupiter_user.get('platforms', {})
            created_at = jupiter_user.get('created_at', 0)
            last_seen = jupiter_user.get('last_seen', 0)
            
            # Format creation date
            import time
            created_date = "unknown"
            if created_at > 0:
                created_date = time.strftime("%Y-%m-%d", time.localtime(created_at))
            
            # Format platforms
            platform_list = [p for p, enabled in platforms.items() if enabled]
            platform_str = ", ".join(platform_list) if platform_list else "discord only"
            
            # Create embed
            embed = discord.Embed(
                title="Your Jupiter ID Information",
                description="This ID lets Jupiter recognize you across different platforms.",
                color=0x3498db
            )
            
            embed.add_field(name="User ID", value=f"`{user_id}`", inline=False)
            embed.add_field(name="Name", value=name, inline=True)
            embed.add_field(name="Platforms", value=platform_str, inline=True)
            embed.add_field(name="Created", value=created_date, inline=True)
            
            # Add footer
            embed.set_footer(text="Use /link to connect with other platforms")
            
            # Send as ephemeral message (only visible to the user)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error processing ID command: {e}")
            await interaction.response.send_message(
                "Sorry, something went wrong processing your command.",
                ephemeral=True
            )
    
    @app_commands.command(name="link", description="Link your Discord identity with another Jupiter platform")
    @app_commands.describe(
        platform="The platform to link with (gui or terminal)",
        username="Your username on that platform"
    )
    async def link_command(self, interaction: discord.Interaction, platform: str, username: str):
        """Command to link identities across platforms"""
        try:
            # Validate platform
            if platform.lower() not in ["gui", "terminal"]:
                await interaction.response.send_message(
                    f"Unknown platform '{platform}'. Supported platforms: gui, terminal",
                    ephemeral=True
                )
                return
            
            # Get Discord user data
            discord_user = self.user_mapper.get_user_id_info(interaction.user)
            
            if not discord_user or 'user_id' not in discord_user:
                await interaction.response.send_message(
                    "You don't have a Jupiter ID yet. Try chatting with me first!",
                    ephemeral=True
                )
                return
            
            # Attempt linking
            user_data_manager = self.user_mapper.user_data_manager
            source_platform = "discord"
            source_name = interaction.user.name
            target_platform = platform.lower()
            target_name = username
            
            success, message = user_data_manager.link_platform_identities(
                source_platform, source_name,
                target_platform, target_name
            )
            
            if success:
                # Update the Discord mapper cache
                discord_id = str(interaction.user.id)
                jupiter_user, user_id = user_data_manager.get_user_by_name(source_name, source_platform)
                if jupiter_user and user_id:
                    with self.user_mapper.mapping_lock:
                        self.user_mapper.discord_id_map[discord_id] = user_id
                        self.user_mapper._save_mapping()
                
                await interaction.response.send_message(
                    f"✅ Success! {message}",
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    f"❌ Linking failed: {message}",
                    ephemeral=True
                )
                
        except Exception as e:
            logger.error(f"Error processing link command: {e}")
            await interaction.response.send_message(
                "Sorry, something went wrong processing your command.",
                ephemeral=True
            )

def setup(bot, user_mapper):
    """Register the commands with the bot"""
    id_commands = IDCommands(bot, user_mapper)
    bot.add_cog(id_commands)
    
    # Register commands with Discord
    return id_commands
