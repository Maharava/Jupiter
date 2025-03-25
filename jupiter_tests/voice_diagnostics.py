#!/usr/bin/env python3
"""
Jupiter Voice Diagnostics

This script performs diagnostics on Jupiter's voice components to help
troubleshoot issues with wake word detection and speech recognition.

Usage:
    python voice_diagnostics.py [--verbose]
"""

import os
import sys
import argparse
import importlib
import platform
import subprocess
from pathlib import Path

# Add the project root to the path to enable imports
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)  # Only one dirname call needed
sys.path.insert(0, project_root)

# Configure colored output
try:
    from colorama import init, Fore, Style
    init()  # Initialize colorama
    
    def success(msg):
        return f"{Fore.GREEN}✓ {msg}{Style.RESET_ALL}"
    
    def error(msg):
        return f"{Fore.RED}✗ {msg}{Style.RESET_ALL}"
    
    def warning(msg):
        return f"{Fore.YELLOW}! {msg}{Style.RESET_ALL}"
        
    def info(msg):
        return f"{Fore.CYAN}ℹ {msg}{Style.RESET_ALL}"
        
except ImportError:
    # Fallback if colorama is not available
    def success(msg):
        return f"✓ {msg}"
    
    def error(msg):
        return f"✗ {msg}"
    
    def warning(msg):
        return f"! {msg}"
        
    def info(msg):
        return f"ℹ {msg}"

# Parse arguments
parser = argparse.ArgumentParser(description="Jupiter Voice Diagnostics")
parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output")
args = parser.parse_args()

VERBOSE = args.verbose

def print_section(title):
    """Print a section title"""
    print(f"\n{Fore.BLUE}=== {title} ==={Style.RESET_ALL}")

def check_import(module_name):
    """Check if a module can be imported"""
    try:
        importlib.import_module(module_name)
        print(success(f"Successfully imported {module_name}"))
        return True
    except ImportError as e:
        print(error(f"Failed to import {module_name}: {e}"))
        return False

def check_file_exists(file_path):
    """Check if a file exists"""
    if os.path.exists(file_path):
        print(success(f"Found file: {file_path}"))
        return True
    else:
        print(error(f"File not found: {file_path}"))
        return False

def check_for_wake_word_model():
    """Search for the wake word model file in common locations"""
    print_section("Wake Word Model")
    
    # Check common locations
    possible_locations = [
        # Config-specified path
        "utils/io/models/jupiter-wake-word.pth",
        # Alternative locations
        "utils/io/jupiter-wake-word.pth",
        "models/jupiter-wake-word.pth",
        "utils/io/models/wake_word.pth",
        "utils/io/wake_word.pth",
    ]
    
    # Get potential paths from config
    try:
        import json
        config_path = os.path.join(project_root, "config", "default_config.json")
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config = json.load(f)
                if 'voice' in config and 'wake_word_model' in config['voice']:
                    model_path = config['voice']['wake_word_model']
                    if model_path not in possible_locations:
                        possible_locations.insert(0, model_path)
    except Exception as e:
        print(warning(f"Could not read config file: {e}"))
    
    # Check all possible locations
    found = False
    for location in possible_locations:
        # Try absolute path
        abs_path = os.path.join(project_root, location)
        if os.path.exists(abs_path):
            print(success(f"Found wake word model at: {abs_path}"))
            found = True
            break
    
    if not found:
        print(error("Wake word model not found in any expected location"))
        print(info("You may need to download or train a wake word model"))
        
    return found

def check_pytorch():
    """Check if PyTorch is installed and working"""
    print_section("PyTorch")
    
    try:
        import torch
        print(success(f"PyTorch version: {torch.__version__}"))
        
        # Check for CUDA
        if torch.cuda.is_available():
            print(success(f"CUDA available: {torch.cuda.get_device_name(0)}"))
        else:
            print(warning("CUDA not available, using CPU for inference"))
            
        # Test a simple operation
        tensor = torch.rand(3, 3)
        result = torch.matmul(tensor, tensor)
        if result is not None:
            print(success("PyTorch tensor operations working"))
            return True
        else:
            print(error("PyTorch tensor operations failed"))
            return False
            
    except ImportError:
        print(error("PyTorch not installed"))
        print(info("Install with: pip install torch"))
        return False
    except Exception as e:
        print(error(f"PyTorch error: {e}"))
        return False

def check_wake_word_detector():
    """Test importing and initializing the wake word detector"""
    print_section("Wake Word Detector")
    
    try:
        from utils.io.io import WakeWordDetector
        print(success("Successfully imported WakeWordDetector"))
        
        # Try to initialize with a dummy model path
        try:
            # Find an actual model path first
            model_path = None
            possible_locations = [
                "utils/io/models/jupiter-wake-word.pth",
                "utils/io/jupiter-wake-word.pth",
                "models/jupiter-wake-word.pth",
            ]
            
            for location in possible_locations:
                abs_path = os.path.join(project_root, location)
                if os.path.exists(abs_path):
                    model_path = abs_path
                    break
            
            if model_path:
                print(info(f"Attempting to initialize WakeWordDetector with {model_path}"))
                detector = WakeWordDetector(model_path=model_path)
                print(success("WakeWordDetector initialized successfully"))
                
                # Check if wake word methods are available
                if hasattr(detector, 'start') and callable(detector.start):
                    print(success("WakeWordDetector has required methods"))
                else:
                    print(error("WakeWordDetector missing required methods"))
                    
                return True
            else:
                print(warning("Skipping WakeWordDetector initialization (no model found)"))
                return False
                
        except Exception as e:
            print(error(f"Failed to initialize WakeWordDetector: {e}"))
            import traceback
            if VERBOSE:
                traceback.print_exc()
            return False
            
    except ImportError as e:
        print(error(f"Failed to import WakeWordDetector: {e}"))
        return False
    except Exception as e:
        print(error(f"Unexpected error: {e}"))
        return False
        
def check_audio_devices():
    """Check for audio devices"""
    print_section("Audio Devices")
    
    try:
        import pyaudio
        p = pyaudio.PyAudio()
        
        # Count input devices
        input_devices = []
        for i in range(p.get_device_count()):
            device_info = p.get_device_info_by_index(i)
            if device_info['maxInputChannels'] > 0:
                input_devices.append(device_info)
        
        # Print input devices
        if input_devices:
            print(success(f"Found {len(input_devices)} input device(s)"))
            for i, device in enumerate(input_devices):
                print(f"  {i+1}. {device['name']} (index: {device['index']})")
                if VERBOSE:
                    print(f"     Channels: {device['maxInputChannels']}")
                    print(f"     Sample Rate: {device['defaultSampleRate']}")
        else:
            print(error("No input devices found"))
            
        # Check default input device
        try:
            default_input = p.get_default_input_device_info()
            print(success(f"Default input device: {default_input['name']} (index: {default_input['index']})"))
        except Exception as e:
            print(error(f"Error getting default input device: {e}"))
            
        # Clean up
        p.terminate()
        
        return len(input_devices) > 0
            
    except ImportError:
        print(error("PyAudio not installed"))
        print(info("Install with: pip install pyaudio"))
        return False
    except Exception as e:
        print(error(f"Error checking audio devices: {e}"))
        return False

def check_stt_module():
    """Check the Speech-to-Text module"""
    print_section("Speech-to-Text")
    
    try:
        from utils.whisper_stt import listen_and_transcribe
        print(success("Successfully imported listen_and_transcribe"))
        
        # Check for whisper
        try:
            import whisper
            print(success(f"Whisper installed"))
            
            # Check for available models
            try:
                models_dir = os.path.join(os.path.expanduser('~'), '.cache', 'whisper')
                if os.path.exists(models_dir):
                    models = [f for f in os.listdir(models_dir) if os.path.isfile(os.path.join(models_dir, f))]
                    if models:
                        print(success(f"Found {len(models)} Whisper model(s)"))
                        for model in models:
                            print(f"  - {model}")
                    else:
                        print(warning("No cached Whisper models found"))
                else:
                    print(warning("Whisper models directory not found"))
            except Exception as e:
                if VERBOSE:
                    print(warning(f"Error checking Whisper models: {e}"))
            
            return True
        except ImportError:
            print(error("Whisper not installed"))
            print(info("Install with: pip install openai-whisper"))
            return False
            
    except ImportError:
        print(error("Failed to import listen_and_transcribe function"))
        return False
    except Exception as e:
        print(error(f"Unexpected error: {e}"))
        return False

def check_voice_manager():
    """Check the VoiceManager module"""
    print_section("Voice Manager")
    
    try:
        from utils.voice_manager import VoiceManager
        print(success("Successfully imported VoiceManager"))
        
        # Check VoiceState enum
        try:
            from utils.voice_manager import VoiceState
            print(success("Successfully imported VoiceState enum"))
            
            # Check required states
            required_states = ["INACTIVE", "LISTENING", "FOCUSING", "PROCESSING", "SPEAKING"]
            missing_states = [state for state in required_states if not hasattr(VoiceState, state)]
            
            if not missing_states:
                print(success("VoiceState has all required states"))
            else:
                print(error(f"VoiceState missing required states: {', '.join(missing_states)}"))
                
        except ImportError:
            print(error("Failed to import VoiceState enum"))
        
        return True
        
    except ImportError:
        print(error("Failed to import VoiceManager class"))
        return False
    except Exception as e:
        print(error(f"Unexpected error: {e}"))
        return False

def main():
    """Run all diagnostics"""
    print_section("System Information")
    print(f"Python: {sys.version}")
    print(f"Platform: {platform.platform()}")
    print(f"Path: {sys.path[0]}")
    
    # Run all checks
    checks = [
        check_for_wake_word_model,
        check_pytorch,
        check_audio_devices,
        check_wake_word_detector,
        check_stt_module,
        check_voice_manager
    ]
    
    results = {}
    for check in checks:
        result = check()
        results[check.__name__] = result
    
    # Print summary
    print_section("Diagnostics Summary")
    success_count = sum(1 for result in results.values() if result)
    print(f"Passed {success_count}/{len(checks)} checks")
    
    failed_checks = [name.replace('check_', '').replace('_', ' ').title() 
                    for name, result in results.items() if not result]
    
    if failed_checks:
        print(error(f"Issues found with: {', '.join(failed_checks)}"))
        print()
        print(info("Suggestions:"))
        
        if "wake word model" in ' '.join(failed_checks).lower():
            print("- Download or train a wake word model")
            print("- Ensure the model path in config/default_config.json is correct")
            
        if "pytorch" in ' '.join(failed_checks).lower():
            print("- Install PyTorch: pip install torch")
            
        if "audio devices" in ' '.join(failed_checks).lower():
            print("- Check your microphone connection")
            print("- Ensure microphone permissions are granted")
            print("- Install PyAudio: pip install pyaudio")
            
        if "wake word detector" in ' '.join(failed_checks).lower():
            print("- Check the implementation of utils/io/io.py")
            
        if "stt module" in ' '.join(failed_checks).lower():
            print("- Install Whisper: pip install openai-whisper")
            
        if "voice manager" in ' '.join(failed_checks).lower():
            print("- Check the implementation of utils/voice_manager.py")
            
    else:
        print(success("All checks passed!"))
        
    print("\nFor more detailed diagnostics, run with --verbose flag")

if __name__ == "__main__":
    main()
