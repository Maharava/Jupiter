import pyaudio
import wave
import numpy as np
import whisper
import os

def listen_and_transcribe():
    # Audio recording parameters
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 16000              # Using 16kHz sample rate (recommended for Whisper)
    CHUNK = 1024              # Frames per buffer
    SILENCE_THRESHOLD = 500   # Amplitude threshold for silence (may need tuning)
    SILENCE_DURATION = 2      # Duration in seconds to consider as silence
    SILENCE_CHUNKS = int((RATE / CHUNK) * SILENCE_DURATION)
    
    # Initialize PyAudio
    audio = pyaudio.PyAudio()
    sample_width = audio.get_sample_size(FORMAT)

    stream = audio.open(format=FORMAT,
                        channels=CHANNELS,
                        rate=RATE,
                        input=True,
                        frames_per_buffer=CHUNK)

    #print("Recording... Speak now")
    frames = []
    silence_counter = 0

    # Record until two consecutive seconds of silence have been detected
    while True:
        data = stream.read(CHUNK)
        frames.append(data)
        
        # Convert recorded data to numpy array for amplitude analysis
        audio_data = np.frombuffer(data, dtype=np.int16)
        amplitude = np.abs(audio_data).mean()
        
        if amplitude < SILENCE_THRESHOLD:
            silence_counter += 1
        else:
            silence_counter = 0
        
        if silence_counter > SILENCE_CHUNKS:
            break

    #print("Recording ended.")

    # Cleanup the audio stream
    stream.stop_stream()
    stream.close()
    audio.terminate()

    # Write the recorded audio to a temporary WAV file
    wav_filename = "temp.wav"
    with wave.open(wav_filename, 'wb') as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(sample_width)
        wf.setframerate(RATE)
        wf.writeframes(b''.join(frames))

    # Load the offline Whisper model (use "tiny" for speed or "base" for slightly higher accuracy)
    model = whisper.load_model("tiny")

    # Transcribe the saved audio file
    result = model.transcribe(wav_filename)
    voice_input = result["text"]

    # Optionally, remove the temporary file
    os.remove(wav_filename)

    return voice_input


if __name__ == "__main__":
    voice_input = listen_and_transcribe()
    print("Voice input:", voice_input)