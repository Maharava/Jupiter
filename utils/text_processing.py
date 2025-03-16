import re

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

def truncate_to_token_limit(text, history, system_prompt, token_limit):
    """Truncate history to fit within token limit"""
    # Start with system prompt and current text
    total_text = system_prompt + "\n\n" + text
    total_tokens = count_tokens(total_text)
    
    # Add history items until we approach the limit
    preserved_history = []
    
    for msg in reversed(history):
        msg_tokens = count_tokens(msg)
        
        if total_tokens + msg_tokens < token_limit:
            preserved_history.insert(0, msg)
            total_tokens += msg_tokens
        else:
            break
    
    return preserved_history