import subprocess
import os
import tempfile
import logging
from utils.path_helper import resolve_path

# Set up logging
logger = logging.getLogger("jupiter.tts")

def llm_speak(text): 
    """Convert text to speech using Piper"""
    if not text or text.strip() == "":
        return
        
    logger.info(f"Speaking: {text[:50]}...")
    
    # Use relative paths based on the current file location
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    piper_exe = os.path.join(base_dir, "utils", "piper", "piper.exe")
    model_path = os.path.join(base_dir, "utils", "piper", "models", "en_GB-vctk-medium.onnx")
    
    # Check if files exist
    if not os.path.exists(piper_exe):
        logger.error(f"Piper executable not found at {piper_exe}")
        return
        
    if not os.path.exists(model_path):
        logger.error(f"Model file not found at {model_path}")
        return
    
    # Clean the text (remove special characters that might cause issues)
    clean_text = text.replace('"', '"').replace("'", "'").replace("*", "")
    
    # Create a temporary file for the text
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt', encoding='utf-8') as temp:
        temp.write(clean_text)
        temp_path = temp.name
    
    try:
        # Use an increased length_scale (1.3 instead of 1.1) to slow down speech
        generate_command = f'"{piper_exe}" -m "{model_path}" --length_scale 1.3 --speaker 3 --output_raw < "{temp_path}" | ffplay -f s16le -ar 22050 -i pipe: -nodisp -autoexit > NUL 2>&1'
        
        # Run the command
        subprocess.run(generate_command, shell=True)
    except Exception as e:
        logger.error(f"Error running Piper: {e}")
    finally:
        # Clean up the temporary file
        try:
            os.unlink(temp_path)
        except:
            pass
    
if __name__ == "__main__": 
    llm_speak("Test complete")
