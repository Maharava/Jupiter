class MockVoice:
    """Mock for the voice/TTS functions"""
    
    def __init__(self):
        """Initialize the mock voice module"""
        self.spoken_texts = []
        self.enabled = True
    
    def speak(self, text):
        """
        Mock for the speak function.
        Instead of speaking, records the text that would have been spoken.
        """
        if self.enabled:
            self.spoken_texts.append(text)
            print(f"MOCK TTS: {text}")
        return True
    
    def disable(self):
        """Disable voice output"""
        self.enabled = False
    
    def enable(self):
        """Enable voice output"""
        self.enabled = True
    
    def get_spoken_texts(self):
        """Get the list of texts that have been 'spoken'"""
        return self.spoken_texts
    
    def clear(self):
        """Clear the list of spoken texts"""
        self.spoken_texts = []


# Create a singleton instance
mock_voice = MockVoice()

def llm_speak(text):
    """
    Mock replacement for the llm_speak function.
    Records the text instead of actually speaking it.
    """
    return mock_voice.speak(text)
