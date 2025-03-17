import sys
from utils.intent_recog_util import preprocess, load_model, get_intent
from utils.ollama_util import send_to_ollama
from utils.piper_util import llm_speak

# Load the trained model and vectorizer from the file
classifier, vectorizer = load_model()

# Action functions
def shut_down(core_prompt,context):
    response = send_to_ollama(core_prompt, "", "The user is signing off now. Please say goodbye.")
    llm_speak(response)
    # Wait for the response to be spoken
    sys.exit(0)

def play_music():
    return "Playing music."

def set_alarm(time):
    return f"Alarm set for {time}."

# Mapping intents to actions
intent_functions = {
    "shut_down": shut_down,
    "play_music": play_music,
    "set_alarm": lambda: set_alarm("7 AM")
}
