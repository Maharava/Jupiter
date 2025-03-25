import threading
import time
import queue
import logging
from enum import Enum, auto
from utils.io.io import WakeWordDetector
from utils.whisper_stt import listen_and_transcribe
from utils.piper import llm_speak

# Set up logging
logger = logging.getLogger("jupiter.voice")

class VoiceState(Enum):
    """States for the voice interaction state machine"""
    INACTIVE = auto()  # Voice features are disabled
    LISTENING = auto()  # Wake word detection active
    FOCUSING = auto()   # STT active, waiting for speech
    PROCESSING = auto() # Processing captured speech
    SPEAKING = auto()   # Jupiter is speaking

class VoiceManager:
    """
    Manages voice interaction for Jupiter, coordinating wake word detection 
    and speech-to-text processing.
    """
    
    def __init__(self, chat_engine, ui, model_path=None, enabled=True):
        """
        Initialize the voice manager.
        
        Args:
            chat_engine: Jupiter's chat engine for processing transcribed text
            ui: The UI object (terminal or GUI) for feedback
            model_path: Path to the wake word model
            enabled: Whether voice features are enabled by default
        """
        self.chat_engine = chat_engine
        self.ui = ui
        self.model_path = model_path
        self.enabled = enabled
        
        # Initialize state and locks
        self.state = VoiceState.INACTIVE
        self.state_lock = threading.Lock()
        self.running = False
        
        # For speech detection status tracking
        self.speech_detected = False
        self.last_speech_time = 0
        
        # Create wake word detector
        self.wake_word_detector = None
        if model_path:
            try:
                self.wake_word_detector = WakeWordDetector(model_path=model_path)
                logger.info(f"Wake word detector initialized with model: {model_path}")
            except Exception as e:
                logger.error(f"Failed to initialize wake word detector: {e}")
        
        # Initialize control thread
        self.control_thread = None
        
        # Command queue for thread-safe operations
        self.command_queue = queue.Queue()
        
        # UI update callback
        self.update_ui_callback = None
        
    def set_ui_callback(self, callback):
        """Set callback function for UI updates"""
        self.update_ui_callback = callback
        
    def start(self):
        """Start the voice manager"""
        if self.running:
            return
            
        if not self.wake_word_detector:
            logger.error("Cannot start voice manager: wake word detector not initialized")
            return
            
        self.running = True
        
        # Start the control thread
        self.control_thread = threading.Thread(
            target=self._control_loop,
            daemon=True,
            name="VoiceManagerThread"
        )
        self.control_thread.start()
        
        # Set initial state
        if self.enabled:
            self._transition_to(VoiceState.LISTENING)
        else:
            self._transition_to(VoiceState.INACTIVE)
            
        logger.info("Voice manager started")
        
    def stop(self):
        """Stop the voice manager"""
        if not self.running:
            return
            
        self.running = False
        
        # Wait for control thread to exit
        if self.control_thread:
            self.control_thread.join(timeout=2.0)
            
        # Ensure wake word detector is stopped
        if self.wake_word_detector:
            self.wake_word_detector.stop()
            
        # Set state to inactive
        self._transition_to(VoiceState.INACTIVE)
        
        logger.info("Voice manager stopped")
        
    def toggle_voice(self, enabled=None):
        """Toggle voice features on/off"""
        if enabled is None:
            # Toggle current state
            enabled = not (self._get_state() == VoiceState.LISTENING 
                          or self._get_state() == VoiceState.FOCUSING)
                          
        if enabled:
            # Queue command to enable
            self.command_queue.put(("enable", None))
            if hasattr(self.ui, 'set_status'):
                self.ui.set_status("Activating voice...", True)
        else:
            # Queue command to disable
            self.command_queue.put(("disable", None))
            if hasattr(self.ui, 'set_status'):
                self.ui.set_status("Deactivating voice...", True)
                
        return enabled
        
    def process_speech(self, text):
        """Process speech captured from STT"""
        if not text or not text.strip():
            return False
            
        try:
            # Mark that we detected speech in this session
            self.speech_detected = True
            self.last_speech_time = time.time()
            
            # Log the transcription
            logger.info(f"Transcribed speech: '{text}'")
            
            # Switch to processing state
            self._transition_to(VoiceState.PROCESSING)
            
            # Queue speech for processing by the chat engine
            self.command_queue.put(("process_speech", text))
            
            return True
        except Exception as e:
            logger.error(f"Error processing speech: {e}")
            return False
            
    def _handle_wake_word_detected(self, confidence):
        """Handle wake word detection callback"""
        logger.info(f"Wake word detected with confidence: {confidence:.4f}")
        
        # Queue command to start focusing
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
                    # In listening state, ensure wake word detector is running
                    if not hasattr(self, '_wake_word_running') or not self._wake_word_running:
                        self._start_wake_word_detection()
                        
                    # Process commands and sleep
                    time.sleep(0.1)
                    
                elif current_state == VoiceState.FOCUSING:
                    # In focusing state, run STT
                    if hasattr(self, '_wake_word_running') and self._wake_word_running:
                        self._stop_wake_word_detection()
                        
                    # Run STT in this thread
                    self._run_stt()
                    
                    # After STT completes, check if we detected speech
                    if not self.speech_detected:
                        # No speech detected, return to listening
                        logger.info("No speech detected in focus session, returning to listening")
                        self._transition_to(VoiceState.LISTENING)
                    else:
                        # Reset for next focus session
                        self.speech_detected = False
                        
                elif current_state == VoiceState.PROCESSING:
                    # In processing state, just wait for commands
                    time.sleep(0.1)
                    
                elif current_state == VoiceState.SPEAKING:
                    # In speaking state, check if done speaking
                    # For now, we'll just wait for the command to transition
                    time.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Error in voice manager control loop: {e}")
                time.sleep(0.5)  # Sleep longer on error
                
        logger.info("Voice manager control thread exited")
        
    def _process_commands(self):
        """Process commands from the queue"""
        try:
            # Get command with short timeout
            command, data = self.command_queue.get(block=True, timeout=0.1)
            
            # Process the command
            if command == "enable":
                self._transition_to(VoiceState.LISTENING)
                logger.info("Voice features enabled")
                
            elif command == "disable":
                # Stop wake word detection if running
                if hasattr(self, '_wake_word_running') and self._wake_word_running:
                    self._stop_wake_word_detection()
                    
                self._transition_to(VoiceState.INACTIVE)
                logger.info("Voice features disabled")
                
            elif command == "focus":
                # Transition to focusing state
                self._transition_to(VoiceState.FOCUSING)
                
            elif command == "process_speech":
                # Process the transcribed speech
                text = data
                
                # Forward the transcribed text to the chat engine
                # We'll set a timer to transition back to focusing after
                # This will happen in the callback from the chat engine
                self._send_to_chat_engine(text)
                
            elif command == "done_speaking":
                # Transition back to focusing
                self._transition_to(VoiceState.FOCUSING)
                
            # Mark command as processed
            self.command_queue.task_done()
            
        except queue.Empty:
            # No commands to process
            pass
        except Exception as e:
            logger.error(f"Error processing command: {e}")
            
    def _start_wake_word_detection(self):
        """Start wake word detection"""
        try:
            # Register detection callback
            self.wake_word_detector.register_detection_callback(self._handle_wake_word_detected)
            
            # Start detection
            self.wake_word_detector.start()
            self._wake_word_running = True
            
            # Update UI
            self._update_ui()
            
            logger.info("Wake word detection started")
        except Exception as e:
            logger.error(f"Error starting wake word detection: {e}")
            self._wake_word_running = False
            
    def _stop_wake_word_detection(self):
        """Stop wake word detection"""
        try:
            # Stop detection
            self.wake_word_detector.stop()
            self._wake_word_running = False
            
            # Update UI
            self._update_ui()
            
            logger.info("Wake word detection stopped")
        except Exception as e:
            logger.error(f"Error stopping wake word detection: {e}")
            
    def _run_stt(self):
        """Run STT and handle the result"""
        try:
            # Reset speech detection flag for this session
            self.speech_detected = False
            self.last_speech_time = 0
            
            # Update UI
            self._update_ui()
            
            # Run the speech-to-text
            logger.info("Starting speech capture with whisper")
            
            # Set silence threshold and duration
            transcription = listen_and_transcribe(
                silence_threshold=500,  # Adjust based on environment
                silence_duration=2.0,   # 2 seconds of silence to end capture
                model_size="tiny"       # Use tiny model for speed
            )
            
            # Process the transcription if valid
            if transcription and transcription.strip():
                # Process the speech
                self.process_speech(transcription)
            else:
                logger.info("No speech detected or empty transcription")
                # No speech detected, will return to listening mode
                pass
                
        except Exception as e:
            logger.error(f"Error in STT processing: {e}")
            
        finally:
            # If we're still in focusing state, go back to listening
            # This can happen if there's an error during STT
            current_state = self._get_state()
            if current_state == VoiceState.FOCUSING and not self.speech_detected:
                self._transition_to(VoiceState.LISTENING)
                
    def _send_to_chat_engine(self, text):
        """Send transcribed text to the chat engine"""
        # We'll use a separate thread to avoid blocking the control loop
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
                
                # Return to focusing state
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
