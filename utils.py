import re
import requests
import datetime
import os

# Try to import tiktoken
try:
    import tiktoken
    TOKENIZER = tiktoken.get_encoding("cl100k_base")
    USE_TIKTOKEN = True
except ImportError:
    USE_TIKTOKEN = False

def count_tokens(text):
    """Count tokens in text"""
    if USE_TIKTOKEN:
        return len(TOKENIZER.encode(text))
    else:
        # Simple approximation
        return len(re.findall(r'\w+|[^\w\s]', text))

def send_to_kobold(url, message, user_prefix):
    """Send message to KoboldCPP and return response"""
    # KoboldCPP API logic
    # ...

def log_message(log_file, role, message):
    """Log message to file"""
    # Logging logic
    # ...