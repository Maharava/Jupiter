"""
Test script for Io Wake Word detection

This script tests the basic functionality of the io-wake-word package
and verifies that your model file is correctly detected and loaded.
"""

import os
import time
import logging
import sys

# Set up logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("wake-word-test")

def find_model_file(model_name="jupiter-wake-word.pth"):
    """Try to find the wake word model file in common locations"""
    # Get base directory
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Potential locations to check
    potential_paths = [
        os.path.join(base_dir, model_name),  # Current directory
        os.path.join(base_dir, "models", model_name),  # models/ subdirectory
        os.path.join(base_dir, "assets", model_name),  # assets/ subdirectory
        os.path.join(base_dir, "io_wake_word", model_name),  # io_wake_word folder
        os.path.join(base_dir, "utils", "io_wake_word", model_name),  # utils/io_wake_word folder
        os.path.join(base_dir, "io-wake-word", model_name),  # io-wake-word folder (with hyphen)
    ]
    
    # Check each path
    for path in potential_paths:
        if os.path.exists(path):
            logger.info(f"Found model file at: {path}")
            return path
    
    # Not found
    logger.error(f"Model file '{model_name}' not found in any of these locations:")
    for path in potential_paths:
        logger.info(f"  - {path}")
    return None

def check_package_imports():
    """Check if io_wake_word package can be imported"""
    try:
        import io_wake_word
        logger.info(f"io_wake_word package found: {io_wake_word.__file__}")
        return True
    except ImportError as e:
        logger.error(f"Failed to import io_wake_word: {e}")
        logger.info("Please install io-wake-word: pip install io-wake-word")
        return False

def test_wake_word_components(model_path):
    """Test all the wake word components"""
    try:
        # Import components
        from io_wake_word.audio import AudioCapture, FeatureExtractor
        from io_wake_word.models import WakeWordDetector
        
        logger.info("Successfully imported all components")
        
        # Try to create audio capture
        logger.info("Initializing AudioCapture...")
        audio = AudioCapture()
        logger.info("AudioCapture initialized successfully")
        
        # Try to create feature extractor
        logger.info("Initializing FeatureExtractor...")
        extractor = FeatureExtractor()
        logger.info("FeatureExtractor initialized successfully")
        
        # Try to create detector with model
        logger.info(f"Initializing WakeWordDetector with model: {model_path}")
        detector = WakeWordDetector(model_path=model_path)
        logger.info("WakeWordDetector initialized successfully")
        
        # Test detection callback
        def detection_callback(confidence):
            logger.info(f"Wake word detected with confidence: {confidence:.4f}")
        
        logger.info("Registering detection callback...")
        detector.register_callback(detection_callback)
        logger.info("Callback registered successfully")
        
        # Try starting audio capture
        logger.info("Starting audio capture...")
        audio.start()
        logger.info("Audio capture started successfully")
        
        # Process a few frames to test detection
        logger.info("Testing audio processing for 5 seconds...")
        start_time = time.time()
        while time.time() - start_time < 5:
            # Get audio buffer
            buffer = audio.get_buffer()
            
            # If buffer available, extract features and detect
            if buffer is not None:
                features = extractor.extract(buffer)
                if features is not None:
                    detector.detect(features)
            
            time.sleep(0.01)
            
        # Stop audio capture
        logger.info("Stopping audio capture...")
        audio.stop()
        logger.info("Audio capture stopped successfully")
        
        return True
        
    except Exception as e:
        logger.error(f"Error testing wake word components: {e}")
        return False

if __name__ == "__main__":
    print("\n=== Jupiter Wake Word Detection Test ===\n")
    
    # Check if io_wake_word package is installed
    if not check_package_imports():
        print("\n❌ io_wake_word package not available. Please install:")
        print("pip install io-wake-word")
        sys.exit(1)
    
    # Find the model file
    model_path = find_model_file()
    if not model_path:
        print("\n❌ Wake word model file not found.")
        print("Please place 'jupiter-wake-word.pth' in one of these locations:")
        print("- Project root directory")
        print("- 'models/' subdirectory")
        print("- 'assets/' subdirectory")
        print("- 'io_wake_word/' subdirectory")
        sys.exit(1)
    
    # Test wake word components
    print("\nTesting wake word components...")
    if test_wake_word_components(model_path):
        print("\n✅ All wake word components tested successfully!")
        print("\nSay 'Jupiter' to test wake word detection (running for 30 seconds)...")
        
        try:
            # Simple interactive test
            from io_wake_word.audio import AudioCapture, FeatureExtractor
            from io_wake_word.models import WakeWordDetector
            
            # Create components
            audio = AudioCapture()
            extractor = FeatureExtractor()
            detector = WakeWordDetector(model_path=model_path)
            
            # Register callback
            def on_wake_word(confidence):
                print(f"\n✨ Wake word detected! Confidence: {confidence:.4f}")
            
            detector.register_callback(on_wake_word)
            
            # Start audio
            audio.start()
            
            # Run for 30 seconds
            start_time = time.time()
            detections = 0
            
            while time.time() - start_time < 30:
                # Process audio
                buffer = audio.get_buffer()
                if buffer is not None:
                    features = extractor.extract(buffer)
                    if features is not None:
                        detector.detect(features)
                
                # Print a dot every second to show it's still running
                if int(time.time()) != int(start_time) and int(time.time()) % 2 == 0:
                    print(".", end="", flush=True)
                    start_time = time.time()
                
                time.sleep(0.01)
                
            # Stop audio
            audio.stop()
            
            print("\n\nTest complete!")
            
        except KeyboardInterrupt:
            print("\n\nTest interrupted by user.")
            audio.stop()
            
    else:
        print("\n❌ Wake word component tests failed. Please check the logs.")
        sys.exit(1)
