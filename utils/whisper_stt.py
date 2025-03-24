"""
Standalone Speech-to-Text (STT) Script using Whisper

Usage:
------
1. Import and call the `listen_and_transcribe` function from your master script
   after detecting the wake word.

   Example:
       from stt_script import listen_and_transcribe

       transcription = listen_and_transcribe(
           silence_threshold=500,  # Adjust based on your microphone/environment
           silence_duration=2,     # Stops recording after 2 seconds of silence
           model_size="tiny"       # Choose a model size: "tiny", "base", etc.
       )
       if transcription:
           print("Transcription:", transcription)
       else:
           print("No transcription available.")

Dependencies:
    - PyAudio (for capturing audio)
    - numpy (for processing audio data)
    - whisper (for transcription)
    - wave, tempfile, os (standard Python libraries)
"""

import pyaudio
import wave
import numpy as np
import whisper
import tempfile
import os

def listen_and_transcribe(silence_threshold=500, silence_duration=2, model_size="tiny"):
    # Audio recording parameters
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 16000        # 16kHz sample rate recommended for Whisper
    CHUNK = 1024        # Frames per buffer
    SILENCE_CHUNKS = int((RATE / CHUNK) * silence_duration)

    # Initialize PyAudio and open microphone stream
    audio = pyaudio.PyAudio()
    sample_width = audio.get_sample_size(FORMAT)
    stream = audio.open(format=FORMAT, channels=CHANNELS, rate=RATE,
                        input=True, frames_per_buffer=CHUNK)

    frames = []
    silence_counter = 0

    # Record audio until two seconds of consecutive silence
    while True:
        data = stream.read(CHUNK, exception_on_overflow=False)
        frames.append(data)
        # Analyze the average amplitude for silence detection
        audio_data = np.frombuffer(data, dtype=np.int16)
        amplitude = np.abs(audio_data).mean()
        if amplitude < silence_threshold:
            silence_counter += 1
        else:
            silence_counter = 0
        if silence_counter > SILENCE_CHUNKS:
            break

    # Stop and close the audio stream
    stream.stop_stream()
    stream.close()
    audio.terminate()

    # Save recorded audio to a temporary WAV file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
        wav_filename = tmp.name
        with wave.open(wav_filename, 'wb') as wf:
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(sample_width)
            wf.setframerate(RATE)
            wf.writeframes(b''.join(frames))
    
    # Load the selected Whisper model and transcribe the audio file
    model = whisper.load_model(model_size)
    result = model.transcribe(wav_filename)
    transcription = result.get("text", "").strip()

    # Clean up the temporary file
    os.remove(wav_filename)
    return transcription

if __name__ == "__main__":
    transcription = listen_and_transcribe()
    print("Transcription:", transcription if transcription else "No transcription available.")