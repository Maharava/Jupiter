"""
UI Helper Utilities
"""

def get_color(color_name, alpha=1.0):
    """
    Convert color name to hex with optional alpha simulation
    
    Args:
        color_name: Name or hex code of the color
        alpha: Alpha value (0.0 to 1.0)
        
    Returns:
        str: Hex color code with alpha applied
    """
    # Basic color mapping
    color_map = {
        "yellow": "#FFEB3B",
        "red": "#F44336",
        "purple": "#673AB7",
        "magenta": "#E91E63"
    }
    
    # Get base color
    base_color = color_map.get(color_name.lower(), color_name)
    
    # If alpha is 1.0, return the base color
    if alpha == 1.0:
        return base_color
    
    # Convert hex to RGB
    r = int(base_color[1:3], 16)
    g = int(base_color[3:5], 16)
    b = int(base_color[5:7], 16)
    
    # Simulate alpha by blending with background (black)
    r = int(r * alpha)
    g = int(g * alpha)
    b = int(b * alpha)
    
    # Convert back to hex
    return f"#{r:02x}{g:02x}{b:02x}"

def schedule_safe_update(root, update_func, pending_ids_list=None):
    """
    Schedule a UI update to run safely on the main thread
    
    Args:
        root: Tkinter root window
        update_func: Function to run
        pending_ids_list: Optional list to track scheduled IDs
    
    Returns:
        int: After ID for the scheduled task
    """
    if root and root.winfo_exists():
        after_id = root.after(0, update_func)
        
        # Keep track of scheduled task IDs if list provided
        if pending_ids_list is not None:
            pending_ids_list.append(after_id)
            
        return after_id
    return None

def cleanup_pending_operations(root, pending_ids_list):
    """
    Clean up any pending operations to prevent memory leaks
    
    Args:
        root: Tkinter root window
        pending_ids_list: List of pending operation IDs
    """
    # Cancel any pending after() calls
    if pending_ids_list:
        for after_id in pending_ids_list:
            try:
                if root and root.winfo_exists():
                    root.after_cancel(after_id)
            except Exception:
                pass
        pending_ids_list.clear()
    
    # Force Python garbage collection
    import gc
    gc.collect()
