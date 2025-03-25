#!/usr/bin/env python3
"""
Standalone Wake Word Detector

This script provides a self-contained wake word detection system that can be integrated
into other applications. It extracts the essential components from the Io wake word
detection engine and combines them into a single, portable module.

Usage:
    # Import and use in another program
    from wake_word_detector import WakeWordDetector
    
    detector = WakeWordDetector(model_path="path/to/model.pth")
    result = detector.listen_for_wake_word(timeout=10)  # Listen for 10 seconds
    if result:
        print("Wake word detected!")
        
    # Or run directly for testing
    python wake_word_detector.py --model path/to/model.pth
"""

import os
import sys
import time
import threading
import collections
import queue
import logging
import argparse
import numpy as np
from pathlib import Path

# Set up basic logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("WakeWordDetector")

# Try importing torch - required for model inference
try:
    import torch
    import torch.nn as nn
except ImportError:
    logger.error("PyTorch is required for wake word detection.")
    logger.error("Please install with: pip install torch")
    raise

# Try importing audio processing libraries
try:
    import pyaudio
    import librosa
except ImportError:
    logger.error("Missing required libraries.")
    logger.error("Please install with: pip install pyaudio librosa")
    raise


#
# Neural Network Model Definition
#
class WakeWordModel(nn.Module):
    """CNN model for wake word detection"""
    
    def __init__(self, n_mfcc=13, num_frames=101):
        super(WakeWordModel, self).__init__()
        
        # Calculate output dimensions for fully connected layer
        # These calculations need to match exactly what the trained model used
        # For standard Io models, these values should produce a size of 1536
        after_pool1 = (num_frames - 3) // 2 + 1
        after_pool2 = (after_pool1 - 3) // 2 + 1
        self.fc_input_size = 64 * after_pool2
        
        logger.debug(f"WakeWordModel fc_input_size calculation: {self.fc_input_size}")
        logger.debug(f"Dimensions: num_frames={num_frames}, after_pool1={after_pool1}, after_pool2={after_pool2}")
        
        # Convolutional layers - matching the architecture from Io
        self.conv_layers = nn.Sequential(
            nn.Conv1d(n_mfcc, 64, kernel_size=3, stride=1, padding=1),
            nn.BatchNorm1d(64),
            nn.ReLU(),
            nn.MaxPool1d(kernel_size=3, stride=2, padding=0),
            
            nn.Conv1d(64, 64, kernel_size=3, stride=1, padding=1),
            nn.BatchNorm1d(64),
            nn.ReLU(),
            nn.MaxPool1d(kernel_size=3, stride=2, padding=0)
        )
        
        # Fully connected layers - matching the architecture from Io
        self.fc_layers = nn.Sequential(
            nn.Linear(self.fc_input_size, 128),
            nn.ReLU(),
            nn.Linear(128, 1),
            nn.Sigmoid()
        )
        
        # Counter for limiting debug logs
        self.forward_count = 0
    
    def forward(self, x):
        self.forward_count += 1
        
        x = self.conv_layers(x)
        
        # Debug log only occasionally to avoid spamming
        if self.forward_count % 100 == 0 and logger.level <= logging.DEBUG:
            logger.debug(f"Shape before flattening (count={self.forward_count}): {x.shape}")
        
        x = x.view(x.size(0), -1)
        x = self.fc_layers(x)
        return x


class SimpleWakeWordModel(nn.Module):
    """Simplified CNN model for wake word detection"""
    
    def __init__(self, n_mfcc=13, num_frames=101):
        super(SimpleWakeWordModel, self).__init__()
        
        # Simple architecture with fewer layers
        self.conv_layer = nn.Sequential(
            nn.Conv1d(n_mfcc, 32, kernel_size=3, stride=1, padding=1),
            nn.ReLU(),
            nn.MaxPool1d(kernel_size=3, stride=2, padding=0)
        )
        
        # Calculate output size - ensure this matches what was used during training
        output_width = (num_frames - 3) // 2 + 1
        self.fc_input_size = 32 * output_width
        
        logger.debug(f"SimpleWakeWordModel fc_input_size calculation: {self.fc_input_size}")
        logger.debug(f"Dimensions: num_frames={num_frames}, output_width={output_width}")
        
        self.fc_layers = nn.Sequential(
            nn.Linear(self.fc_input_size, 64),
            nn.ReLU(),
            nn.Linear(64, 1),
            nn.Sigmoid()
        )
        
        # Counter for limiting debug logs
        self.forward_count = 0
    
    def forward(self, x):
        self.forward_count += 1
        
        x = self.conv_layer(x)
        
        # Debug log only occasionally to avoid spamming
        if self.forward_count % 100 == 0 and logger.level <= logging.DEBUG:
            logger.debug(f"Shape before flattening (count={self.forward_count}): {x.shape}")
            
        x = x.view(x.size(0), -1)
        x = self.fc_layers(x)
        return x


#
# Feature Extraction
#
class FeatureExtractor:
    """Extract MFCC features from audio frames"""
    
    def __init__(self, sample_rate=16000, n_mfcc=13, n_fft=2048, hop_length=160):
        self.sample_rate = sample_rate
        self.n_mfcc = n_mfcc
        self.n_fft = n_fft
        self.hop_length = hop_length
        
        # Number of frames needed for detection
        self.num_frames = 101
        
        # Audio buffer for context
        self.audio_buffer = np.zeros(0)
        
        # Energy threshold for silence detection
        self.energy_threshold = 0.005
        
    def extract(self, audio_frame):
        """Extract MFCC features from audio frame"""
        # Add current frame to buffer
        self.audio_buffer = np.append(self.audio_buffer, audio_frame)
        
        # We need at least 1 second of audio
        min_samples = self.sample_rate + len(audio_frame)
        
        if len(self.audio_buffer) < min_samples:
            return None
            
        # Keep only the most recent audio
        if len(self.audio_buffer) > min_samples * 1.2:
            self.audio_buffer = self.audio_buffer[-min_samples:]
        
        # Check if audio is silent
        energy = np.mean(self.audio_buffer**2)
        if energy < self.energy_threshold:
            return None  # Don't process silent audio
        
        try:
            # Calculate MFCCs
            mfccs = librosa.feature.mfcc(
                y=self.audio_buffer, 
                sr=self.sample_rate,
                n_mfcc=self.n_mfcc,
                n_fft=self.n_fft,
                hop_length=self.hop_length
            )
            
            # Ensure consistent length
            if mfccs.shape[1] < self.num_frames:
                # Pad if too short
                pad_width = self.num_frames - mfccs.shape[1]
                mfccs = np.pad(mfccs, ((0, 0), (0, pad_width)))
            elif mfccs.shape[1] > self.num_frames:
                # Truncate if too long
                mfccs = mfccs[:, -self.num_frames:]
            
            # Apply normalization (feature-wise)
            for i in range(mfccs.shape[0]):
                feature_mean = np.mean(mfccs[i])
                feature_std = np.std(mfccs[i])
                if feature_std > 1e-6:  # Prevent division by zero
                    mfccs[i] = (mfccs[i] - feature_mean) / feature_std
            
            # Reshape for the model [batch, channels, features, time]
            features = np.expand_dims(mfccs, axis=0)
            
            return features
            
        except Exception as e:
            logger.error(f"Error extracting features: {e}")
            return None
    
    def clear_buffer(self):
        """Clear the audio buffer"""
        self.audio_buffer = np.zeros(0)


#
# Audio Capture
#
class AudioCapture:
    """Thread-safe audio capture with PyAudio"""
    
    def __init__(self, device_index=None, sample_rate=16000, frame_size=512, callback=None):
        self.device_index = device_index
        self.sample_rate = sample_rate
        self.frame_size = frame_size
        self.callback = callback
        self.stream = None
        self.pyaudio = None
        self.is_running = False
        
        # Create circular buffer (2 seconds of audio)
        buffer_frames = int(2 * sample_rate / frame_size)
        self.buffer = collections.deque(maxlen=buffer_frames)
        
        # Lock for thread safety
        self.lock = threading.Lock()
    
    def list_devices(self):
        """List available audio input devices"""
        try:
            p = pyaudio.PyAudio()
            devices = []
            
            for i in range(p.get_device_count()):
                device_info = p.get_device_info_by_index(i)
                if device_info["maxInputChannels"] > 0:
                    devices.append({
                        "index": i,
                        "name": device_info["name"],
                        "channels": device_info["maxInputChannels"],
                        "sample_rate": int(device_info["defaultSampleRate"])
                    })
            
            p.terminate()
            return devices
        except Exception as e:
            logger.error(f"Error listing audio devices: {e}")
            return []
    
    def _audio_callback(self, in_data, frame_count, time_info, status):
        """PyAudio callback function for streaming audio data"""
        if status:
            logger.warning(f"Audio callback status: {status}")
        
        try:
            # Convert bytes to numpy array (16-bit audio)
            audio_data = np.frombuffer(in_data, dtype=np.int16).astype(np.float32)
            
            # Normalize to [-1.0, 1.0]
            audio_data = audio_data / 32768.0
            
            # Apply automatic gain control (simple normalization)
            if np.abs(audio_data).max() > 0:
                audio_data = audio_data / np.abs(audio_data).max() * 0.9
            
            # Add to buffer with thread safety
            with self.lock:
                self.buffer.append(audio_data)
            
            # Process the audio if callback is set
            if self.callback:
                self.callback(audio_data)
        except Exception as e:
            logger.error(f"Error in audio callback: {e}")
        
        # Continue the stream
        return (None, pyaudio.paContinue)
    
    def start(self):
        """Start audio capture with proper resource management"""
        if self.is_running:
            return
        
        try:
            self.pyaudio = pyaudio.PyAudio()
            
            # If no device index specified, use default
            if self.device_index is None:
                try:
                    self.device_index = self.pyaudio.get_default_input_device_info()["index"]
                    logger.info(f"Using default audio device with index {self.device_index}")
                except Exception as e:
                    logger.error(f"Could not get default device: {e}. Using device 0.")
                    self.device_index = 0
            
            # Open audio stream in callback mode
            self.stream = self.pyaudio.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=self.sample_rate,
                input=True,
                input_device_index=self.device_index,
                frames_per_buffer=self.frame_size,
                stream_callback=self._audio_callback
            )
            
            self.is_running = True
            logger.info(f"Audio capture started on device {self.device_index}")
        except Exception as e:
            logger.error(f"Error starting audio capture: {e}")
            self._cleanup_resources()
    
    def stop(self):
        """Stop audio capture with proper resource cleanup"""
        if not self.is_running:
            return
        
        self.is_running = False
        self._cleanup_resources()
        logger.info("Audio capture stopped")
    
    def _cleanup_resources(self):
        """Clean up PyAudio resources properly"""
        try:
            if self.stream:
                if self.stream.is_active():
                    self.stream.stop_stream()
                self.stream.close()
                self.stream = None
        except Exception as e:
            logger.error(f"Error closing stream: {e}")
        
        try:
            if self.pyaudio:
                self.pyaudio.terminate()
                self.pyaudio = None
        except Exception as e:
            logger.error(f"Error terminating PyAudio: {e}")
    
    def get_buffer(self):
        """Get the current audio buffer (thread-safe)"""
        with self.lock:
            # Convert deque to numpy array
            if len(self.buffer) > 0:
                return np.concatenate(list(self.buffer))
            else:
                return np.array([], dtype=np.float32)
    
    def __del__(self):
        """Destructor to ensure resources are released"""
        self.stop()


#
# Wake Word Detector
#
class WakeWordDetector:
    """
    Self-contained wake word detector that can be integrated into other applications.
    
    This class combines audio capture, feature extraction, and model inference to 
    provide a complete wake word detection solution.
    """
    
    def __init__(self, model_path='jupiter-wake-word.pth', threshold=0.85, device_index=None, sample_rate=16000):
        """
        Initialize the wake word detector.
        
        Args:
            model_path: Path to the wake word model (.pth file)
            threshold: Detection threshold (0.0-1.0, higher values reduce false positives)
            device_index: Audio device index (None for default)
            sample_rate: Audio sample rate (default 16000 Hz)
        """
        self.model_path = model_path
        self.threshold = threshold
        self.device_index = device_index
        self.sample_rate = sample_rate
        
        # Detection state
        self.detected = False
        self.detection_lock = threading.Lock()
        
        # Detection debouncing
        self.last_detection_time = 0
        self.detection_cooldown = 2.0  # seconds
        
        # Recent predictions for smoothing
        self.recent_predictions = collections.deque(maxlen=5)
        
        # Consecutive high confidence counter
        self.high_confidence_streak = 0
        self.required_streak = 2
        
        # Callbacks
        self.detection_callbacks = []
        
        # Load model
        self.model = self._load_model(model_path)
        
        # Create feature extractor
        self.feature_extractor = FeatureExtractor(sample_rate=sample_rate)
        
        # Processing components
        self.audio_queue = queue.Queue(100)  # Queue doesn't accept maxlen, just size
        self.processing_thread = None
        self.is_running = False
    
    def _load_model(self, model_path):
        """Load the wake word model from file"""
        if not model_path:
            logger.warning("No model path provided. Detection will not work.")
            return None
            
        model_path = Path(model_path)
        if not model_path.exists():
            logger.error(f"Model file not found: {model_path}")
            return None
            
        try:
            # Load state dictionary to check architecture
            state_dict = torch.load(model_path, map_location=torch.device('cpu'))
            
            # Try to identify model architecture more reliably
            is_simple_model = any('conv_layer' in key for key in state_dict.keys())
            has_conv_layers = any('conv_layers.0.weight' in key for key in state_dict.keys())
            
            # Try both models if architecture is unclear
            model = None
            
            # First try with the model we think it is
            try:
                if is_simple_model:
                    logger.info("Trying SimpleWakeWordModel architecture")
                    model = SimpleWakeWordModel(n_mfcc=13, num_frames=101)
                    model.load_state_dict(state_dict)
                elif has_conv_layers:
                    logger.info("Trying WakeWordModel architecture")
                    model = WakeWordModel(n_mfcc=13, num_frames=101)
                    model.load_state_dict(state_dict)
                else:
                    # Default to standard model if we can't tell
                    logger.info("Unable to determine model type, trying WakeWordModel")
                    model = WakeWordModel(n_mfcc=13, num_frames=101)
                    model.load_state_dict(state_dict)
            except Exception as first_error:
                logger.warning(f"First model loading attempt failed: {first_error}")
                # Try the other model
                try:
                    if is_simple_model or not has_conv_layers:
                        logger.info("Trying WakeWordModel as fallback")
                        model = WakeWordModel(n_mfcc=13, num_frames=101)
                        model.load_state_dict(state_dict)
                    else:
                        logger.info("Trying SimpleWakeWordModel as fallback")
                        model = SimpleWakeWordModel(n_mfcc=13, num_frames=101)
                        model.load_state_dict(state_dict)
                except Exception as second_error:
                    logger.error(f"Both model architectures failed. First error: {first_error}, Second error: {second_error}")
                    return None
            
            if model is not None:
                # Set to evaluation mode
                model.eval()
                logger.info(f"Model loaded successfully from {model_path}")
                return model
            else:
                logger.error("Failed to load model with either architecture")
                return None
                
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            return None
            
    def register_detection_callback(self, callback):
        """
        Register a function to be called when the wake word is detected.
        
        The callback function should accept a single argument: confidence (float).
        """
        if callable(callback) and callback not in self.detection_callbacks:
            self.detection_callbacks.append(callback)
            return True
        return False
    
    def _audio_callback(self, audio_frame):
        """Callback function for audio capture"""
        if self.is_running:
            try:
                # Use non-blocking put with timeout to avoid deadlocks
                self.audio_queue.put(audio_frame, block=True, timeout=0.1)
            except queue.Full:
                # Queue is full, drop the frame
                pass
    
    def _processing_loop(self):
        """Main audio processing loop"""
        logger.info("Audio processing thread started")
        
        # For logging management
        processed_frames = 0
        last_log_time = time.time()
        log_interval = 5.0  # seconds
        
        while self.is_running:
            try:
                # Get audio frame from queue with timeout
                audio_frame = self.audio_queue.get(block=True, timeout=0.1)
                
                # Extract features
                features = self.feature_extractor.extract(audio_frame)
                
                # Detect wake word if features were extracted
                if features is not None:
                    processed_frames += 1
                    detection, confidence = self._detect(features)
                    
                    # Update detection state
                    if detection:
                        with self.detection_lock:
                            self.detected = True
                
                # Log processing stats periodically
                current_time = time.time()
                if current_time - last_log_time > log_interval:
                    if logger.level <= logging.DEBUG:
                        logger.debug(f"Processed {processed_frames} frames in the last {log_interval:.1f}s")
                    last_log_time = current_time
                    processed_frames = 0
                    
            except queue.Empty:
                # Timeout waiting for audio, just continue
                pass
            except Exception as e:
                logger.error(f"Error in audio processing: {e}")
                time.sleep(0.1)  # Avoid CPU spinning on repeated errors
        
        logger.info("Audio processing thread stopped")
    
    def _detect(self, features):
        """Detect wake word in audio features"""
        if self.model is None:
            return False, 0.0
            
        # Convert to tensor if it's a numpy array
        if isinstance(features, np.ndarray):
            features = torch.from_numpy(features).float()
        
        try:
            # Run inference
            with torch.no_grad():
                outputs = self.model(features)
                confidence = outputs.item()
            
            # Process high confidence scores
            if confidence > self.threshold:
                self.high_confidence_streak += 1
            else:
                self.high_confidence_streak = 0
            
            # Add to recent predictions
            current_time = time.time()
            self.recent_predictions.append((confidence, current_time))
            
            # Process predictions with smoothing
            if len(self.recent_predictions) >= 3:
                recent_confidences = [c for c, _ in self.recent_predictions]
                avg_confidence = sum(recent_confidences) / len(recent_confidences)
                
                # Count high confidence predictions
                high_conf_count = sum(1 for conf, _ in self.recent_predictions if conf > self.threshold)
                
                # Check debounce time
                time_since_last = current_time - self.last_detection_time
                can_trigger = time_since_last > self.detection_cooldown
                
                # Final detection decision
                is_detected = (
                    avg_confidence > self.threshold and
                    high_conf_count >= min(3, len(self.recent_predictions)) and
                    self.high_confidence_streak >= self.required_streak and
                    can_trigger
                )
                
                # If detected, trigger callbacks
                if is_detected:
                    logger.info(f"Wake word detected with confidence: {avg_confidence:.4f}")
                    
                    # Update detection time
                    self.last_detection_time = current_time
                    self.high_confidence_streak = 0
                    
                    # Update detection state
                    with self.detection_lock:
                        self.detected = True
                    
                    # Call callbacks
                    for callback in self.detection_callbacks:
                        try:
                            callback(avg_confidence)
                        except Exception as e:
                            logger.error(f"Error in detection callback: {e}")
                
                return is_detected, avg_confidence
            
            return False, confidence
                
        except Exception as e:
            logger.error(f"Error during inference: {e}")
            return False, 0.0
    
    def start(self):
        """Start listening for the wake word"""
        if self.is_running:
            return
            
        # Reset detection state
        with self.detection_lock:
            self.detected = False
        
        # Start processing thread
        self.is_running = True
        self.processing_thread = threading.Thread(target=self._processing_loop)
        self.processing_thread.daemon = True
        self.processing_thread.start()
        
        # Create and start audio capture
        self.audio_capture = AudioCapture(
            device_index=self.device_index,
            sample_rate=self.sample_rate,
            callback=self._audio_callback
        )
        self.audio_capture.start()
        
        logger.info("Wake word detector started")
    
    def stop(self):
        """Stop listening for the wake word"""
        if not self.is_running:
            return
            
        # Stop processing
        self.is_running = False
        
        # Stop audio capture
        if hasattr(self, 'audio_capture'):
            self.audio_capture.stop()
        
        # Wait for processing thread to finish
        if self.processing_thread:
            self.processing_thread.join(timeout=2.0)
            self.processing_thread = None
        
        # Clear the queue
        while not self.audio_queue.empty():
            try:
                self.audio_queue.get_nowait()
            except queue.Empty:
                break
                
        logger.info("Wake word detector stopped")
    
    def listen_for_wake_word(self, timeout=None, continuous=False, on_detect=None):
        """
        Listen for the wake word and return when detected or timeout.
        
        Args:
            timeout: Maximum time to listen in seconds (None for indefinite)
            continuous: If True, continue listening after wake word is detected
            on_detect: Callback function to call when wake word is detected
            
        Returns:
            True if wake word detected, False if timeout or error
        """
        # Register callback for continuous mode
        if continuous and on_detect and callable(on_detect):
            self.register_detection_callback(on_detect)
        
        # Start if not already running
        was_running = self.is_running
        if not was_running:
            self.start()
        
        try:
            # Wait for detection or timeout
            start_time = time.time()
            detected_once = False
            last_detection_time = 0  # Track when we last handled a detection
            
            while True:
                # Check for detection
                with self.detection_lock:
                    if self.detected:
                        detected_once = True
                        current_time = time.time()
                        
                        # Only handle the detection if we haven't recently
                        if current_time - last_detection_time > 1.0:  # 1 second debounce
                            last_detection_time = current_time
                            
                            # If not continuous, stop here
                            if not continuous:
                                # Print directly for single detection mode
                                print("Test success")
                                return True
                            
                            # For continuous mode, the callback handles printing
                            # Don't reset the flag, that's for the main thread to handle
                            # The detector's internal debounce will prevent rapid re-detection
                        
                        # Always reset the flag even if we didn't handle it
                        # This prevents accumulating unhandled detections
                        self.detected = False
                        
                        # If continuous, reset start time for timeout
                        start_time = current_time
                
                # Check for timeout
                if timeout and time.time() - start_time > timeout:
                    logger.info(f"Listening timeout after {timeout} seconds")
                    return detected_once
                
                # Sleep to avoid CPU spinning
                time.sleep(0.1)
                
        finally:
            # Stop if we started in this method and not continuous
            if not was_running and not continuous:
                self.stop()


def main():
    """Main function for command-line usage"""
    parser = argparse.ArgumentParser(description="Standalone Wake Word Detector")
    parser.add_argument("--model", required=True, help="Path to the wake word model file (.pth)")
    parser.add_argument("--threshold", type=float, default=0.85, help="Detection threshold (0.0-1.0)")
    parser.add_argument("--device", type=int, help="Audio device index (optional)")
    parser.add_argument("--list-devices", action="store_true", help="List available audio devices")
    parser.add_argument("--timeout", type=float, help="Maximum listening time in seconds")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--continuous", action="store_true", help="Continue listening after wake word detection")
    
    args = parser.parse_args()
    
    # Set debug logging if requested
    if args.debug:
        logger.setLevel(logging.DEBUG)
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("Debug logging enabled")
    
    # List devices if requested
    if args.list_devices:
        audio = AudioCapture()
        devices = audio.list_devices()
        print("Available audio devices:")
        for device in devices:
            print(f"  {device['index']}: {device['name']} "
                  f"(Channels: {device['channels']}, Rate: {device['sample_rate']})")
        return
    
    # Check if model exists
    model_path = Path(args.model)
    if not model_path.exists():
        print(f"Error: Model file not found: {model_path}")
        return
    
    try:
        # Create detector
        print(f"Loading model from {args.model}...")
        detector = WakeWordDetector(
            model_path=args.model,
            threshold=args.threshold,
            device_index=args.device
        )
        
        # Check if model loaded successfully
        if detector.model is None:
            print("Error: Failed to load model. Check logs for details.")
            return
        
        # Define callback for continuous mode
        def on_wake_word_detected(confidence):
            print(f"\nWake word detected! (confidence: {confidence:.4f})")
            print("Test success")
            print("Listening for next wake word...")
            
        print(f"Listening for wake word... (threshold: {args.threshold}, "
              f"timeout: {args.timeout if args.timeout else 'none'}, "
              f"mode: {'continuous' if args.continuous else 'single detection'})")
        print("Press Ctrl+C to stop")
        
        # Listen indefinitely or until timeout
        result = detector.listen_for_wake_word(
            timeout=args.timeout,
            continuous=args.continuous,
            on_detect=on_wake_word_detected if args.continuous else None
        )
        
        if args.continuous:
            # In continuous mode, we only get here on timeout
            if result:
                print("Listening ended (timeout, wake word was detected at least once)")
            else:
                print("No wake word detected (timeout)")
        else:
            # In single detection mode, we handled the "Test success" print in the listen_for_wake_word method
            if result:
                print("Wake word detected!")
            else:
                print("No wake word detected (timeout)")
            
    except KeyboardInterrupt:
        print("\nStopped by user")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if 'detector' in locals() and detector is not None:
            detector.stop()


if __name__ == "__main__":
    main()