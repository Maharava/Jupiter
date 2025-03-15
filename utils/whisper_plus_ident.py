import os
import time
import numpy as np
import whisper
from pyannote.audio.pipelines import SpeakerDiarization
from pyannote.audio import Inference
import torch
from scipy.spatial.distance import cdist

# Load Whisper model
def load_whisper_model():
    try:
        current_dir = os.path.dirname(__file__)
        parent_dir = os.path.abspath(os.path.join(current_dir, os.pardir))
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

# Load pyannote-audio speaker diarization pipeline
def load_diarization_model():
    try:
        diarization = SpeakerDiarization.from_pretrained("pyannote/speaker-diarization")
        print("Speaker Diarization model loaded")
        return diarization
    except Exception as e:
        print(f"Error loading Diarization model: {e}")
        return None

# Load pyannote-audio speaker embedding model
def load_embedding_model():
    try:
        embedding = Inference("pyannote/embedding", device=torch.device('cpu'))
        print("Speaker Embedding model loaded")
        return embedding
    except Exception as e:
        print(f"Error loading Embedding model: {e}")
        return None

# Check if audio is silent
def is_silent(audio_data, silence_threshold):
    audio_array = np.frombuffer(audio_data, np.int16).astype(np.float32) / 32768.0
    return np.max(np.abs(audio_array)) < silence_threshold

# Perform real-time transcription and speaker identification
def activate_whisper_transcription(mic_stream, whis_model, diarization_model, embedding_model, known_speakers, silence_threshold, silence_duration, CHUNK):
    frames = []
    silence_start_time = None
    while True:
        data = mic_stream.read(CHUNK)
        frames.append(data)

        if is_silent(data, silence_threshold):
            if silence_start_time is None:
                silence_start_time = time.time()
            elif time.time() - silence_start_time > silence_duration:
                break
        else:
            silence_start_time = None

    audio_data = b''.join(frames)
    audio_array = np.frombuffer(audio_data, np.int16).astype(np.float32) / 32768.0

    # Transcribe audio using Whisper
    transcription_result = whis_model.transcribe(audio_array)
    transcription = transcription_result['text']

    # Perform speaker diarization
    diarization_results = diarization_model({'waveform': audio_array, 'sample_rate': 16000})

    identified_speakers = {}

    for segment, track, speaker in diarization_results.itertracks(yield_label=True):
        segment_start, segment_end = segment.start, segment.end
        segment_audio = audio_array[int(segment_start * 16000):int(segment_end * 16000)]
        segment_embedding = embedding_model({'waveform': segment_audio, 'sample_rate': 16000}).embedding

        # Compare segment embedding to known speaker embeddings
        distances = {name: cdist([segment_embedding], [emb.embedding], metric='cosine')[0][0] for name, emb in known_speakers.items()}
        identified_speaker = min(distances, key=distances.get)

        identified_speakers[speaker] = identified_speaker

    speaker_names = ', '.join(set(identified_speakers.values()))
    return transcription, speaker_names

# Example usage
if __name__ == '__main__':
    # Load models
    whis_model = load_whisper_model()
    diarization_model = load_diarization_model()
    embedding_model = load_embedding_model()

    # Known speaker embeddings
    known_speakers = {
        "Wendy": embedding_model('path_to_wendy_voice_sample.wav'),
        "Brian": embedding_model('path_to_brian_voice_sample.wav')
    }

    # Setup audio stream (using pyaudio or other library)

    # Example usage of activate_whisper_transcription
    transcription, speaker_names = activate_whisper_transcription(mic_stream, whis_model, diarization_model, embedding_model, known_speakers, silence_threshold=0.1, silence_duration=2, CHUNK=1024)
    print("Transcription:", transcription)
    print("Identified Speakers:", speaker_names)
