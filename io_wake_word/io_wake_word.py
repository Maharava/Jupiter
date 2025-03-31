#!/usr/bin/env python3
"""
Wake Word Detector

A simple, efficient wake word detection system designed for easy integration.
Can be used as a standalone module or imported into other applications.

Usage:
    # Import into another program
    from wake_word_detector import WakeWordDetector
    
    detector = WakeWordDetector(model_path="path/to/model.pth")
    detector.start()
    
    # Check for wake word in a non-blocking way
    if detector.is_detected():
        print("Wake word detected!")
    
    # Or use the blocking method
    if detector.listen_for_wake_word(timeout=5):
        print("Wake word detected within 5 seconds!")
    
    detector.stop()
        
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

# Setup logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("WakeWordDetector")

# Import required dependencies
try:
    import torch
    import torch.nn as nn
    import pyaudio
    import librosa
except ImportError as e:
    logger.error(f"Missing dependency: {e}")
    logger.error("Install requirements with: pip install torch pyaudio librosa")
    raise


class WakeWordModel(nn.Module):
    """CNN model for wake word detection"""
    
    def __init__(self, n_mfcc=13, num_frames=101):
        super(WakeWordModel, self).__init__()
        
        # Calculate dimensions for fully connected layer
        after_pool1 = (num_frames - 3) // 2 + 1
        after_pool2 = (after_pool1 - 3) // 2 + 1
        fc_input_size = 64 * after_pool2
        
        # Convolutional layers
        self.conv_layers = nn.Sequential(
            # First conv block
            nn.Conv1d(n_mfcc, 64, kernel_size=3, stride=1, padding=1),
            nn.BatchNorm1d(64),
            nn.ReLU(),
            nn.MaxPool1d(kernel_size=3, stride=2, padding=0),
            
            # Second conv block
            nn.Conv1d(64, 64, kernel_size=3, stride=1, padding=1),
            nn.BatchNorm1d(64),
            nn.ReLU(),
            nn.MaxPool1d(kernel_size=3, stride=2, padding=0)
        )
        
        # Fully connected layers
        self.fc_layers = nn.Sequential(
            nn.Linear(fc_input_size, 128),
            nn.ReLU(),
            nn.Linear(128, 1),
            nn.Sigmoid()
        )
    
    def forward(self, x):
        x = self.conv_layers(x)
        x = x.view(x.size(0), -1)  # Flatten
        x = self.fc_layers(x)
        return x


class FeatureExtractor:
    """Extracts MFCC features from audio frames"""
    
    def __init__(self, sample_rate=16000, n_mfcc=13):
        self.sample_rate = sample_rate
        self.n_mfcc = n_mfcc
        self.n_fft = 2048
        self.hop_length = 160
        self.num_frames = 101
        self.audio_buffer = np.zeros(0)
        self.energy_threshold = 0.005
    
    def extract(self, audio_frame):
        """Process audio frame and extract MFCC features"""
        # Add current frame to buffer
        self.audio_buffer = np.append(self.audio_buffer, audio_frame)
        
        # Need at least 1 second of audio
        min_samples = self.sample_rate + len(audio_frame)
        if len(self.audio_buffer) < min_samples:
            return None
        
        # Keep only recent audio
        if len(self.audio_buffer) > min_samples * 1.2:
            self.audio_buffer = self.audio_buffer[-min_samples:]
        
        # Skip silent audio
        energy = np.mean(self.audio_buffer**2)
        if energy < self.energy_threshold:
            return None
        
        try:
            # Extract MFCCs
            mfccs = librosa.feature.mfcc(
                y=self.audio_buffer,
                sr=self.sample_rate,
                n_mfcc=self.n_mfcc,
                n_fft=self.n_fft,
                hop_length=self.hop_length
            )
            
            # Ensure consistent size
            if mfccs.shape[1] < self.num_frames:
                # Pad if too short
                pad_width = self.num_frames - mfccs.shape[1]
                mfccs = np.pad(mfccs, ((0, 0), (0, pad_width)))
            elif mfccs.shape[1] > self.num_frames:
                # Truncate if too long
                mfccs = mfccs[:, -self.num_frames:]
            
            # Normalize features
            for i in range(mfccs.shape[0]):
                feature_mean = np.mean(mfccs[i])
                feature_std = np.std(mfccs[i])
                if feature_std > 1e-6:  # Avoid division by zero
                    mfccs[i] = (mfccs[i] - feature_mean) / feature_std
            
            # Format for model input
            features = np.expand_dims(mfccs, axis=0)
            return features
            
        except Exception as e:
            logger.error(f"Feature extraction error: {e}")
            return None
    
    def clear_buffer(self):
        """Reset the audio buffer"""
        self.audio_buffer = np.zeros(0)


class AudioCapture:
    """Captures audio from microphone"""
    
    def __init__(self, device_index=None, sample_rate=16000, frame_size=512, callback=None):
        self.device_index = device_index
        self.sample_rate = sample_rate
        self.frame_size = frame_size
        self.callback = callback
        self.stream = None
        self.pyaudio = None
        self.is_running = False
        
        # Circular buffer for audio storage (2 seconds)
        buffer_frames = int(2 * sample_rate / frame_size)
        self.buffer = collections.deque(maxlen=buffer_frames)
        self.lock = threading.Lock()
    
    def list_devices(self):
        """List available audio input devices"""
        devices = []
        try:
            p = pyaudio.PyAudio()
            for i in range(p.get_device_count()):
                info = p.get_device_info_by_index(i)
                if info["maxInputChannels"] > 0:
                    devices.append({
                        "index": i,
                        "name": info["name"],
                        "channels": info["maxInputChannels"],
                        "sample_rate": int(info["defaultSampleRate"])
                    })
            p.terminate()
        except Exception as e:
            logger.error(f"Error listing devices: {e}")
        return devices
    
    def _audio_callback(self, in_data, frame_count, time_info, status):
        """PyAudio callback for processing incoming audio"""
        if status:
            logger.warning(f"Audio status: {status}")
        
        try:
            # Convert bytes to normalized float array
            audio_data = np.frombuffer(in_data, dtype=np.int16).astype(np.float32) / 32768.0
            
            # Simple automatic gain control
            if np.abs(audio_data).max() > 0:
                audio_data = audio_data / np.abs(audio_data).max() * 0.9
            
            # Store in buffer (thread-safe)
            with self.lock:
                self.buffer.append(audio_data)
            
            # Process with callback if provided
            if self.callback:
                self.callback(audio_data)
        except Exception as e:
            logger.error(f"Audio callback error: {e}")
        
        return (None, pyaudio.paContinue)
    
    def start(self):
        """Start audio capture"""
        if self.is_running:
            return
        
        try:
            self.pyaudio = pyaudio.PyAudio()
            
            # Get default device if not specified
            if self.device_index is None:
                try:
                    self.device_index = self.pyaudio.get_default_input_device_info()["index"]
                except Exception:
                    logger.warning("Could not get default device. Using device 0.")
                    self.device_index = 0
            
            # Open audio stream
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
            logger.info(f"Audio capture started (device: {self.device_index})")
        except Exception as e:
            logger.error(f"Error starting audio: {e}")
            self._cleanup()
    
    def stop(self):
        """Stop audio capture"""
        if not self.is_running:
            return
        
        self.is_running = False
        self._cleanup()
    
    def _cleanup(self):
        """Clean up audio resources"""
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
        """Get current audio buffer (thread-safe)"""
        with self.lock:
            if len(self.buffer) > 0:
                return np.concatenate(list(self.buffer))
            else:
                return np.array([], dtype=np.float32)
    
    def __del__(self):
        """Ensure resources are cleaned up"""
        self.stop()


class WakeWordDetector:
    """
    Main wake word detector class for integration into other applications.
    """
    
    def __init__(self, model_path=None, threshold=0.85, device_index=None, sample_rate=16000):
        self.model_path = model_path
        self.threshold = threshold
        self.device_index = device_index
        self.sample_rate = sample_rate
        
        # Detection state
        self.detected = False
        self.detection_lock = threading.Lock()
        self.last_detection_time = 0
        self.detection_cooldown = 2.0  # seconds
        
        # Detection smoothing
        self.recent_predictions = collections.deque(maxlen=5)
        self.high_confidence_streak = 0
        self.required_streak = 2
        
        # Callbacks for detection events
        self.detection_callbacks = []
        
        # Initialize components
        self.model = self._load_model(model_path)
        self.feature_extractor = FeatureExtractor(sample_rate=sample_rate)
        self.audio_queue = queue.Queue(100)
        self.processing_thread = None
        self.is_running = False
    
    def _load_model(self, model_path):
        """Load PyTorch model from file"""
        if not model_path:
            logger.warning("No model path provided")
            return None
        
        model_path = Path(model_path)
        if not model_path.exists():
            logger.error(f"Model not found: {model_path}")
            return None
        
        try:
            # Load the model
            state_dict = torch.load(model_path, map_location=torch.device('cpu'))
            model = WakeWordModel(n_mfcc=13, num_frames=101)
            model.load_state_dict(state_dict)
            model.eval()  # Set to evaluation mode
            logger.info(f"Model loaded from {model_path}")
            return model
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            return None
    
    def register_detection_callback(self, callback):
        """Register a function to call when wake word is detected"""
        if callable(callback) and callback not in self.detection_callbacks:
            self.detection_callbacks.append(callback)
            return True
        return False
    
    def _audio_callback(self, audio_frame):
        """Handle incoming audio frames"""
        if self.is_running:
            try:
                # Add to processing queue
                self.audio_queue.put(audio_frame, block=True, timeout=0.1)
            except queue.Full:
                pass  # Drop frame if queue is full
    
    def _processing_loop(self):
        """Main audio processing thread"""
        logger.info("Processing thread started")
        
        while self.is_running:
            try:
                # Get audio frame from queue
                audio_frame = self.audio_queue.get(block=True, timeout=0.1)
                
                # Extract features
                features = self.feature_extractor.extract(audio_frame)
                
                # Detect wake word if features available
                if features is not None:
                    detection, confidence = self._detect(features)
                    
                    # Update detection state
                    if detection:
                        with self.detection_lock:
                            self.detected = True
                    
            except queue.Empty:
                pass  # No audio available
            except Exception as e:
                logger.error(f"Processing error: {e}")
                time.sleep(0.1)  # Avoid tight loop on error
        
        logger.info("Processing thread stopped")
    
    def _detect(self, features):
        """Run detection on features"""
        if self.model is None:
            return False, 0.0
        
        # Convert to tensor if needed
        if isinstance(features, np.ndarray):
            features = torch.from_numpy(features).float()
        
        try:
            # Run inference
            with torch.no_grad():
                outputs = self.model(features)
                confidence = outputs.item()
            
            # Update confidence streak
            if confidence > self.threshold:
                self.high_confidence_streak += 1
            else:
                self.high_confidence_streak = 0
            
            # Add to recent predictions
            current_time = time.time()
            self.recent_predictions.append((confidence, current_time))
            
            # Process with smoothing when we have enough data
            if len(self.recent_predictions) >= 3:
                # Calculate average confidence
                recent_confidences = [c for c, _ in self.recent_predictions]
                avg_confidence = sum(recent_confidences) / len(recent_confidences)
                
                # Count high confidence predictions
                high_conf_count = sum(1 for conf, _ in self.recent_predictions if conf > self.threshold)
                
                # Check if we can trigger (cooldown period)
                time_since_last = current_time - self.last_detection_time
                can_trigger = time_since_last > self.detection_cooldown
                
                # Final detection decision
                is_detected = (
                    avg_confidence > self.threshold and
                    high_conf_count >= min(3, len(self.recent_predictions)) and
                    self.high_confidence_streak >= self.required_streak and
                    can_trigger
                )
                
                # Handle detection
                if is_detected:
                    logger.info(f"Wake word detected (confidence: {avg_confidence:.4f})")
                    
                    # Update detection time
                    self.last_detection_time = current_time
                    self.high_confidence_streak = 0
                    
                    # Set detection flag
                    with self.detection_lock:
                        self.detected = True
                    
                    # Call all registered callbacks
                    for callback in self.detection_callbacks:
                        try:
                            callback(avg_confidence)
                        except Exception as e:
                            logger.error(f"Callback error: {e}")
                
                return is_detected, avg_confidence
            
            return False, confidence
                
        except Exception as e:
            logger.error(f"Detection error: {e}")
            return False, 0.0
    
    def start(self):
        """Start wake word detection"""
        if self.is_running:
            return
        
        # Reset state
        with self.detection_lock:
            self.detected = False
        
        # Start processing thread
        self.is_running = True
        self.processing_thread = threading.Thread(target=self._processing_loop)
        self.processing_thread.daemon = True
        self.processing_thread.start()
        
        # Start audio capture
        self.audio_capture = AudioCapture(
            device_index=self.device_index,
            sample_rate=self.sample_rate,
            callback=self._audio_callback
        )
        self.audio_capture.start()
        
        logger.info("Wake word detector started")
    
    def stop(self):
        """Stop wake word detection"""
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
        
        # Clear audio queue
        while not self.audio_queue.empty():
            try:
                self.audio_queue.get_nowait()
            except queue.Empty:
                break
                
        logger.info("Wake word detector stopped")
    
    def is_detected(self):
        """Check if wake word has been detected (non-blocking)"""
        with self.detection_lock:
            detected = self.detected
            if detected:
                self.detected = False
            return detected
    
    def listen_for_wake_word(self, timeout=None, continuous=False, on_detect=None):
        """
        Listen for wake word and return when detected or timeout.
        
        Args:
            timeout: Maximum listening time in seconds (None for indefinite)
            continuous: Continue listening after detection if True
            on_detect: Callback for detections in continuous mode
            
        Returns:
            True if wake word detected, False on timeout
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
            
            while True:
                # Check for detection
                if self.is_detected():
                    detected_once = True
                    
                    # Handle detection
                    if not continuous:
                        return True
                    
                    # Reset timeout for continuous mode
                    start_time = time.time()
                
                # Check for timeout
                if timeout and time.time() - start_time > timeout:
                    logger.info(f"Listening timeout after {timeout} seconds")
                    return detected_once
                
                # Sleep to avoid CPU spinning
                time.sleep(0.1)
                
        finally:
            # Stop if we started in this method and not in continuous mode
            if not was_running and not continuous:
                self.stop()


def main():
    """Command-line interface"""
    parser = argparse.ArgumentParser(description="Wake Word Detector")
    parser.add_argument("--model", required=True, help="Path to model file (.pth)")
    parser.add_argument("--threshold", type=float, default=0.85, help="Detection threshold (0.0-1.0)")
    parser.add_argument("--device", type=int, help="Audio device index")
    parser.add_argument("--list-devices", action="store_true", help="List audio devices")
    parser.add_argument("--timeout", type=float, help="Maximum listening time in seconds")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--continuous", action="store_true", help="Continue listening after detection")
    
    args = parser.parse_args()
    
    # Set debug logging if requested
    if args.debug:
        logger.setLevel(logging.DEBUG)
        logging.getLogger().setLevel(logging.DEBUG)
    
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
        
        # Check if model loaded
        if detector.model is None:
            print("Error: Failed to load model.")
            return
        
        # Define callback for continuous mode
        def on_wake_word_detected(confidence):
            print(f"\nWake word detected! (confidence: {confidence:.4f})")
            print("Listening for next wake word...")
            
        print(f"Listening for wake word... (threshold: {args.threshold}, "
              f"timeout: {args.timeout if args.timeout else 'none'}, "
              f"mode: {'continuous' if args.continuous else 'single detection'})")
        print("Press Ctrl+C to stop")
        
        # Listen for wake word
        result = detector.listen_for_wake_word(
            timeout=args.timeout,
            continuous=args.continuous,
            on_detect=on_wake_word_detected if args.continuous else None
        )
        
        if args.continuous:
            # In continuous mode
            if result:
                print("Listening ended (timeout, wake word was detected at least once)")
            else:
                print("No wake word detected (timeout)")
        else:
            # In single detection mode
            if not result:
                print("No wake word detected (timeout)")
            
    except KeyboardInterrupt:
        print("\nStopped by user")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if 'detector' in locals() and detector is not None:
            detector.stop()


if __name__ == "__main__":
    main()