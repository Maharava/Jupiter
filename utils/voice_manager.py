import threading
import time
import queue
import logging
from enum import Enum, auto
import os

try:
    from io_wake_word.audio import AudioCapture
    from io_wake_word.models import WakeWordDetector
    WAKE_WORD_AVAILABLE = True
except ImportError:
    WAKE_WORD_AVAILABLE = False
    logging.getLogger("jupiter.voice").warning("io_wake_word package not available - voice features will be limited")

from utils.whisper_stt import listen_and_transcribe
from utils.piper import llm_speak

# Set up logging
logger = logging.getLogger("jupiter.voice")

class VoiceState(Enum):
    """States for the voice interaction state machine"""
    INACTIVE = auto()  # Voice features disabled
    LISTENING = auto()  # Wake word detection active
    FOCUSING = auto()   # STT active, waiting for speech
    PROCESSING = auto() # Processing captured speech
    SPEAKING = auto()   # Jupiter is speaking

class VoiceManager:
    """Manages voice interaction for Jupiter"""
    
    def __init__(self, chat_engine, ui, model_path=None, enabled=True):
        """Initialize voice manager"""
        self.chat_engine = chat_engine
        self.ui = ui
        self.model_path = None
        self.enabled = enabled
        self.debug_mode = False  # Enable for more detailed logging
        
        # Store original model path for troubleshooting
        self.original_model_path = model_path
        
        # Try to find the wake word model
        if model_path:
            self._find_model(model_path)
        
        # Initialize state
        self.state = VoiceState.INACTIVE
        self.state_lock = threading.Lock()
        self.running = False
        
        # For speech detection status tracking
        self.speech_detected = False
        self.last_speech_time = 0
        
        # Initialize components
        self.wake_word_detector = None
        self.audio_capture = None
        
        # Initialize control thread and queues
        self.control_thread = None
        self.command_queue = queue.Queue()
        self.update_ui_callback = None
    
    def _find_model(self, model_path):
        """Find the wake word model file in various possible locations"""
        # First check if path is valid as is
        if os.path.exists(model_path):
            logger.info(f"Found wake word model at path: {model_path}")
            self.model_path = model_path
            return
            
        # Try to resolve relative path
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # Define common places to look
        search_paths = [
            os.path.join(base_dir, model_path),  # Base dir
            os.path.join(base_dir, "models", model_path),  # Models folder
            os.path.join(base_dir, "assets", model_path),  # Assets folder
            os.path.join(base_dir, "io_wake_word", model_path),  # io_wake_word folder
            os.path.join(base_dir, "utils", "io_wake_word", model_path)  # utils/io_wake_word folder
        ]
        
        # Search for the model file
        for path in search_paths:
            if os.path.exists(path):
                logger.info(f"Found wake word model at: {path}")
                self.model_path = path
                return
                
        # Model not found
        logger.warning(f"Wake word model not found: {model_path}")
        logger.warning(f"Searched paths: {search_paths}")
        self.model_path = None
        
    def set_ui_callback(self, callback):
        """Set callback function for UI updates"""
        self.update_ui_callback = callback
        
    def start(self):
        """Start the voice manager"""
        if self.running:
            logger.info("Voice manager already running")
            return
            
        self.running = True
        
        # Initialize wake word detector if model exists
        if WAKE_WORD_AVAILABLE:
            if self.model_path:
                try:
                    self.wake_word_detector = WakeWordDetector(model_path=self.model_path)
                    logger.info(f"Wake word detector initialized with model: {self.model_path}")
                except Exception as e:
                    logger.error(f"Failed to initialize wake word detector: {e}")
                    # Show user a message through UI
                    if hasattr(self.ui, 'set_status'):
                        self.ui.set_status(f"Voice error: {str(e)}", False)
            else:
                logger.warning("Cannot initialize wake word detector - model not found")
                # Show user a message through UI
                if hasattr(self.ui, 'set_status'):
                    self.ui.set_status("Voice unavailable - model not found", False)
        else:
            logger.warning("Wake word detection not available - io_wake_word package missing")
            # Show user a message through UI
            if hasattr(self.ui, 'set_status'):
                self.ui.set_status("Voice unavailable - missing dependencies", False)
        
        # Start the control thread
        self.control_thread = threading.Thread(
            target=self._control_loop,
            daemon=True,
            name="VoiceManagerThread"
        )
        self.control_thread.start()
        
        # Set initial state
        if self.enabled and self.wake_word_detector is not None:
            self._transition_to(VoiceState.LISTENING)
            if hasattr(self.ui, 'set_status'):
                self.ui.set_status("Voice activated - listening for wake word", False)
        else:
            self._transition_to(VoiceState.INACTIVE)
            if hasattr(self.ui, 'set_status'):
                self.ui.set_status("Voice inactive", False)
            
        logger.info(f"Voice manager started, enabled={self.enabled}, model_available={self.model_path is not None}")
        
        # Log diagnostic info in debug mode
        if self.debug_mode:
            logger.info(f"Voice manager details:")
            logger.info(f"  Original model path: {self.original_model_path}")
            logger.info(f"  Resolved model path: {self.model_path}")
            logger.info(f"  WAKE_WORD_AVAILABLE: {WAKE_WORD_AVAILABLE}")
            logger.info(f"  wake_word_detector: {self.wake_word_detector}")
            logger.info(f"  Initial state: {self.state}")
        
    def stop(self):
        """Stop the voice manager and clean up resources"""
        if not self.running:
            return
            
        self.running = False
        
        # Wait for control thread to exit
        if self.control_thread:
            self.control_thread.join(timeout=2.0)
            
        # Stop audio components
        self._stop_audio_components()
        
        # Clean up resources
        if self.audio_capture:
            try:
                self.audio_capture.stop()
            except Exception as e:
                logger.error(f"Error stopping audio capture: {e}")
            finally:
                self.audio_capture = None
                
        if hasattr(self, 'feature_extractor') and self.feature_extractor:
            self.feature_extractor = None
            
        # Set state to inactive
        self._transition_to(VoiceState.INACTIVE)
        
        logger.info("Voice manager stopped")
        
    def toggle_voice(self, enabled=None):
        """Toggle voice features on/off"""
        if enabled is None:
            # Toggle current state
            enabled = not (self._get_state() == VoiceState.LISTENING 
                          or self._get_state() == VoiceState.FOCUSING)
        
        # Check if wake word detection is available      
        if enabled and not WAKE_WORD_AVAILABLE:
            logger.warning("Cannot enable voice - wake word package not available")
            if hasattr(self.ui, 'set_status'):
                self.ui.set_status("Voice unavailable - missing dependencies", False)
            return False
            
        # Check if model is available
        if enabled and not self.model_path:
            logger.warning("Cannot enable voice - wake word model not found")
            if hasattr(self.ui, 'set_status'):
                self.ui.set_status("Voice unavailable - model not found", False)
            return False
            
        # Send command to enable/disable
        if enabled:
            self.command_queue.put(("enable", None))
            if hasattr(self.ui, 'set_status'):
                self.ui.set_status("Activating voice...", True)
        else:
            self.command_queue.put(("disable", None))
            if hasattr(self.ui, 'set_status'):
                self.ui.set_status("Deactivating voice...", True)
                
        return enabled
        
    def process_speech(self, text):
        """Process speech captured from STT"""
        if not text or not text.strip():
            return False
            
        try:
            # Mark that we detected speech
            self.speech_detected = True
            self.last_speech_time = time.time()
            
            # Log the transcription
            logger.info(f"Transcribed speech: '{text}'")
            
            # Switch to processing state
            self._transition_to(VoiceState.PROCESSING)
            
            # Queue speech for processing
            self.command_queue.put(("process_speech", text))
            
            return True
        except Exception as e:
            logger.error(f"Error processing speech: {e}")
            return False
            
    def _handle_wake_word_detected(self, confidence):
        """Handle wake word detection callback"""
        logger.info(f"Wake word detected with confidence: {confidence:.4f}")
        self.command_queue.put(("focus", None))
        
    def _control_loop(self):
        """Main control loop for voice manager thread"""
        logger.info("Voice manager control thread started")
        
        while self.running:
            try:
                # Process any pending commands
                self._process_commands()
                
                # Handle state-specific actions
                current_state = self._get_state()
                
                if current_state == VoiceState.INACTIVE:
                    # In inactive state, just sleep
                    time.sleep(0.1)
                    
                elif current_state == VoiceState.LISTENING:
                    # Ensure audio components are running
                    if not hasattr(self, '_listening_active') or not self._listening_active:
                        self._setup_listening()
                    
                    # Process audio frame
                    if hasattr(self, '_listening_active') and self._listening_active:
                        self._process_audio_frame()
                    
                    time.sleep(0.01)
                    
                elif current_state == VoiceState.FOCUSING:
                    # In focusing state, run STT
                    if hasattr(self, '_listening_active') and self._listening_active:
                        self._stop_audio_components()
                        
                    # Run STT
                    self._run_stt()
                    
                    # Check if we detected speech
                    if not self.speech_detected:
                        # No speech detected, return to listening
                        logger.info("No speech detected, returning to listening")
                        self._transition_to(VoiceState.LISTENING)
                    else:
                        # Reset for next focus session
                        self.speech_detected = False
                        
                elif current_state in (VoiceState.PROCESSING, VoiceState.SPEAKING):
                    # Just wait for commands
                    time.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Error in voice manager control loop: {e}")
                time.sleep(0.5)
                
        logger.info("Voice manager control thread exited")
    
    def _setup_listening(self):
        """Set up components for listening mode"""
        try:
            # Check if wake word detection is available
            if not WAKE_WORD_AVAILABLE:
                logger.warning("Cannot start listening - wake word detection unavailable")
                self._transition_to(VoiceState.INACTIVE)
                return False
                
            if not self.wake_word_detector:
                logger.warning("Cannot start listening - wake word detector not initialized")
                self._transition_to(VoiceState.INACTIVE)
                return False
                
            if not self.audio_capture:
                try:
                    self.audio_capture = AudioCapture()
                except Exception as e:
                    logger.error(f"Failed to initialize audio capture: {e}")
                    self._transition_to(VoiceState.INACTIVE)
                    return False
                
            # Register wake word detection callback
            if self.wake_word_detector:
                self.wake_word_detector.register_detection_callback(self._handle_wake_word_detected)
                
            # Start audio capture
            if not hasattr(self.audio_capture, 'is_running') or not self.audio_capture.is_running:
                try:
                    self.audio_capture.start()
                except Exception as e:
                    logger.error(f"Failed to start audio capture: {e}")
                    self._transition_to(VoiceState.INACTIVE)
                    return False
                
            # Mark listening as active
            self._listening_active = True
            
            # Update UI
            self._update_ui()
            
            logger.info("Wake word detection started")
            return True
            
        except Exception as e:
            logger.error(f"Error starting wake word detection: {e}")
            self._listening_active = False
            self._transition_to(VoiceState.INACTIVE)
            return False
    
    def _process_audio_frame(self):
        """Process a single audio frame for wake word detection"""
        try:
            if not self.audio_capture or not self.wake_word_detector:
                return
                
            # Get audio frame from capture
            audio_buffer = self.audio_capture.get_buffer()
            
            if audio_buffer is not None and len(audio_buffer) > 0:
                # Check if we need to start the detector
                if not self.wake_word_detector.is_running:
                    try:
                        self.wake_word_detector.start()
                    except Exception as e:
                        logger.error(f"Failed to start wake word detector: {e}")
                        self._transition_to(VoiceState.INACTIVE)
        except Exception as e:
            logger.error(f"Error processing audio frame: {e}")
                
    def _stop_audio_components(self):
        """Stop audio processing components"""
        try:
            # Stop audio capture
            if self.audio_capture:
                self.audio_capture.stop()
                
            # Stop wake word detector
            if self.wake_word_detector and hasattr(self.wake_word_detector, 'is_running') and self.wake_word_detector.is_running:
                self.wake_word_detector.stop()
                
            # Mark listening as inactive
            self._listening_active = False
            
            # Update UI
            self._update_ui()
            
            logger.info("Wake word detection stopped")
        except Exception as e:
            logger.error(f"Error stopping audio components: {e}")
            
    def _process_commands(self):
        """Process commands from the queue"""
        try:
            # Get command with short timeout
            try:
                command, data = self.command_queue.get(block=True, timeout=0.1)
            except queue.Empty:
                return
            
            # Process the command
            if command == "enable":
                # Check if model is available before enabling
                if not self.model_path or not self.wake_word_detector:
                    logger.warning("Cannot enable voice - wake word model or detector not available")
                    if hasattr(self.ui, 'set_status'):
                        self.ui.set_status("Voice unavailable - model not found", False)
                else:
                    self._transition_to(VoiceState.LISTENING)
                    logger.info("Voice features enabled")
                    if hasattr(self.ui, 'set_status'):
                        self.ui.set_status("Voice activated - listening for wake word", False)
                
            elif command == "disable":
                if hasattr(self, '_listening_active') and self._listening_active:
                    self._stop_audio_components()
                    
                self._transition_to(VoiceState.INACTIVE)
                logger.info("Voice features disabled")
                if hasattr(self.ui, 'set_status'):
                    self.ui.set_status("Voice inactive", False)
                
            elif command == "focus":
                # Transition to focusing state
                self._transition_to(VoiceState.FOCUSING)
                
            elif command == "process_speech":
                # Process the transcribed speech
                self._send_to_chat_engine(data)
                
            elif command == "done_speaking":
                # Transition back to focusing or listening
                if self._get_state() == VoiceState.SPEAKING:
                    self._transition_to(VoiceState.LISTENING)
                
            # Mark command as processed
            self.command_queue.task_done()
            
        except Exception as e:
            logger.error(f"Error processing command: {e}")
            
    def _run_stt(self):
        """Run STT and handle the result"""
        try:
            # Reset speech detection flag
            self.speech_detected = False
            self.last_speech_time = 0
            
            # Update UI
            self._update_ui()
            
            # Add a "Listening..." indicator to the chat
            if hasattr(self.ui, 'output_queue'):
                self.ui.output_queue.put({"type": "status_bubble", "text": "Listening..."})
            
            # Run the speech-to-text
            logger.info("Starting speech capture with whisper")
            
            try:
                transcription = listen_and_transcribe(
                    silence_threshold=500,
                    silence_duration=2.0,
                    model_size="tiny"
                )
            except Exception as e:
                logger.error(f"Error in speech recognition: {e}")
                transcription = None
            
            # Remove the listening indicator
            if hasattr(self.ui, 'output_queue'):
                self.ui.output_queue.put({"type": "remove_status_bubble"})
            
            # Process the transcription if valid
            if transcription and transcription.strip():
                self.process_speech(transcription)
            else:
                logger.info("No speech detected or empty transcription")
                
        except Exception as e:
            logger.error(f"Error in STT processing: {e}")
            
        finally:
            # Remove the status bubble if we exit unexpectedly
            if hasattr(self.ui, 'output_queue'):
                self.ui.output_queue.put({"type": "remove_status_bubble"})
                
            # If we're still in focusing state, go back to listening
            current_state = self._get_state()
            if current_state == VoiceState.FOCUSING and not self.speech_detected:
                self._transition_to(VoiceState.LISTENING)
                
    def _send_to_chat_engine(self, text):
        """Send transcribed text to the chat engine"""
        # Use a separate thread
        def process_thread():
            try:
                # Get user prefix from chat engine
                user_prefix = self.chat_engine.get_user_prefix()
                
                # Display the user message in UI
                if hasattr(self.ui, 'output_queue'):
                    # GUI mode - add to output queue
                    self.ui.output_queue.put({"type": "user", "text": text})
                else:
                    # Terminal mode - print directly
                    print(f"\n{user_prefix} {text}")
                
                # Log user message
                self.chat_engine.logger.log_message(user_prefix, text)
                
                # Add to conversation history
                self.chat_engine.add_to_conversation_history(f"{user_prefix} {text}")
                
                # Set speaking state
                self._transition_to(VoiceState.SPEAKING)
                
                # Prepare and send message to LLM
                llm_message = self.chat_engine.prepare_message_for_llm(text)
                response = self.chat_engine.llm_client.generate_chat_response(
                    llm_message, 
                    temperature=self.chat_engine.config['llm']['chat_temperature']
                )
                
                # Display Jupiter's response in UI
                if hasattr(self.ui, 'output_queue'):
                    # GUI mode - add to output queue
                    self.ui.output_queue.put({"type": "jupiter", "text": response})
                else:
                    # Terminal mode - print directly
                    print(f"\nJupiter: {response}")
                
                # Log Jupiter's response
                self.chat_engine.logger.log_message("Jupiter:", response)
                
                # Speak the response
                llm_speak(response)
                
                # Add to conversation history
                self.chat_engine.add_to_conversation_history(f"Jupiter: {response}")
                
                # Return to listening state
                self.command_queue.put(("done_speaking", None))
                
            except Exception as e:
                logger.error(f"Error in chat engine processing: {e}")
                # Return to listening state on error
                self._transition_to(VoiceState.LISTENING)
                
        # Start processing thread
        thread = threading.Thread(target=process_thread)
        thread.daemon = True
        thread.start()
        
    def _get_state(self):
        """Get current state with thread safety"""
        with self.state_lock:
            return self.state
            
    def _transition_to(self, new_state):
        """Transition to a new state with thread safety"""
        with self.state_lock:
            old_state = self.state
            self.state = new_state
            
        # Log the transition
        logger.info(f"Voice state transition: {old_state.name} -> {new_state.name}")
        
        # If transitioning to LISTENING state but model is not available, go to INACTIVE
        if new_state == VoiceState.LISTENING and (not self.model_path or not self.wake_word_detector):
            logger.warning("Cannot transition to LISTENING - wake word model or detector not available")
            with self.state_lock:
                self.state = VoiceState.INACTIVE
            self._update_ui()
            if hasattr(self.ui, 'set_status'):
                self.ui.set_status("Voice unavailable - model not found", False)
            return
        
        # Update UI
        self._update_ui()
        
    def _update_ui(self):
        """Update UI based on current state"""
        try:
            current_state = self._get_state()
            
            # Call the UI callback if available
            if self.update_ui_callback and callable(self.update_ui_callback):
                self.update_ui_callback(current_state)
                
            # Update status in GUI if available
            if hasattr(self.ui, 'set_status'):
                if current_state == VoiceState.INACTIVE:
                    self.ui.set_status("Voice inactive", False)
                elif current_state == VoiceState.LISTENING:
                    self.ui.set_status("Listening for wake word", False)
                elif current_state == VoiceState.FOCUSING:
                    self.ui.set_status("Listening to you", True)
                elif current_state == VoiceState.PROCESSING:
                    self.ui.set_status("Processing your request", True)
                elif current_state == VoiceState.SPEAKING:
                    self.ui.set_status("Speaking", True)
                    
        except Exception as e:
            logger.error(f"Error updating UI: {e}")
    
    def set_debug_mode(self, enabled=True):
        """Enable or disable debug mode for more verbose logging"""
        self.debug_mode = enabled
        if enabled:
            logger.info("Voice manager debug mode enabled")
            
            # Log current state
            logger.info(f"Current state: {self._get_state().name}")
            logger.info(f"Model path: {self.model_path}")
            logger.info(f"Wake word detector: {self.wake_word_detector}")
            logger.info(f"Audio capture: {self.audio_capture}")
            
            # Check if listening is active
            listening_active = hasattr(self, '_listening_active') and self._listening_active
            logger.info(f"Listening active: {listening_active}")