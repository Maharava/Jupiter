# response_formatter.py

class ResponseFormatter:
    """Formats Jupiter's responses for Discord"""
    
    MAX_MESSAGE_LENGTH = 2000  # Discord's character limit
    
    def __init__(self):
        pass
        
    def format_response(self, response):
        """Format Jupiter's response for Discord"""
        # Handle message length limits
        if len(response) > self.MAX_MESSAGE_LENGTH:
            return self._split_long_message(response)
            
        # Convert any special formatting
        response = self._format_code_blocks(response)
            
        return response
    
    def _split_long_message(self, response):
        """Split long messages into chunks"""
        chunks = []
        current_chunk = ""
        
        for line in response.split('\n'):
            # If adding this line would exceed limit, start a new chunk
            if len(current_chunk) + len(line) + 1 > self.MAX_MESSAGE_LENGTH:
                chunks.append(current_chunk)
                current_chunk = line
            else:
                if current_chunk:
                    current_chunk += '\n' + line
                else:
                    current_chunk = line
        
        # Add the last chunk
        if current_chunk:
            chunks.append(current_chunk)
            
        return chunks
    
    def _format_code_blocks(self, text):
        """Ensure code blocks are properly formatted for Discord"""
        # Discord already supports markdown code blocks
        return text