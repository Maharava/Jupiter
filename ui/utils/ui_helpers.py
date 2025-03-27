"""
UI Helper Utilities
"""
import logging
import gc

# Set up logging
logger = logging.getLogger("jupiter.gui.helpers")

def get_color(color_name, alpha=1.0):
    """
    Convert color name to hex with optional alpha simulation
    
    Args:
        color_name: Name or hex code of the color
        alpha: Alpha value (0.0 to 1.0)
        
    Returns:
        str: Hex color code with alpha applied
    """
    try:
        # Basic color mapping
        color_map = {
            "yellow": "#FFEB3B",
            "red": "#F44336",
            "purple": "#673AB7",
            "magenta": "#E91E63",
            "blue": "#2196F3",
            "green": "#4CAF50",
            "gray": "#9E9E9E",
            "black": "#000000",
            "white": "#FFFFFF"
        }
        
        # Get base color
        base_color = color_map.get(color_name.lower(), color_name)
        
        # Validate base color is a hex code
        if not base_color.startswith('#') or len(base_color) != 7:
            # Return a default color on invalid input
            logger.warning(f"Invalid color name or hex code: {color_name}, using default")
            base_color = "#888888"  # Default gray
        
        # If alpha is 1.0, return the base color
        if alpha == 1.0:
            return base_color
        
        # Validate alpha value
        alpha = max(0.0, min(1.0, alpha))  # Clamp between 0 and 1
        
        # Convert hex to RGB
        try:
            r = int(base_color[1:3], 16)
            g = int(base_color[3:5], 16)
            b = int(base_color[5:7], 16)
        except ValueError:
            # Return a default color on parsing failure
            logger.warning(f"Failed to parse hex color: {base_color}, using default")
            return "#888888"  # Default gray
        
        # Simulate alpha by blending with background (black)
        r = int(r * alpha)
        g = int(g * alpha)
        b = int(b * alpha)
        
        # Convert back to hex
        return f"#{r:02x}{g:02x}{b:02x}"
    except Exception as e:
        logger.error(f"Error processing color: {e}")
        return "#888888"  # Default gray on any error

def schedule_safe_update(root, update_func, pending_ids_list=None):
    """
    Schedule a UI update to run safely on the main thread
    
    Args:
        root: Tkinter root window
        update_func: Function to run
        pending_ids_list: Optional list to track scheduled IDs
    
    Returns:
        int: After ID for the scheduled task or None on failure
    """
    try:
        # Check if root exists and is a valid Tkinter window
        if root and hasattr(root, 'winfo_exists') and root.winfo_exists():
            # Wrap the update function in an error handler
            def safe_update():
                try:
                    update_func()
                except Exception as e:
                    logger.error(f"Error in scheduled update: {e}")
            
            # Schedule the update
            after_id = root.after(0, safe_update)
            
            # Keep track of scheduled task IDs if list provided
            if pending_ids_list is not None:
                pending_ids_list.append(after_id)
                
            return after_id
        else:
            logger.warning("Cannot schedule update - root window not available")
            return None
    except Exception as e:
        logger.error(f"Error scheduling UI update: {e}")
        return None

def cleanup_pending_operations(root, pending_ids_list):
    """
    Clean up any pending operations to prevent memory leaks
    
    Args:
        root: Tkinter root window
        pending_ids_list: List of pending operation IDs
    """
    try:
        # Cancel any pending after() calls
        if pending_ids_list:
            # Create a copy to avoid modification during iteration
            for after_id in list(pending_ids_list):
                try:
                    if root and hasattr(root, 'winfo_exists') and root.winfo_exists():
                        root.after_cancel(after_id)
                except Exception as e:
                    logger.debug(f"Error cancelling after ID {after_id}: {e}")
                    
            # Clear the list even if errors occurred
            pending_ids_list.clear()
        
        # Force Python garbage collection
        gc.collect()
    except Exception as e:
        logger.error(f"Error cleaning up pending operations: {e}")
        # Make sure list is cleared even on error
        if pending_ids_list:
            pending_ids_list.clear()