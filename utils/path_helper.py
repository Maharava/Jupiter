import os
import inspect

def resolve_path(relative_path, base_file=None):
    """
    Resolve a relative path to an absolute path
    
    Args:
        relative_path: The relative path to resolve
        base_file: The file to use as base (defaults to the calling file)
    
    Returns:
        str: The absolute path
    """
    # Return if already absolute
    if os.path.isabs(relative_path):
        return relative_path
        
    if base_file is None:
        # Get the file that called this function
        frame = inspect.stack()[1]
        base_file = frame.filename
        
    # Get the base directory (two levels up from the file)
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(base_file)))
    
    # Join with the relative path
    abs_path = os.path.join(base_dir, relative_path)
    
    return abs_path
