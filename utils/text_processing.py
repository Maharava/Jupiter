import re

try:
    import tiktoken
    TOKENIZER = tiktoken.get_encoding("cl100k_base")
    USE_TIKTOKEN = True
except ImportError:
    USE_TIKTOKEN = False

def count_tokens(text):
    """
    Count tokens in text with improved fallback when tiktoken is not available.
    This uses a more accurate heuristic based on GPT tokenization patterns.
    """
    if USE_TIKTOKEN:
        return len(TOKENIZER.encode(text))
    else:
        # More accurate approximation than simple word splitting
        # GPT tokenizers generally split on whitespace, punctuation, and subword units
        
        # 1. Count words (including contractions as single tokens)
        words = re.findall(r'\b[\w\']+\b', text)
        word_count = len(words)
        
        # 2. Count punctuation and special characters that become separate tokens
        punctuation = re.findall(r'[^\w\s]', text)
        punct_count = len(punctuation)
        
        # 3. Add adjustment for long words that will be split into multiple tokens
        # Most tokenizers split words around 4-6 characters
        long_word_chars = sum(max(0, len(word) - 5) for word in words)
        long_word_adjustment = long_word_chars // 4  # Approximate additional tokens
        
        # 4. Calculate final count
        return word_count + punct_count + long_word_adjustment

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