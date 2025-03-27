import threading
import queue
import logging
import time
import gc

# Set up logging
logger = logging.getLogger("jupiter.gui.message_processor")

class MessageProcessor(threading.Thread):
    """
    Thread-safe message processor for GUI updates
    
    Handles messages from the output queue and updates the UI components
    in a thread-safe manner.
    """
    
    def __init__(self, message_queue, chat_view, knowledge_view, status_bar, root):
        """
        Initialize the message processor
        
        Args:
            message_queue: Queue containing UI update messages
            chat_view: ChatView component
            knowledge_view: KnowledgeView component
            status_bar: StatusBar component
            root: Tkinter root window
        """
        super().__init__(daemon=True, name="MessageProcessorThread")
        self.message_queue = message_queue
        self.chat_view = chat_view
        self.knowledge_view = knowledge_view
        self.status_bar = status_bar
        self.root = root
        self.running = False
        
        # Initialize tracking for pending operations
        self._pending_after_ids = []
    
    def run(self):
        """Run the message processor thread"""
        self.running = True
        logger.info("Message processor started")
        
        while self.running:
            try:
                # Get message from queue with timeout to allow checking running flag
                try:
                    message = self.message_queue.get(timeout=0.1)
                except queue.Empty:
                    continue
                
                # Process based on message type - schedule updates on main thread
                if message["type"] == "jupiter":
                    self._schedule_safe_update(
                        lambda m=message["text"]: self.chat_view.display_jupiter_message(m)
                    )
                elif message["type"] == "user":
                    self._schedule_safe_update(
                        lambda m=message["text"]: self.chat_view.display_user_message(m)
                    )
                elif message["type"] == "update_prefix":
                    self._schedule_safe_update(
                        lambda m=message["prefix"]: self.chat_view.update_user_prefix(m)
                    )
                elif message["type"] == "status":
                    self._schedule_safe_update(
                        lambda m=message: self.status_bar.set_status(m["text"], m.get("color", "#4CAF50"))
                    )
                elif message["type"] == "clear":
                    self._schedule_safe_update(
                        lambda: self.chat_view.clear()
                    )
                elif message["type"] == "status_bubble":
                    self._schedule_safe_update(
                        lambda m=message["text"]: self.chat_view.display_status_bubble(m)
                    )
                elif message["type"] == "remove_status_bubble":
                    self._schedule_safe_update(
                        lambda: self.chat_view.remove_status_bubble()
                    )
                elif message["type"] == "create_knowledge":
                    self._schedule_safe_update(
                        lambda m=message["data"]: self.knowledge_view.create_knowledge_bubbles(m)
                    )
                
                # Mark as done
                self.message_queue.task_done()
                
                # Small sleep to prevent CPU hogging
                time.sleep(0.01)
                
            except Exception as e:
                logger.error(f"Error processing message: {e}", exc_info=True)
        
        logger.info("Message processor stopped")
    
    def stop(self):
        """Stop the message processor with proper cleanup"""
        logger.info("Message processor stopping...")
        self.running = False
        
        # Clean up pending operations
        self._cleanup_pending_operations()
        
        # Wait a bit for thread to finish processing
        count = 0
        while self.is_alive() and count < 10:
            time.sleep(0.1)
            count += 1
            
        logger.info("Message processor stopped")
    
    def _schedule_safe_update(self, update_func):
        """Schedule a UI update to run safely on the main thread with error handling"""
        try:
            # Check if root window still exists
            if not self.root or not self.root.winfo_exists():
                logger.debug("Cannot schedule update - root window no longer exists")
                return
                
            # Tkinter's after() method is thread-safe and queues the call
            after_id = self.root.after(0, self._execute_safe_update, update_func)
            
            # Keep track of scheduled task IDs
            self._pending_after_ids.append(after_id)
            
        except Exception as e:
            logger.error(f"Error scheduling UI update: {e}")
    
    def _execute_safe_update(self, update_func):
        """Execute a UI update function with proper error handling"""
        try:
            # Try to execute the update function
            update_func()
            
        except Exception as e:
            logger.error(f"Error executing UI update: {e}")
            
        finally:
            # Remove this task ID from tracking list
            for after_id in list(self._pending_after_ids):
                try:
                    if after_id in self._pending_after_ids:
                        self._pending_after_ids.remove(after_id)
                except Exception:
                    pass
    
    def _cleanup_pending_operations(self):
        """Clean up any pending operations to prevent memory leaks"""
        try:
            # Cancel any pending after() calls
            if self.root and self.root.winfo_exists():
                for after_id in list(self._pending_after_ids):
                    try:
                        self.root.after_cancel(after_id)
                    except Exception:
                        pass
            
            # Clear the list even if root is gone
            self._pending_after_ids.clear()
            
            # Force garbage collection
            gc.collect()
            
        except Exception as e:
            logger.error(f"Error cleaning up message processor: {e}")
            # Make sure list is cleared even on error
            self._pending_after_ids.clear()