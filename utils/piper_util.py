import subprocess
import time
from config import *

def llm_speak(text):
    ai_name = config.ai_name
    print(f"{ai_name}: {text}")
    llm_model = "cori.onnx"
    if ai_name == "Saturn":
        llm_model = "en_GB-northern_english_male-medium.onnx" #model for Saturn
    generate_command = f'echo {text} | .\\piper\\piper -m piper\\models\\{llm_model} --length_scale 0.85 --output_raw | ffplay -f s16le -ar 22050 -i pipe: -nodisp -autoexit > NUL 2>&1'
    print("Running")
    subprocess.run(generate_command, shell=True)

def chunk_text(text, max_chunk_size=200):
    words = text.split()
    chunks = []
    chunk = []

    for word in words:
        if len(' '.join(chunk + [word])) <= max_chunk_size:
            chunk.append(word)
        else:
            chunks.append(' '.join(chunk))
            chunk = [word]

    if chunk:
        chunks.append(' '.join(chunk))

    return chunks

def handle_piper_response(response):
    text_chunks = chunk_text(response)
    for chunk in text_chunks:
        llm_speak(chunk)
        time.sleep(0.5)
