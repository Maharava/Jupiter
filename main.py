import os
import re
import pyaudio
import numpy as np
import time
import subprocess
import re
import threading
import argparse
import json
import atexit
import signal
from datetime import datetime
from config import *
from utils.convo_util import *
from utils.wake_word import load_oww_model
from utils.whisper_util import load_whisper_model, activate_whisper_transcription
from utils.ollama_util import send_to_ollama
from utils.piper_util import llm_speak, chunk_text, handle_piper_response
from utils.intent_recog_util import *
from utils.voice_cmd_util import intent_functions

def handle_exit():
    # Call the log_conversation function
    log_conversation(conversation_file, f"{config.ai_name} Shutdown", "")

# Register the handle_exit function to be called on normal program exit
atexit.register(handle_exit)

# Register the handle_exit function to be called on signal interrupts (like Ctrl+C)
signal.signal(signal.SIGINT, lambda sig, frame: handle_exit())
signal.signal(signal.SIGTERM, lambda sig, frame: handle_exit())


def init_args_and_models(args):
    whis_model = load_whisper_model()
    if whis_model is None:
        print("Failed to load Whisper model. Exiting...")
        exit(1)
    oww_model = load_oww_model(args)
    return whis_model, oww_model

def open_mic_stream(audio, format, channels, rate, chunk):
    try:
        device_index = None  # Set this to the correct input device index if needed
        return audio.open(format=format, channels=channels, rate=rate, input=True, input_device_index=device_index, frames_per_buffer=chunk)
    except Exception as e:
        print(f"Could not open mic stream: {e}")
        exit(1)

def reset_wakeword_timer(timer_event):
    timer_event.wait(1.5)
    global wakeword_detected
    wakeword_detected = False

def handle_input(transcription, core_prompt, conversation_file):
    classifier, vectorizer = load_recog_model()
    context = fetch_context(conversation_file)
    predicted_intent = get_intent(transcription, classifier, vectorizer)
    print(f"Predicted intent: {predicted_intent}")
    
    location = re.search(r'in (\w+)', transcription)
    location = location.group(1) if location else None

    if predicted_intent and predicted_intent in intent_functions:
        if predicted_intent == "set_timer":
            duration, timer_name = extract_timer_details(transcription)
            command_class = intent_functions[predicted_intent]
            command = command_class(core_prompt, context, duration, timer_name)
        else:
            command_class = intent_functions[predicted_intent]
            command = command_class(core_prompt, context)
        
        if predicted_intent == "get_weather" and location:
            command.run(location)
        else:
            command.execute()
    else:
        response = send_to_ollama(core_prompt, context, transcription)
        llm_speak(response)
        log_conversation(conversation_file, transcription, response)

    global wakeword_timer_event
    wakeword_timer_event.set()
    wakeword_timer_event.clear()
    threading.Thread(target=reset_wakeword_timer, args=(wakeword_timer_event,)).start()


def main():
    print("Starting main function...")
    
    try:
        args = parse_args()  # Use the parse_args function from config.py
        print(f"Arguments: {args}")
        whis_model, oww_model = init_args_and_models(args)
        print("Models loaded successfully.")
        
        if args.personality == "Saturn":
            config.jupiter = False
            config.ai_name = "Saturn"
        else:
            config.jupiter = True
            config.ai_name = "Jupiter"
        
        FORMAT = pyaudio.paInt16
        CHANNELS = 1
        RATE = 16000
        CHUNK = args.chunk_size  # Use the chunk size from args
        audio = pyaudio.PyAudio()
        
        mic_stream = open_mic_stream(audio, FORMAT, CHANNELS, RATE, CHUNK)
        print("Microphone stream opened successfully.")

        SILENCE_THRESHOLD = 0.1
        SILENCE_DURATION = 2
        
        core_prompt, user_info = load_prompts_and_user_info()
        print("Prompts and user info loaded successfully.")

        global wakeword_detected
        global wakeword_timer_event
        wakeword_detected = False
        wakeword_timer_event = threading.Event()

        debug = True
        if not config.jupiter:
            config.ai_name = "Saturn"
        llm_speak(config.ai_name + " Online")
        if not debug:
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            message = f"You are online. The current time is: {current_time}. Greet the user - keep the greeting as short as possible. User information follows:"
            response = llm_speak(send_to_ollama(core_prompt + message, "", user_info))
            log_conversation(conversation_file, "", response)
            print("Online")

        while True:
            if debug:
                print("Debug")
                handle_input("set a 1 minute 30 second timer", core_prompt, conversation_file)
                debug = False
            else:
                debug = False
                try:
                    audio_data = np.frombuffer(mic_stream.read(CHUNK), dtype=np.int16)
                    prediction = oww_model.predict(audio_data)

                    for mdl in oww_model.prediction_buffer.keys():
                        scores = list(oww_model.prediction_buffer[mdl])

                        if scores[-1] > 0.9:
                            print("Detected")
                            transcription = activate_whisper_transcription(mic_stream, whis_model, SILENCE_THRESHOLD, SILENCE_DURATION, CHUNK)
                            if len(transcription) > 2 and len(transcription.replace(" ", "")) > 1:
                                print(f"Transcription: {transcription}")
                                handle_input(transcription, core_prompt, conversation_file)

                                wakeword_detected = True
                                wakeword_timer_event.set()
                                wakeword_timer_event.clear()
                                threading.Thread(target=reset_wakeword_timer, args=(wakeword_timer_event,)).start()
                            else:
                                wakeword_detected = False
                            oww_model.prediction_buffer[mdl] = [0] * len(oww_model.prediction_buffer[mdl])

                        if wakeword_detected:
                            wakeword_timer_event.set()
                            wakeword_timer_event.clear()
                            threading.Thread(target=reset_wakeword_timer, args=(wakeword_timer_event,)).start()

                except OSError as e:
                    if e.errno == -9988:  # Stream closed error
                        print("Stream closed. Reopening...")
                        mic_stream.close()
                        mic_stream = open_mic_stream(audio, FORMAT, CHANNELS, RATE, CHUNK)
                    else:
                        print(f"An error occurred: {e}")
                        time.sleep(1)

    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    main()