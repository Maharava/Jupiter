def get_current_persona(config):
    """Get the current AI persona configuration"""
    # Default values if misconfigured
    default_persona = {
        "name": "Jupiter",
        "color": "yellow", 
        "wake_word": "jupiter",
        "name_variations": ["jupiter", "jup"]
    }
    
    # Try to get configured persona
    ai_config = config.get("ai", {})
    current_name = ai_config.get("current_persona", "jupiter")
    personas = ai_config.get("personas", {})
    
    # Return the current persona, or default if not found
    return personas.get(current_name, default_persona)