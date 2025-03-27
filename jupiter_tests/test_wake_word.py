#!/usr/bin/env python3
"""
Wake Word Diagnostics Tool for Jupiter

This script helps diagnose issues with wake word detection by:
1. Checking dependencies
2. Locating model files
3. Testing model loading
4. Testing audio device access

Usage:
    python voice_diagnostics.py
"""

import os
import sys
import importlib
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("voice_diagnostics")

def check_dependencies():
    """Check if required dependencies are installed"""
    print("\n=== Checking Dependencies ===")
    
    dependencies = [
        ("torch", "PyTorch is required for wake word model inference"),
        ("pyaudio", "PyAudio is required for audio capture"),
        ("librosa", "Librosa is required for audio processing"),
        ("numpy", "NumPy is required for audio data handling"),
        ("whisper", "Whisper is required for speech recognition")
    ]
    
    all_ok = True
    for package, description in dependencies:
        try:
            importlib.import_module(package)
            print(f"✅ {package}: Installed")
        except ImportError:
            print(f"❌ {package}: Missing - {description}")
            all_ok = False
    
    return all_ok

def find_wake_word_model():
    """Find the wake word model file"""
    print("\n=== Checking Wake Word Model ===")
    
    # Get the base directory (Jupiter root)
    # Assuming this script is in utils/voice_diagnostics.py
    current_dir = os.path.dirname(os.path.abspath(__file__))
    base_dir = os.path.dirname(current_dir)
    
    # Common model file names
    model_filenames = [
        "jupiter-wake-word.pth",
        "wake-word-model.pth",
        "io-model.pth"
    ]
    
    # Places to search
    search_locations = [
        base_dir,
        os.path.join(base_dir, "utils", "io"),
        os.path.join(base_dir, "models"),
        os.path.join(base_dir, "utils", "models"),
        current_dir
    ]
    
    # Check common configurations
    print(f"Looking for wake word models in common locations...")
    
    found_models = []
    
    for location in search_locations:
        for filename in model_filenames:
            path = os.path.join(location, filename)
            if os.path.isfile(path):
                found_models.append(path)
                print(f"✅ Found model: {path}")
    
    # Also check if any .pth files exist in these directories
    for location in search_locations:
        if os.path.isdir(location):
            for file in os.listdir(location):
                if file.endswith(".pth") and os.path.join(location, file) not in found_models:
                    found_models.append(os.path.join(location, file))
                    print(f"✅ Found potential model: {os.path.join(location, file)}")
    
    if not found_models:
        print("❌ No wake word model files found")
        print("\nSuggestions:")
        print("1. Download a wake word model file (.pth)")
        print("2. Place it in one of these locations:")
        for location in search_locations:
            print(f"   - {location}")
        print("3. Update your configuration to point to the model file")
        return None
    
    return found_models

def test_wake_word_loading(model_paths):
    """Test loading the wake word model"""
    if not model_paths:
        return False
    
    print("\n=== Testing Wake Word Model Loading ===")
    
    try:
        # Import dependencies
        import torch
        from utils.io.io import WakeWordDetector
        
        # Try loading each found model
        success = False
        
        for model_path in model_paths:
            try:
                print(f"Testing model: {model_path}")
                detector = WakeWordDetector(model_path=model_path)
                print(f"✅ Successfully loaded wake word model from {model_path}")
                success = True
                
                # Try initializing detector
                try:
                    detector.start()
                    print("✅ Successfully initialized wake word detector")
                    detector.stop()
                except Exception as e:
                    print(f"❌ Failed to initialize detector: {e}")
                
                break  # Stop after first success
                
            except Exception as e:
                print(f"❌ Failed to load model {model_path}: {e}")
        
        return success
    
    except ImportError as e:
        print(f"❌ Cannot test model loading - missing dependencies: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error testing model loading: {e}")
        return False

def test_audio_device():
    """Test audio device access"""
    print("\n=== Testing Audio Device Access ===")
    
    try:
        import pyaudio
        
        p = pyaudio.PyAudio()
        device_count = p.get_device_count()
        
        print(f"Found {device_count} audio devices:")
        
        # Get default input device
        try:
            default_input = p.get_default_input_device_info()
            print(f"✅ Default input device: {default_input['name']} (index {default_input['index']})")
            default_index = default_input['index']
        except Exception as e:
            print(f"❌ Error getting default input device: {e}")
            default_index = None
        
        # List all input devices
        input_devices = []
        for i in range(device_count):
            try:
                device_info = p.get_device_info_by_index(i)
                if device_info['maxInputChannels'] > 0:
                    input_devices.append(device_info)
                    star = "*" if default_index is not None and i == default_index else " "
                    print(f"{star} Input #{i}: {device_info['name']} (channels: {device_info['maxInputChannels']})")
            except Exception as e:
                print(f"  Error getting device #{i} info: {e}")
        
        # Test opening a stream
        if input_devices:
            try:
                # Try to open a stream with the default input device
                stream = p.open(
                    format=pyaudio.paInt16,
                    channels=1,
                    rate=16000,
                    input=True,
                    frames_per_buffer=1024,
                    input_device_index=default_index
                )
                
                print("✅ Successfully opened audio input stream")
                stream.close()
            except Exception as e:
                print(f"❌ Failed to open audio input stream: {e}")
        else:
            print("❌ No input devices available")
        
        p.terminate()
        
        return len(input_devices) > 0
    
    except ImportError:
        print("❌ Cannot test audio - PyAudio not installed")
        return False
    except Exception as e:
        print(f"❌ Unexpected error testing audio: {e}")
        return False

def main():
    """Run all diagnostics"""
    print("Jupiter Voice System Diagnostics")
    print("===============================")
    
    # Check Python version
    print(f"Python version: {sys.version}")
    
    # Run all tests
    deps_ok = check_dependencies()
    model_paths = find_wake_word_model()
    model_ok = test_wake_word_loading(model_paths)
    audio_ok = test_audio_device()
    
    # Summary
    print("\n=== Summary ===")
    print(f"Dependencies: {'✅ OK' if deps_ok else '❌ Missing dependencies'}")
    print(f"Wake Word Model: {'✅ Found and loadable' if model_ok else '❌ Issues with model'}")
    print(f"Audio Device: {'✅ Available' if audio_ok else '❌ Issues with audio'}")
    
    if deps_ok and model_ok and audio_ok:
        print("\n✅ All checks passed! Voice system should work correctly.")
    else:
        print("\n❌ Some checks failed. Please address the issues above.")
        
        # Provide specific suggestions
        print("\nSuggestions:")
        if not deps_ok:
            print("- Install missing dependencies:")
            print("  pip install torch pyaudio librosa numpy openai-whisper")
        if not model_ok:
            print("- Ensure the wake word model file (.pth) is in the correct location")
            print("- Update your configuration to point to the model file")
        if not audio_ok:
            print("- Check your microphone is connected and working")
            print("- Ensure you have permission to access audio devices")
            print("- Try installing PyAudio properly: pip install pyaudio")
            if sys.platform == "linux":
                print("- On Linux, you may need: sudo apt-get install portaudio19-dev")
            elif sys.platform == "darwin":
                print("- On macOS, you may need: brew install portaudio")

if __name__ == "__main__":
    main()