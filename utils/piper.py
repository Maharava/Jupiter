import subprocess 

def llm_speak(text): 
    print(f"Speaking: {text}") 
    generate_command = f'echo "{text}" | .\\..\\piper\\piper -m ..\\piper\\models\\cori.onnx --length_scale 0.85 --output_raw | ffplay -f s16le -ar 22050 -i pipe: -nodisp -autoexit > NUL 2>&1' 
    print("Running") 
    subprocess.run(generate_command, shell=True) 
    
if __name__ == "__main__": 
    llm_speak("Test complete")