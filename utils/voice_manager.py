import threading
import time
import queue
import logging
from enum import Enum, auto

from utils.piper import llm_speak

# Set up logging
logger = logging.getLogger("jupiter.voice")

class VoiceState(Enum):
    """States for the voice interaction state machine"""
    INACTIVE = auto()  # Voice features disabled
    SPEAKING = auto()   # Jupiter is speaking

class VoiceManager:
    """Simplified voice manager for Jupiter - handles TTS only"""
    
    def __init__(self, chat_engine, ui, model_path=None, enabled=True):
        """Initialize voice manager"""
        self.chat_engine = chat_engine
        self.ui = ui
        self.enabled = enabled
        
        # Initialize state
        self.state = VoiceState.INACTIVE
        self.state_lock = threading.Lock()
        self.running = False
        
        # Initialize control thread and queues
        self.control_thread = None
        self.command_queue = queue.Queue()
        self.update_ui_callback = None
    
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
        
        # Set initial state
        self._transition_to(VoiceState.INACTIVE)
        if hasattr(self.ui, 'set_status'):
            self.ui.set_status("Voice active for speaking only", False)
            
        logger.info(f"Voice manager started, enabled={self.enabled}")
        
    def stop(self):
        """Stop the voice manager and clean up resources"""
        if not self.running:
            return
            
        self.running = False
        
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
                
        # Update UI with current state
        if enabled:
            if hasattr(self.ui, 'set_status'):
                self.ui.set_status("Voice active for speaking only", False)
        else:
            if hasattr(self.ui, 'set_status'):
                self.ui.set_status("Voice inactive", False)
                
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
                if hasattr(self.ui, 'set_status'):
                    self.ui.set_status("Voice active for speaking only", False)
                
            elif command == "disable":
                self.enabled = False
                logger.info("Voice features disabled")
                if hasattr(self.ui, 'set_status'):
                    self.ui.set_status("Voice inactive", False)
                
            elif command == "done_speaking":
                # Transition back to inactive state
                if self._get_state() == VoiceState.SPEAKING:
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
            
            # Return to inactive state
            self._transition_to(VoiceState.INACTIVE)
            
            return True
        except Exception as e:
            logger.error(f"Error in TTS: {e}")
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
                    if self.enabled:
                        self.ui.set_status("Voice active for speaking only", False)
                    else:
                        self.ui.set_status("Voice inactive", False)
                elif current_state == VoiceState.SPEAKING:
                    self.ui.set_status("Speaking", True)
                    
        except Exception as e:
            logger.error(f"Error updating UI: {e}")