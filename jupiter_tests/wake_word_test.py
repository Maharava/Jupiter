"""
Test script for Jupiter wake word detection
Run this script to test whether the wake word detector is working properly
"""
import os
import sys
import time
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import wake word detector from io_wake_word
try:
    from io_wake_word.io_wake_word import WakeWordDetector
    WAKE_WORD_AVAILABLE = True
except ImportError:
    WAKE_WORD_AVAILABLE = False
    print("Error: io_wake_word module not found. Make sure the io_wake_word directory is in your Python path.")
    sys.exit(1)

def on_wake_word_detected(confidence):
    """Callback for when wake word is detected"""
    print(f"\n🎤 Wake word detected! (confidence: {confidence:.4f})")
    print("Jupiter would now be listening for a command...")
    print("\nListening for next wake word...\n")

def main():
    """Main test function"""
    print("Jupiter Wake Word Detection Test")
    print("--------------------------------")
    
    # Default model path
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    model_path = os.path.join(base_dir, "models", "jupiter-wake-word.pth")
    
    # Check if model exists
    if not os.path.exists(model_path):
        print(f"❌ Wake word model not found at: {model_path}")
        return
    
    print(f"✓ Found wake word model at: {model_path}")
    
    try:
        # Create wake word detector
        detector = WakeWordDetector(model_path=model_path, threshold=0.85)
        
        # Register detection callback
        detector.register_detection_callback(on_wake_word_detected)
        
        print("\nStarting wake word detection...")
        detector.start()
        
        print("✓ Wake word detector started")
        print("\n🎤 Say 'Hey Jupiter' to trigger the wake word detector")
        print("\nPress Ctrl+C to exit")
        
        # Use the built-in listen_for_wake_word method with continuous mode
        detector.listen_for_wake_word(timeout=None, continuous=True)
        
    except KeyboardInterrupt:
        print("\nStopping wake word detector...")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        if 'detector' in locals():
            detector.stop()
        print("Wake word detector stopped")

if __name__ == "__main__":
    main()