import subprocess
import os

def llm_speak(text): 
    print(f"Speaking: {text}")
    
    # Hard-code the exact paths since we know them
    piper_exe = "C:\\Users\\rford\\Local\\HomeAI\\AllInOne\\piper\\piper.exe"
    model_path = "C:\\Users\\rford\\Local\\HomeAI\\AllInOne\\piper\\models\\cori.onnx"
    
    # Check if files exist
    if not os.path.exists(piper_exe):
        print(f"ERROR: Piper executable not found at {piper_exe}")
        return
        
    if not os.path.exists(model_path):
        print(f"ERROR: Model file not found at {model_path}")
        return
    
    # Clean the text to avoid command injection without adding backslashes the TTS will read
    # Instead of escaping quotes, we'll replace them with similar characters
    safe_text = text.replace('"', '"').replace("'", "'")
    
    # Use the absolute paths in the command
    generate_command = f'echo "{safe_text}" | "{piper_exe}" -m "{model_path}" --length_scale 0.85 --output_raw | ffplay -f s16le -ar 22050 -i pipe: -nodisp -autoexit > NUL 2>&1'
    
    print(f"Running command: {generate_command}")
    try:
        subprocess.run(generate_command, shell=True)
    except Exception as e:
        print(f"Error running Piper: {e}")
    
if __name__ == "__main__": 
    llm_speak("Test complete")