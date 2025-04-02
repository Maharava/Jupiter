import threading
import time
import queue
import logging
import os
from enum import Enum, auto

from utils.piper import llm_speak
from utils.whisper_stt import listen_and_transcribe

# Import wake word detector
try:
    from io_wake_word.io_wake_word import WakeWordDetector
    WAKE_WORD_AVAILABLE = True
except ImportError as e:
    WAKE_WORD_AVAILABLE = False
    print(f"Warning: io_wake_word module not available: {e}")

# Set up logging
logger = logging.getLogger("jupiter.voice")

# Reduce states by combining FOCUSING and PROCESSING
class VoiceState(Enum):
    """Simplified states for voice interaction"""
    INACTIVE = auto()   # Voice disabled
    LISTENING = auto()  # Waiting for wake word
    ACTIVE = auto()     # Processing user input (combines focusing and processing)
    SPEAKING = auto()   # Speaking response

def error_handler(func):
    """Decorator to standardize error handling"""
    def wrapper(self, *args, **kwargs):
        try:
            return func(self, *args, **kwargs)
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {e}")
            # Return to stable state
            self._transition_to(VoiceState.LISTENING if self.enabled else VoiceState.INACTIVE)
            return None
    return wrapper

class VoiceManager:
    """Voice manager for Jupiter - handles TTS, STT, and wake word detection"""
    
    def __init__(self, chat_engine, ui, model_path=None, enabled=True):
        """Initialize voice manager"""
        self.chat_engine = chat_engine
        self.ui = ui
        self.enabled = enabled
        
        # Default model path if not provided
        if not model_path:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.model_path = os.path.join(base_dir, "models", "jupiter-wake-word.pth")
        else:
            self.model_path = model_path
        
        # Initialize state
        self.state = VoiceState.INACTIVE
        self.state_lock = threading.Lock()
        self.running = False
        
        # Initialize wake word detection components
        self.wake_word_detector = None
        self.wake_word_thread = None
        self.detector_available = WAKE_WORD_AVAILABLE and os.path.exists(self.model_path)
        
        # Initialize control thread and queues
        self.control_thread = None
        self.command_queue = queue.Queue()
        self.update_ui_callback = None
        
        # Flag for active listening
        self._listening_active = False

        # Initialize task queue and worker thread
        self.task_queue = queue.Queue()
        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
    
    def set_ui_callback(self, callback):
        """Set callback function for UI updates"""
        self.update_ui_callback = callback
        
    def start(self):
        """Start the voice manager"""
        if self.running:
            logger.info("Voice manager already running")
            return
            
        self.running = True
        
        # Start the control thread
        self.control_thread = threading.Thread(
            target=self._control_loop,
            daemon=True,
            name="VoiceManagerThread"
        )
        self.control_thread.start()

        # Start the worker thread
        self.worker_thread.start()
        
        # Start wake word detection if enabled and available
        if self.enabled and self.detector_available:
            self._start_wake_word_detection()
            if hasattr(self.ui, 'set_status'):
                self.ui.set_status("Listening for wake word", False)
        else:
            # Set initial state
            self._transition_to(VoiceState.INACTIVE)
            if hasattr(self.ui, 'set_status'):
                if not self.detector_available and self.enabled:
                    self.ui.set_status("Voice active for speaking only (wake word unavailable)", False)
                else:
                    self.ui.set_status("Voice active for speaking only", False)
            
        logger.info(f"Voice manager started, enabled={self.enabled}, wake_word_available={self.detector_available}")
        
    def _start_wake_word_detection(self):
        """Start wake word detection in a background thread"""
        if not self.detector_available:
            logger.warning("Wake word detection not available")
            return False
            
        try:
            # Create the wake word detector
            self.wake_word_detector = WakeWordDetector(
                model_path=self.model_path,
                threshold=0.85  # Detection threshold
            )
            
            # Register wake word detection callback
            self.wake_word_detector.register_detection_callback(self._on_wake_word_detected)
            
            # Start the detection thread
            self.wake_word_thread = threading.Thread(
                target=self._wake_word_detection_loop,
                daemon=True,
                name="WakeWordThread"
            )
            self.wake_word_thread.start()
            
            # Transition to listening state
            self._transition_to(VoiceState.LISTENING)
            
            logger.info("Wake word detection started")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start wake word detection: {e}")
            self.wake_word_detector = None
            return False
            
    def _wake_word_detection_loop(self):
        """Background thread for wake word detection"""
        try:
            logger.info("Starting wake word detection loop")
            
            # Start the detector
            self.wake_word_detector.start()
            
            # Use the blocking listen method with continuous option
            self.wake_word_detector.listen_for_wake_word(
                timeout=None,  # No timeout
                continuous=True  # Keep listening after detection
            )
            
        except Exception as e:
            logger.error(f"Error in wake word detection loop: {e}")
        finally:
            logger.info("Wake word detection loop ended")
                
    def _on_wake_word_detected(self, confidence):
        """Called when wake word is detected"""
        if not self.enabled:
            logger.debug(f"Wake word detected (confidence: {confidence:.4f}) but voice is disabled")
            return
            
        logger.info(f"Wake word detected (confidence: {confidence:.4f}) - starting to listen for command")
        
        # Check if we're already processing a command
        current_state = self._get_state()
        if current_state in [VoiceState.ACTIVE, VoiceState.SPEAKING]:
            logger.info(f"Ignoring wake word detection while in {current_state.name} state")
            return
        
        # Transition to ACTIVE state
        self._transition_to(VoiceState.ACTIVE)
        
        # Display status bubble in UI
        if hasattr(self.ui, 'display_status_bubble'):
            self.ui.display_status_bubble("Listening for command...")
            
        # Start listening for command in a separate thread to not block wake word detection
        self.task_queue.put((self._listen_for_command, [], {}))
    
    def _listen_for_command(self):
        """Listen for and process voice command after wake word detection"""
        try:
            # Flag to track listening state
            self._listening_active = True
            
            # Use Whisper to transcribe command
            transcription = listen_and_transcribe(
                silence_threshold=500,  # Adjust based on your environment
                silence_duration=2,     # Stop after 2 seconds of silence
                model_size="base"       # Can be "tiny", "base", "small", etc.
            )
            
            # Reset listening flag
            self._listening_active = False
            
            # Remove status bubble
            if hasattr(self.ui, 'remove_status_bubble'):
                self.ui.remove_status_bubble()
                
            # Transition to ACTIVE state
            self._transition_to(VoiceState.ACTIVE)
            
            # Log the transcription
            logger.info(f"Command transcription: {transcription}")
            
            # Process the command if we got a valid transcription
            if transcription and transcription.strip():
                # Display transcription in UI
                if hasattr(self.ui, 'display_status_bubble'):
                    self.ui.display_status_bubble(f"Processing: {transcription}")
                
                # Process command by sending it to chat engine like a normal input
                self._process_voice_command(transcription)
            else:
                # No valid transcription
                logger.info("No valid command detected")
                self._transition_to(VoiceState.LISTENING)
                
        except Exception as e:
            logger.error(f"Error listening for command: {e}")
            self._listening_active = False
            self._transition_to(VoiceState.LISTENING)
            
            # Remove status bubble
            if hasattr(self.ui, 'remove_status_bubble'):
                self.ui.remove_status_bubble()
    
    def _process_voice_command(self, command):
        """Process voice command by sending it to chat engine"""
        try:
            # Check if we have a valid chat engine
            if not self.chat_engine:
                logger.error("No chat engine available to process command")
                self._transition_to(VoiceState.LISTENING)
                return
                
            # Get current user data for context
            user_prefix = self.chat_engine.get_user_prefix().rstrip(':')
            
            # Log the command
            self.chat_engine.logger.log_message(f"{user_prefix}:", command)
            
            # Add to conversation history
            self.chat_engine.add_to_conversation_history(f"{user_prefix}: {command}")
            
            # Update UI to show the command
            if hasattr(self.ui, 'output_queue'):
                self.ui.output_queue.put({"type": "user", "text": command})
            
            # Check for user commands
            command_response = self.chat_engine.handle_user_commands(command)
            if command_response:
                # This was a command, display response
                if hasattr(self.ui, 'output_queue'):
                    self.ui.output_queue.put({"type": "jupiter", "text": command_response})
                
                # Add response to history
                self.chat_engine.add_to_conversation_history(f"Jupiter: {command_response}")
                self.chat_engine.logger.log_message("Jupiter:", command_response)
                
                # Speak the response
                self._transition_to(VoiceState.SPEAKING)
                self.speak(command_response)
                
                # Return to listening state
                self._transition_to(VoiceState.LISTENING)
                return
                
            # Process with LLM
            llm_message = self.chat_engine.prepare_message_for_llm(command)
            response = self.chat_engine.llm_client.generate_chat_response(
                llm_message, 
                temperature=self.chat_engine.config['llm']['chat_temperature']
            )
            
            # Display response in UI
            if hasattr(self.ui, 'output_queue'):
                self.ui.output_queue.put({"type": "jupiter", "text": response})
            
            # Add response to history
            self.chat_engine.add_to_conversation_history(f"Jupiter: {response}")
            self.chat_engine.logger.log_message("Jupiter:", response)
            
            # Speak the response
            self._transition_to(VoiceState.SPEAKING)
            self.speak(response)
            
            # Return to listening state
            self._transition_to(VoiceState.LISTENING)
            
        except Exception as e:
            logger.error(f"Error processing voice command: {e}")
            self._transition_to(VoiceState.LISTENING)
        
        finally:
            # Remove status bubble
            if hasattr(self.ui, 'remove_status_bubble'):
                self.ui.remove_status_bubble()
            
            # Reset UI status
            if hasattr(self.ui, 'set_status'):
                self.ui.set_status("Ready", False)
    
    def stop(self):
        """Stop the voice manager and clean up resources"""
        if not self.running:
            return
            
        self.running = False
        
        # Stop wake word detector
        if self.wake_word_detector:
            try:
                self.wake_word_detector.stop()
            except:
                pass
            self.wake_word_detector = None
        
        # Wait for control thread to exit
        if self.control_thread:
            self.control_thread.join(timeout=2.0)
            
        # Set state to inactive
        self._transition_to(VoiceState.INACTIVE)
        
        logger.info("Voice manager stopped")
        
    def toggle_voice(self, enabled=None):
        """Toggle voice features on/off"""
        if enabled is None:
            # Toggle current state
            enabled = not self.enabled
        
        # Update enabled state
        self.enabled = enabled
        
        # Update wake word detector state
        if enabled and self.detector_available:
            if not self.wake_word_detector:
                self._start_wake_word_detection()
            self._transition_to(VoiceState.LISTENING)
            if hasattr(self.ui, 'set_status'):
                self.ui.set_status("Listening for wake word", False)
        else:
            # Stop wake word detector if running
            if self.wake_word_detector:
                try:
                    self.wake_word_detector.stop()
                except:
                    pass
                self.wake_word_detector = None
                
            self._transition_to(VoiceState.INACTIVE)
            if hasattr(self.ui, 'set_status'):
                if not enabled:
                    self.ui.set_status("Voice inactive", False)
                else:
                    self.ui.set_status("Voice active for speaking only", False)
                
        # Log state change
        logger.info(f"Voice features {'enabled' if enabled else 'disabled'}")
                
        return enabled
            
    def _control_loop(self):
        """Main control loop for voice manager thread"""
        logger.info("Voice manager control thread started")
        
        while self.running:
            try:
                # Process any pending commands
                self._process_commands()
                
                # Just sleep - no active processing needed
                time.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Error in voice manager control loop: {e}")
                time.sleep(0.5)
                
        logger.info("Voice manager control thread exited")
    
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
                self.enabled = True
                logger.info("Voice features enabled")
                
                # Start wake word detector if available
                if self.detector_available:
                    if not self.wake_word_detector:
                        self._start_wake_word_detection()
                    self._transition_to(VoiceState.LISTENING)
                    if hasattr(self.ui, 'set_status'):
                        self.ui.set_status("Listening for wake word", False)
                else:
                    if hasattr(self.ui, 'set_status'):
                        self.ui.set_status("Voice active for speaking only", False)
                
            elif command == "disable":
                self.enabled = False
                logger.info("Voice features disabled")
                
                # Stop wake word detector if running
                if self.wake_word_detector:
                    try:
                        self.wake_word_detector.stop()
                    except:
                        pass
                    self.wake_word_detector = None
                
                self._transition_to(VoiceState.INACTIVE)
                if hasattr(self.ui, 'set_status'):
                    self.ui.set_status("Voice inactive", False)
                
            elif command == "done_speaking":
                # Transition back to listening state if wake word is active
                if self._get_state() == VoiceState.SPEAKING:
                    if self.enabled and self.wake_word_detector:
                        self._transition_to(VoiceState.LISTENING)
                    else:
                        self._transition_to(VoiceState.INACTIVE)
                
            # Mark command as processed
            self.command_queue.task_done()
            
        except Exception as e:
            logger.error(f"Error processing command: {e}")
    
    def speak(self, text):
        """Speak text using TTS if enabled"""
        if not self.enabled:
            logger.debug("Voice disabled, not speaking")
            return False
            
        try:
            # Set speaking state
            self._transition_to(VoiceState.SPEAKING)
            
            # Speak using Piper TTS
            llm_speak(text)
            
            # Return to appropriate state based on wake word detector status
            if self.enabled and self.wake_word_detector:
                self._transition_to(VoiceState.LISTENING)
            else:
                self._transition_to(VoiceState.INACTIVE)
            
            return True
        except Exception as e:
            logger.error(f"Error in TTS: {e}")
            
            # Return to appropriate state based on wake word detector status
            if self.enabled and self.wake_word_detector:
                self._transition_to(VoiceState.LISTENING)
            else:
                self._transition_to(VoiceState.INACTIVE)
                
            return False
        
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
        
    def _update_ui(self, message=None, busy=False, bubble_text=None):
        """Centralized UI update method"""
        current_state = self._get_state()
        
        # Update callback if registered
        if self.update_ui_callback:
            self.update_ui_callback(current_state)
        
        # Update status text if provided
        if message and hasattr(self.ui, 'set_status'):
            self.ui.set_status(message, busy)
        
        # Update status bubble if provided
        if bubble_text:
            if hasattr(self.ui, 'display_status_bubble'):
                self.ui.display_status_bubble(bubble_text)
        elif bubble_text is None and hasattr(self.ui, 'remove_status_bubble'):
            self.ui.remove_status_bubble()

    def _worker_loop(self):
        """Single worker thread to handle all async tasks"""
        while self.running:
            try:
                task_func, args, kwargs = self.task_queue.get(timeout=0.1)
                task_func(*args, **kwargs)
                self.task_queue.task_done()
            except queue.Empty:
                pass
            except Exception as e:
                logger.error(f"Task error: {e}")