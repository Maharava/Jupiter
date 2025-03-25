#!/usr/bin/env python3
"""
Jupiter Wake Word Test

This script tests the wake word detector (Io) in isolation.
It attempts to initialize the detector, listen for the wake word,
and report success or failure.

Usage:
    python test_wake_word.py --model path/to/model.pth [--timeout SECONDS]
"""

import os
import sys
import argparse
import time
from pathlib import Path

# Add the project root to the path to enable imports
# Add the project root to the path to enable imports
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)  # Only one dirname call needed
sys.path.insert(0, project_root)

# Parse arguments
parser = argparse.ArgumentParser(description="Jupiter Wake Word Test")
parser.add_argument("--model", help="Path to wake word model file")
parser.add_argument("--timeout", type=int, default=15, help="Listen timeout in seconds")
parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output")
args = parser.parse_args()

# Determine model path
model_path = args.model
if not model_path:
    # Check common locations
    possible_locations = [
        "utils/io/models/jupiter-wake-word.pth",
        "utils/io/jupiter-wake-word.pth",
        "models/jupiter-wake-word.pth",
    ]
    
    # Try to get from config
    try:
        import json
        config_path = os.path.join(project_root, "config", "default_config.json")
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config = json.load(f)
                if 'voice' in config and 'wake_word_model' in config['voice']:
                    config_model = config['voice']['wake_word_model']
                    if config_model:
                        # Make path absolute if relative
                        if not os.path.isabs(config_model):
                            config_model = os.path.join(project_root, config_model)
                        possible_locations.insert(0, config_model)
    except Exception as e:
        if args.verbose:
            print(f"Warning: Could not read config file: {e}")
    
    # Check each location
    for location in possible_locations:
        # Try as absolute path first
        if os.path.exists(location):
            model_path = location
            break
            
        # Try as relative to project root
        abs_path = os.path.join(project_root, location)
        if os.path.exists(abs_path):
            model_path = abs_path
            break

# Validate model path
if not model_path or not os.path.exists(model_path):
    print(f"Error: Wake word model not found.")
    if not model_path:
        print("Please specify a model path with --model or add to config.")
    else:
        print(f"The specified model path does not exist: {model_path}")
    sys.exit(1)

print(f"Using wake word model: {model_path}")

# Import the wake word detector
try:
    from utils.io.io import WakeWordDetector
except ImportError as e:
    print(f"Error importing WakeWordDetector: {e}")
    print("Make sure utils/io/io.py exists and is properly implemented.")
    sys.exit(1)

# Define callback for wake word detection
def wake_word_callback(confidence):
    print(f"\n✓ Wake word detected! (confidence: {confidence:.4f})")
    print("Test successful")

# Create and test the detector
print(f"Initializing wake word detector...")
try:
    detector = WakeWordDetector(model_path=model_path)
    print("✓ Wake word detector initialized successfully")
except Exception as e:
    print(f"✗ Failed to initialize wake word detector: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Register callback
detector.register_detection_callback(wake_word_callback)

# Start listening
print(f"Listening for wake word for {args.timeout} seconds...")
print("Say 'Jupiter' to test the detector")
print("Press Ctrl+C to stop")

try:
    # Start detection
    detector.start()
    
    # Listen for a specific time or until detection
    timeout = time.time() + args.timeout
    while time.time() < timeout:
        time.sleep(0.1)
        
    print("\nTimeout reached. No wake word detected.")
    
except KeyboardInterrupt:
    print("\nStopped by user")
except Exception as e:
    print(f"Error during testing: {e}")
    import traceback
    traceback.print_exc()
finally:
    # Ensure detector is stopped
    try:
        detector.stop()
        print("Wake word detector stopped")
    except:
        pass
