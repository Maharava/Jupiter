# tts_manager.py
import threading
import queue
from piper_tts import PiperTTS

class TTSManager:
    def __init__(self):
        # Initialize TTS engine
        self.tts = PiperTTS()
        
        # Create a queue for speech requests
        self.speech_queue = queue.Queue()
        
        # Flag to control background thread
        self.running = True
        
        # Start worker thread
        self.worker_thread = threading.Thread(target=self._process_queue)
        self.worker_thread.daemon = True
        self.worker_thread.start()
        
        # Track current speech task
        self.current_task = None
    
    def _process_queue(self):
        """Worker thread that processes the speech queue"""
        while self.running:
            try:
                # Get task with timeout to allow checking running flag
                task = self.speech_queue.get(timeout=0.5)
                self.current_task = task
                
                # Process the task
                text, voice, speaker_id, callback = task
                
                # Speak the text (blocking in this thread, but not main thread)
                self.tts.speak_long_text(text, voice, speaker_id, blocking=True)
                
                # Execute callback if provided
                if callback:
                    callback()
                    
                # Mark task as done
                self.speech_queue.task_done()
                self.current_task = None
                
            except queue.Empty:
                # Queue timeout - just continue and check running flag
                pass
            except Exception as e:
                print(f"Error in TTS worker: {e}")
                if self.current_task:
                    self.speech_queue.task_done()
                    self.current_task = None
    
    def speak(self, text, voice=None, speaker_id=None, callback=None):
        """Add text to the speech queue"""
        self.speech_queue.put((text, voice, speaker_id, callback))
    
    def stop(self):
        """Stop currently playing speech and clear queue"""
        # Clear the queue
        while not self.speech_queue.empty():
            try:
                self.speech_queue.get_nowait()
                self.speech_queue.task_done()
            except queue.Empty:
                break
        
        # Stop current playback (if sd has a stop method)
        import sounddevice as sd
        sd.stop()
    
    def shutdown(self):
        """Shut down the TTS manager"""
        self.running = False
        self.stop()
        if self.worker_thread.is_alive():
            self.worker_thread.join(timeout=1.0)