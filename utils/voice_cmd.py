import datetime
from utils.intent_recog import preprocess, load_model, get_intent

# Load the trained model and vectorizer from the file
classifier, vectorizer = load_model()

# Action functions
def tell_time():
    """Returns the current time in a user-friendly format"""
    current_time = datetime.datetime.now().strftime("%I:%M %p")
    return f"The current time is {current_time}."

def play_music():
    """Simulates playing music"""
    return "Playing music."

# Mapping intents to actions
intent_functions = {
    "tell_time": tell_time,
    "play_music": play_music
}