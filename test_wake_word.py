import argparse
import logging
import time
from pathlib import Path
from io_wake_word.io_wake_word import WakeWordDetector, AudioCapture

# Setup logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("WakeWordDetectorTest")

def list_audio_devices():
    """List available audio input devices."""
    audio = AudioCapture()
    devices = audio.list_devices()
    print("Available audio devices:")
    for device in devices:
        print(f"  {device['index']}: {device['name']} "
              f"(Channels: {device['channels']}, Rate: {device['sample_rate']})")

def test_wake_word_detector(model_path, device_index, threshold):
    """Test the WakeWordDetector with the given model and device."""
    
    def on_wake_word_detected(confidence):
        print(f"Wakeword detected! (confidence: {confidence:.4f})")

    logger.info(f"Loading model from {model_path}...")
    detector = WakeWordDetector(model_path=model_path, device_index=device_index, threshold=threshold)
    detector.start()
    
    # Register the callback for wake word detection
    detector.register_detection_callback(on_wake_word_detected)
    
    try:
        logger.info("Listening for wake word... Press Ctrl+C to stop.")
        while True:
            if detector.is_detected():
                print("Wakeword detected!")
            time.sleep(0.1)  # Sleep to avoid busy-waiting
    except KeyboardInterrupt:
        logger.info("Stopped by user")
    finally:
        detector.stop()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Wake Word Detector Test Script")
    parser.add_argument("--model", required=True, help="Path to model file (.pth)")
    parser.add_argument("--device", type=int, help="Audio device index (default is the system default device)")
    parser.add_argument("--threshold", type=float, default=0.85, help="Detection threshold (0.0-1.0)")
    parser.add_argument("--list-devices", action="store_true", help="List available audio devices")

    args = parser.parse_args()

    if args.list_devices:
        list_audio_devices()
    else:
        model_path = Path(args.model)
        if not model_path.exists():
            print(f"Error: Model file not found: {model_path}")
        else:
            test_wake_word_detector(model_path=model_path, device_index=args.device, threshold=args.threshold)