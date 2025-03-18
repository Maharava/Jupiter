import subprocess
import os
import tempfile

def llm_speak(text): 
    print(f"Speaking: {text}")
    
    # Skip empty text
    if not text or text.strip() == "":
        return
    
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
    
    # Clean the text
    clean_text = text.replace('"', '"').replace("'", "'").replace("*", "")
    
    # Create a temporary file for the text
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt', encoding='utf-8') as temp:
        temp.write(clean_text)
        temp_path = temp.name
    
    try:
        # Use a single command with the text file as input (no chunking)
        # Uses a faster speech rate with length_scale=0.65
        generate_command = f'"{piper_exe}" -m "{model_path}" --length_scale 0.75 --output_raw < "{temp_path}" | ffplay -f s16le -ar 22050 -i pipe: -nodisp -autoexit > NUL 2>&1'
        
        # Run the command
        subprocess.run(generate_command, shell=True)
    except Exception as e:
        print(f"Error running Piper: {e}")
    finally:
        # Clean up the temporary file
        try:
            os.unlink(temp_path)
        except:
            pass
    
if __name__ == "__main__": 
    llm_speak("Test complete")