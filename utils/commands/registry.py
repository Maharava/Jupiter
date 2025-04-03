from typing import Dict, Callable, List, Any, Optional

class Command:
    """Represents a Jupiter command that works across platforms"""
    def __init__(self, name, handler, description, usage=None, platforms=None):
        self.name = name
        self.handler = handler  # Function that implements the command
        self.description = description
        self.usage = usage or f"/{name}"
        self.platforms = platforms or ["discord", "terminal", "gui"]
        
class CommandRegistry:
    """Central registry for all Jupiter commands"""
    def __init__(self):
        self.commands: Dict[str, Command] = {}
        
    def register(self, command: Command) -> None:
        """Register a command"""
        self.commands[command.name] = command
        
    def get(self, name: str) -> Optional[Command]:
        """Get a command by name"""
        return self.commands.get(name)
    
    def get_command(self, name: str) -> Optional[Command]:
        """Alias for get() - returns a command by name"""
        return self.get(name)
        
    def get_for_platform(self, platform: str) -> List[Command]:
        """Get all commands available for a specific platform"""
        return [cmd for cmd in self.commands.values() if platform in cmd.platforms]

# Create a singleton instance
registry = CommandRegistry()