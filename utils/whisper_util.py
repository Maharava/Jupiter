import os
import time
import numpy as np
import whisper

def load_whisper_model():
    try:
        # Get the directory of the current script
        current_dir = os.path.dirname(__file__)
        # Navigate one directory up
        parent_dir = os.path.abspath(os.path.join(current_dir, os.pardir))
        # Construct the path to the Whisper model
        whis_model_path = os.path.join(parent_dir, "Whisper", "models", "small.en.pt")
        if os.path.exists(whis_model_path):
            model = whisper.load_model(whis_model_path)
            print(f"Model loaded from {whis_model_path}")
            return model
        else:
            print(f"Model file not found at {whis_model_path}")
            return None
    except Exception as e:
        print(f"Error loading Whisper model: {e}")
        return None

def is_silent(audio_data, silence_threshold):
    audio_array = np.frombuffer(audio_data, np.int16).astype(np.float32) / 32768.0
    return np.max(np.abs(audio_array)) < silence_threshold

def activate_whisper_transcription(mic_stream, whis_model, silence_threshold, silence_duration, CHUNK, timeout=30):
    frames = []
    silence_start_time = None
    start_time = time.time()
    
    while True:
        if time.time() - start_time > timeout:
            print("Transcription timeout reached.")
            break

        try:
            data = mic_stream.read(CHUNK)
            frames.append(data)
        except IOError as e:
            print(f"Error reading from microphone stream: {e}")
            break

        if is_silent(data, silence_threshold):
            if silence_start_time is None:
                silence_start_time = time.time()
            elif time.time() - silence_start_time > silence_duration:
                break
        else:
            silence_start_time = None

    audio_data = b''.join(frames)
    audio_array = np.frombuffer(audio_data, np.int16).astype(np.float32) / 32768.0

    try:
        transcription = whis_model.transcribe(audio_array)
        return transcription['text']
    except Exception as e:
        print(f"Error during transcription: {e}")
        return ""
