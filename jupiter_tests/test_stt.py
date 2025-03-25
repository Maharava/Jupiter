#!/usr/bin/env python3
"""
Jupiter Speech-to-Text Test

This script tests the Whisper STT module in isolation.
It listens for speech and outputs the transcription.

Usage:
    python test_stt.py [--model tiny|base|small] [--threshold THRESHOLD] [--duration SECONDS]
"""

import os
import sys
import argparse
import time
from pathlib import Path

# Add the project root to the path to enable imports
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)  # Only one dirname call needed
sys.path.insert(0, project_root)

# Parse arguments
parser = argparse.ArgumentParser(description="Jupiter Speech-to-Text Test")
parser.add_argument("--model", default="tiny", choices=["tiny", "base", "small", "medium", "large"], 
                    help="Whisper model size")
parser.add_argument("--threshold", type=int, default=500, 
                    help="Silence threshold (0-1000, higher means less sensitive)")
parser.add_argument("--duration", type=float, default=2.0, 
                    help="Silence duration before stopping (seconds)")
parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output")
args = parser.parse_args()

# Import the STT module
try:
    from utils.whisper_stt import listen_and_transcribe
    print("✓ Successfully imported STT module")
except ImportError as e:
    print(f"Error importing STT module: {e}")
    print("Make sure utils/whisper_stt.py exists and is properly implemented.")
    sys.exit(1)

# Test if required packages are installed
try:
    import pyaudio
    import whisper
    import numpy as np
    print("✓ All required packages are installed")
except ImportError as e:
    print(f"Missing required package: {e}")
    print("Make sure you have installed: pyaudio, openai-whisper, numpy")
    sys.exit(1)

# Check if whisper model is available (or will be downloaded)
try:
    model_path = os.path.join(os.path.expanduser('~'), '.cache', 'whisper', f"{args.model}.pt")
    if os.path.exists(model_path):
        size_mb = os.path.getsize(model_path) / (1024 * 1024)
        print(f"✓ Whisper {args.model} model found ({size_mb:.1f} MB)")
    else:
        print(f"! Whisper {args.model} model not found locally")
        print(f"  It will be downloaded on first use to: {model_path}")
except Exception as e:
    if args.verbose:
        print(f"Warning checking for model file: {e}")

# Test audio devices
try:
    p = pyaudio.PyAudio()
    
    # Count and print input devices
    input_devices = []
    for i in range(p.get_device_count()):
        device_info = p.get_device_info_by_index(i)
        if device_info['maxInputChannels'] > 0:
            input_devices.append(device_info)
    
    if input_devices:
        print(f"✓ Found {len(input_devices)} audio input device(s)")
        if args.verbose:
            for i, device in enumerate(input_devices):
                print(f"  {i+1}. {device['name']} (index: {device['index']})")
    else:
        print("✗ No audio input devices found")
        p.terminate()
        sys.exit(1)
    
    # Check default input device
    try:
        default_input = p.get_default_input_device_info()
        print(f"✓ Default input device: {default_input['name']}")
    except Exception as e:
        print(f"! Could not determine default input device: {e}")
    
    p.terminate()
    
except Exception as e:
    print(f"Error checking audio devices: {e}")
    sys.exit(1)

# Run the STT test
print("\nSpeech-to-Text Test")
print("-------------------")
print(f"Model: {args.model}")
print(f"Silence threshold: {args.threshold}")
print(f"Silence duration: {args.duration} seconds")
print("\nStarting recording...")
print("Please speak now. Recording will automatically stop after silence.")
print("(Press Ctrl+C to cancel)")

try:
    # Wait a moment before starting
    time.sleep(1)
    
    # Start recording and transcription
    start_time = time.time()
    print("\nListening...")
    
    transcription = listen_and_transcribe(
        silence_threshold=args.threshold,
        silence_duration=args.duration,
        model_size=args.model
    )
    
    end_time = time.time()
    duration = end_time - start_time
    
    # Print results
    print("\nResults:")
    print(f"Recording duration: {duration:.1f} seconds")
    
    if transcription:
        print(f"Transcription: \"{transcription}\"")
        print("\nTest completed successfully!")
    else:
        print("No speech detected or transcription failed.")
        print("Try adjusting the silence threshold or speaking louder.")
    
except KeyboardInterrupt:
    print("\nStopped by user")
except Exception as e:
    print(f"\nError during speech recognition: {e}")
    import traceback
    traceback.print_exc()
