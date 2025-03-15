import tkinter as tk
import subprocess
import os

# Configurable paths
VENV_PATH = os.getenv('VENV_PATH', r"C:\Users\rford\Local\HomeAI\AllInOne\myenv\Scripts\activate.bat")
MAIN_SCRIPT_PATH = os.getenv('MAIN_SCRIPT_PATH', r"C:\Users\rford\Local\HomeAI\AllInOne\main.py")

def run_ai(personality):
    # Activate the virtual environment and run the main script with the selected personality
    venv_activate = VENV_PATH
    main_script = MAIN_SCRIPT_PATH
    command = f'{venv_activate} && python {main_script} {personality}'
    subprocess.Popen(['cmd.exe', '/k', command], creationflags=subprocess.CREATE_NEW_CONSOLE)

def on_jupiter():
    run_ai('Jupiter')
    root.destroy()

def on_saturn():
    run_ai('Saturn')
    root.destroy()

def on_exit():
    root.destroy()

# Create the main window
root = tk.Tk()
root.title("Select AI Personality")

# Create buttons
jupiter_button = tk.Button(root, text="Jupiter", command=on_jupiter)
saturn_button = tk.Button(root, text="Saturn", command=on_saturn)
exit_button = tk.Button(root, text="Exit", command=on_exit)

# Arrange buttons in the window
jupiter_button.pack(pady=10)
saturn_button.pack(pady=10)
exit_button.pack(pady=10)

# Run the application
root.mainloop()
