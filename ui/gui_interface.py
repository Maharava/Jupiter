import tkinter as tk
import threading
import queue
import os
import gc
import logging
import time

from ui.components.chat_view import ChatView
from ui.components.knowledge_view import KnowledgeView
from ui.components.status_bar import StatusBar
from ui.components.voice_indicator import VoiceIndicator
from ui.utils.message_processor import MessageProcessor
from utils.voice_manager import VoiceState

# Set up logging
logger = logging.getLogger("jupiter.gui")

class GUIInterface:
    """Graphical User Interface for Jupiter Chat"""
    
    def __init__(self, jupiter_color="red", user_color="purple"):
        """Initialize GUI interface with colors"""
        # Store colors
        self.jupiter_color = jupiter_color
        self.user_color = user_color
        
        # Communication queues for thread-safe operation
        self.input_queue = queue.Queue()
        self.output_queue = queue.Queue()
        self.knowledge_edit_queue = queue.Queue()
        
        # Threading events for synchronization
        self.input_ready = threading.Event()
        self.gui_ready = threading.Event()
        
        # Flag to check if GUI is still running
        self.is_running = True
        
        # Current view state
        self.current_view = "chat"  # can be "chat" or "knowledge"
        
        # User info
        self.user_prefix = "User"
        self.last_user_input = ""
        
        # Button callbacks
        self.restart_callback = None
        self.knowledge_callback = None
        self.voice_toggle_callback = None
        
        # Voice indicator reference
        self.voice_indicator = None
        
        # Initialize tracking for pending operations
        self._pending_after_ids = []
        
        # Debugging state for voice
        self.voice_debug_mode = False
        
        # Start GUI in a separate thread with proper error handling
        self.gui_thread = threading.Thread(target=self._run_gui)
        self.gui_thread.daemon = True
        self.gui_thread.start()
        
        # Wait for GUI to initialize with timeout to prevent deadlock
        if not self.gui_ready.wait(timeout=10.0):
            logger.error("GUI failed to initialize within timeout period")
            self.is_running = False
            raise RuntimeError("GUI failed to initialize")
    
    def _run_gui(self):
        """Run the GUI in a separate thread with proper error handling"""
        try:
            # Create main window
            self.root = tk.Tk()
            self.root.title("Jupiter Chat")
            self.root.configure(bg="black")
            self.root.geometry("400x600")  # Default size, but resizable
            
            # Set up window close handler
            self.root.protocol("WM_DELETE_WINDOW", self.handle_window_close)
            
            # Try to load icon
            self._setup_icons()
            
            # Create button frame at the top
            button_frame = tk.Frame(self.root, bg="black")
            button_frame.pack(fill=tk.X, padx=5, pady=5)
            
            # Create Restart button
            restart_button = tk.Button(
                button_frame,
                text="Restart",
                bg="#333",
                fg="white",
                relief=tk.FLAT,
                padx=10,
                pady=2,
                command=self._handle_restart
            )
            restart_button.pack(side=tk.LEFT, padx=5)
            
            # Create Knowledge button
            knowledge_button = tk.Button(
                button_frame,
                text="Knowledge",
                bg="#333",
                fg="white",
                relief=tk.FLAT,
                padx=10,
                pady=2,
                command=self._handle_knowledge
            )
            knowledge_button.pack(side=tk.LEFT, padx=5)
            
            # Create Voice Debug button
            debug_button = tk.Button(
                button_frame,
                text="VDebug",
                bg="#333",
                fg="white",
                relief=tk.FLAT,
                padx=10,
                pady=2,
                command=self._toggle_voice_debug
            )
            debug_button.pack(side=tk.LEFT, padx=5)
            
            # Create Calendar Preferences button if available
            self._setup_calendar_button(button_frame)
            
            # Create chat view component
            self.chat_view = ChatView(
                self.root, 
                jupiter_color=self.jupiter_color,
                user_color=self.user_color
            )
            
            # Create knowledge view component
            self.knowledge_view = KnowledgeView(
                self.root,
                jupiter_color=self.jupiter_color,
                clean_callback=lambda: self.command_queue.put(("show_chat", None))
            )
            
            # Initially show chat view
            self.current_view = "chat"
            self.chat_view.pack(fill=tk.BOTH, expand=True)
            
            # Create input area frame
            input_frame = tk.Frame(self.root, bg="black")
            input_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
            
            # Create status bar
            self.status_bar = StatusBar(self.root)
            self.status_bar.pack(fill=tk.X, padx=10, pady=(0, 5))
            
            # Create user label
            self.user_label = tk.Label(
                input_frame,
                text=f"{self.user_prefix}:",
                bg="black",
                fg=self._get_color(self.user_color),
                font=("Helvetica", 10, "bold")
            )
            self.user_label.pack(side=tk.LEFT, padx=(0, 5))
            
            # Create text entry
            self.text_entry = tk.Entry(
                input_frame,
                bg="#222",
                fg="white",
                insertbackground="white",
                font=("Helvetica", 10)
            )
            self.text_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
            
            # Create send and close buttons
            self.send_button = tk.Button(
                input_frame,
                text="Send",
                bg="#333",
                fg="white",
                relief=tk.FLAT,
                padx=5,
                pady=2
            )
            self.send_button.pack(side=tk.RIGHT, padx=(5, 0))
            
            # Create close button (initially hidden)
            self.close_button = tk.Button(
                input_frame,
                text="Close",
                bg="#333",
                fg="white",
                relief=tk.FLAT,
                padx=5,
                pady=2,
                command=lambda: self.command_queue.put(("show_chat", None))
            )
            
            # Handle send button click and Enter key
            def send_message(event=None):
                message = self.text_entry.get().strip()
                if message:
                    # Store the message before clearing the entry
                    self.last_user_input = message
                    
                    # Clear entry
                    self.text_entry.delete(0, tk.END)
                    
                    # Put message in queue
                    self.input_queue.put(message)
                    
                    # Signal that input is ready
                    self.input_ready.set()
                    
                    # Focus on text entry
                    self.text_entry.focus_set()
            
            self.send_button.config(command=send_message)
            self.text_entry.bind("<Return>", send_message)
            
            # Set initial focus
            self.text_entry.focus_set()
            
            # Initialize message processor
            self.message_processor = MessageProcessor(
                self.output_queue,
                self.chat_view,
                self.knowledge_view,
                self.status_bar,
                self.root
            )
            self.message_processor.start()
            
            # Create command processing queue and start command thread
            self.command_queue = queue.Queue()
            self.command_thread = threading.Thread(
                target=self._process_commands,
                daemon=True,
                name="GUICommandThread"
            )
            self.command_thread.start()
            
            # Initialize calendar notifications if available
            self._init_calendar_notifications()
            
            # Signal that GUI is ready
            self.gui_ready.set()
            
            # Start GUI event loop
            self.root.mainloop()
            
        except Exception as e:
            logger.error(f"Error initializing GUI: {e}", exc_info=True)
            # Signal that GUI failed to initialize
            self.is_running = False
            self.gui_ready.set()  # Set event to unblock main thread
    
    def _toggle_voice_debug(self):
        """Toggle voice debug mode for diagnostics"""
        self.voice_debug_mode = not self.voice_debug_mode
        if self.voice_debug_mode:
            self.set_status("Voice debug mode enabled", True)
            if hasattr(self, 'voice_indicator') and self.voice_indicator:
                self._schedule_safe_update(lambda: self._check_voice_state_debug())
        else:
            self.set_status("Voice debug mode disabled", False)
    
    def _check_voice_state_debug(self):
        """Check voice state and display debug info"""
        if not self.voice_debug_mode:
            return
            
        try:
            status_text = "Voice Debug Info:\n"
            
            # Try to access voice manager from chat engine
            if hasattr(self, '_chat_engine') and self._chat_engine:
                vm = getattr(self._chat_engine, 'voice_manager', None)
                if vm:
                    status_text += f"State: {vm.state.name if hasattr(vm.state, 'name') else 'Unknown'}\n"
                    status_text += f"Enabled: {vm.enabled}\n"
                    status_text += f"Running: {vm.running}\n"
                    status_text += f"Model Path: {vm.model_path}\n"
                    
                    # Check if audio components are active
                    listening_active = getattr(vm, '_listening_active', False)
                    status_text += f"Listening Active: {listening_active}\n"
                else:
                    status_text += "Voice Manager not found\n"
            else:
                status_text += "Chat Engine not available\n"
                
            # Display info in chat
            self.output_queue.put({"type": "jupiter", "text": status_text})
            
            # Schedule next check in 5 seconds if debug mode is still on
            if self.voice_debug_mode:
                self._schedule_safe_update(lambda: self._check_voice_state_debug())
                
        except Exception as e:
            logger.error(f"Error in voice debug: {e}")
            self.output_queue.put({"type": "jupiter", "text": f"Voice Debug Error: {str(e)}"})
    
    def _setup_icons(self):
        """Set up window icons with proper error handling"""
        try:
            assets_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")
            if not os.path.exists(assets_dir):
                os.makedirs(assets_dir, exist_ok=True)
                
            icon_path = os.path.join(assets_dir, "jupiter.ico")
            if os.path.exists(icon_path):
                try:
                    # For Windows, set both the window icon and taskbar icon
                    self.root.iconbitmap(icon_path)
                    
                    # Set taskbar icon (Windows specific)
                    try:
                        # Using ctypes to set the app user model ID for Windows taskbar
                        import ctypes
                        myappid = 'jupiter.ai.chat.1.0'  # Arbitrary but unique string
                        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
                    except (ImportError, AttributeError, Exception):
                        pass
                        
                    # Alternative approach for other platforms
                    try:
                        png_path = os.path.join(assets_dir, "jupiter.png")
                        if os.path.exists(png_path):
                            icon_img = tk.PhotoImage(file=png_path)
                            self.root.iconphoto(True, icon_img)
                    except Exception:
                        pass
                except Exception:
                    pass
        except Exception as e:
            logger.warning(f"Could not set up application icons: {e}")
    
    def _init_calendar_notifications(self):
        """Initialize calendar notifications if available with error handling"""
        try:
            from utils.calendar import initialize_calendar_daemon
            initialize_calendar_daemon(gui_root=self.root, terminal_ui=None, enable_voice=True)
            logger.info("Calendar notifications initialized")
        except ImportError:
            logger.info("Calendar module not available, notifications disabled")
        except Exception as e:
            logger.warning(f"Could not initialize calendar notifications: {e}")
    
    def _setup_calendar_button(self, button_frame):
        """Set up calendar button if calendar module is available with error handling"""
        try:
            from utils.calendar.preferences_ui import show_preferences_dialog
            calendar_button = tk.Button(
                button_frame,
                text="Calendar",
                bg="#333",
                fg="white",
                relief=tk.FLAT,
                padx=10,
                pady=2,
                command=lambda: self._schedule_safe_update(
                    lambda: show_preferences_dialog(self.root)
                )
            )
            calendar_button.pack(side=tk.LEFT, padx=5)
            logger.info("Calendar button added")
        except ImportError:
            logger.info("Calendar module not available, button not added")
        except Exception as e:
            logger.warning(f"Could not add calendar button: {e}")
    
    def _process_commands(self):
        """Process commands from the command queue with proper error handling"""
        while self.is_running:
            try:
                # Get command with timeout
                try:
                    command, data = self.command_queue.get(timeout=0.5)
                except queue.Empty:
                    continue
                
                # Process the command
                if command == "show_chat":
                    self._schedule_safe_update(self._show_chat_view_internal)
                elif command == "show_knowledge":
                    self._schedule_safe_update(self._show_knowledge_view_internal)
                
                # Mark command as processed
                self.command_queue.task_done()
                
            except Exception as e:
                logger.error(f"Error processing command: {e}")
            
            # Small sleep to prevent CPU hogging
            time.sleep(0.01)
    
    def setup_voice_indicator(self, toggle_callback=None):
        """Set up the voice indicator in the GUI with proper error handling"""
        if not hasattr(self, 'root') or not self.root:
            logger.warning("Cannot set up voice indicator - root window not available")
            return
            
        try:
            # Store callback for diagnostics
            self.voice_toggle_callback = toggle_callback
            
            # Create indicator in status area
            status_frame = self.status_bar.get_frame()
            
            # Create the voice indicator
            self.voice_indicator = VoiceIndicator(status_frame, callback=self._handle_voice_toggle)
            
            # Position it next to the status label
            self.voice_indicator.pack(side=tk.RIGHT, padx=10)
            
            # Set initial state
            self.update_voice_state(None)
            logger.info("Voice indicator set up successfully")
            
        except Exception as e:
            logger.error(f"Error setting up voice indicator: {e}")
    
    def _handle_voice_toggle(self):
        """Handle voice indicator click with proper error handling"""
        try:
            if self.voice_debug_mode:
                # In debug mode, show detailed status
                self._check_voice_state_debug()
                
            # Call the original toggle function if available
            if self.voice_toggle_callback and callable(self.voice_toggle_callback):
                self.voice_toggle_callback()
        except Exception as e:
            logger.error(f"Error handling voice toggle: {e}")
            self.set_status(f"Voice toggle error: {str(e)}", True)
            
    def update_voice_state(self, state):
        """Update the voice indicator state with proper error handling"""
        if not hasattr(self, 'voice_indicator') or not self.voice_indicator:
            return
            
        try:
            # Schedule update on main thread
            self._schedule_safe_update(lambda: self.voice_indicator.update_state(state))
            
            # If state is INACTIVE and we're in debug mode, show an explanation
                
        except Exception as e:
            logger.error(f"Error updating voice state: {e}")
    
    def _get_color(self, color_name, alpha=1.0):
        """Convert color name to hex with optional alpha simulation"""
        # Basic color mapping
        color_map = {
            "yellow": "#FFEB3B",
            "red": "#F44336",
            "purple": "#673AB7",
            "magenta": "#E91E63"
        }
        
        # Get base color
        base_color = color_map.get(color_name.lower(), color_name)
        
        # If alpha is 1.0, return the base color
        if alpha == 1.0:
            return base_color
        
        # Convert hex to RGB
        r = int(base_color[1:3], 16)
        g = int(base_color[3:5], 16)
        b = int(base_color[5:7], 16)
        
        # Simulate alpha by blending with background (black)
        r = int(r * alpha)
        g = int(g * alpha)
        b = int(b * alpha)
        
        # Convert back to hex
        return f"#{r:02x}{g:02x}{b:02x}"
    
    def _schedule_safe_update(self, update_func):
        """Schedule a UI update to run safely on the main thread"""
        if not hasattr(self, 'root') or not self.root or not self.root.winfo_exists():
            logger.debug("Cannot schedule update - root window not available")
            return None
            
        try:
            after_id = self.root.after(0, update_func)
            # Keep track of scheduled task IDs
            self._pending_after_ids.append(after_id)
            return after_id
        except Exception as e:
            logger.error(f"Error scheduling UI update: {e}")
            return None
    
    def _handle_restart(self):
        """Handle restart button click with proper error handling"""
        try:
            if self.restart_callback:
                self.restart_callback()
            else:
                self.output_queue.put({"type": "jupiter", "text": "Restart functionality not yet implemented."})
        except Exception as e:
            logger.error(f"Error handling restart: {e}")
            self.output_queue.put({"type": "jupiter", "text": "An error occurred while restarting."})
    
    def _handle_knowledge(self):
        """Handle knowledge button click with proper error handling"""
        try:
            if self.knowledge_callback:
                self.knowledge_callback()
            else:
                self.output_queue.put({"type": "jupiter", "text": "Knowledge functionality not yet implemented."})
        except Exception as e:
            logger.error(f"Error handling knowledge view: {e}")
            self.output_queue.put({"type": "jupiter", "text": "An error occurred while accessing knowledge."})
    
    def show_knowledge_view(self):
        """Switch to knowledge view with proper cleanup (thread-safe)"""
        self.command_queue.put(("show_knowledge", None))
    
    def _show_knowledge_view_internal(self):
        """Internal implementation to switch to knowledge view"""
        try:
            if self.current_view == "knowledge":
                return
            
            # Clean up any pending operations
            self._cleanup_pending_operations()
            
            # Update state first to prevent race conditions
            self.current_view = "knowledge"
            
            # Hide chat view if it exists
            if hasattr(self, 'chat_view') and self.chat_view:
                self.chat_view.pack_forget()
            
            # Show knowledge view if it exists
            if hasattr(self, 'knowledge_view') and self.knowledge_view:
                self.knowledge_view.pack(fill=tk.BOTH, expand=True)
            
            # Change button in input area
            if hasattr(self, 'send_button') and self.send_button and self.send_button.winfo_exists():
                self.send_button.pack_forget()
            
            if hasattr(self, 'close_button') and self.close_button and self.close_button.winfo_exists():
                self.close_button.pack(side=tk.RIGHT, padx=(5, 0))
            
            # Update status
            if hasattr(self, 'status_bar') and self.status_bar:
                self.status_bar.set_status("Viewing Knowledge", False)
                
        except Exception as e:
            logger.error(f"Error showing knowledge view: {e}")
            # Fall back to chat view on error
            self.show_chat_view()
    
    def show_chat_view(self):
        """Switch back to chat view with proper cleanup (thread-safe)"""
        self.command_queue.put(("show_chat", None))
    
    def _show_chat_view_internal(self):
        """Internal implementation to switch back to chat view"""
        try:
            if self.current_view == "chat":
                return
            
            # Clean up any pending operations
            self._cleanup_pending_operations()
            
            # Update state first to prevent race conditions
            self.current_view = "chat"
            
            # Hide knowledge view if it exists
            if hasattr(self, 'knowledge_view') and self.knowledge_view:
                self.knowledge_view.pack_forget()
            
            # Show chat view if it exists
            if hasattr(self, 'chat_view') and self.chat_view:
                self.chat_view.pack(fill=tk.BOTH, expand=True)
            
            # Change button in input area
            if hasattr(self, 'close_button') and self.close_button and self.close_button.winfo_exists():
                self.close_button.pack_forget()
            
            if hasattr(self, 'send_button') and self.send_button and self.send_button.winfo_exists():
                self.send_button.pack(side=tk.RIGHT, padx=(5, 0))
            
            # Process any knowledge edits
            self.process_knowledge_edits()
            
            # Update status
            if hasattr(self, 'status_bar') and self.status_bar:
                self.status_bar.set_status("Ready", False)
            
            # Force garbage collection
            gc.collect()
            
        except Exception as e:
            logger.error(f"Error showing chat view: {e}")
    
    def _cleanup_pending_operations(self):
        """Clean up any pending operations to prevent memory leaks"""
        try:
            # Cancel any pending after() calls
            if hasattr(self, 'root') and self.root and self.root.winfo_exists():
                for after_id in list(self._pending_after_ids):
                    try:
                        self.root.after_cancel(after_id)
                    except Exception:
                        pass
                self._pending_after_ids.clear()
            else:
                self._pending_after_ids.clear()
            
            # Force Python garbage collection
            gc.collect()
        
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            self._pending_after_ids.clear()  # Clear list even on failure
    
    def create_knowledge_bubbles(self, user_data):
        """Create knowledge bubbles from user data"""
        if hasattr(self, 'knowledge_view') and self.knowledge_view:
            self.output_queue.put({"type": "create_knowledge", "data": user_data})
    
    def set_status(self, status_text, is_busy=False):
        """Set the status message in the GUI"""
        # Choose color based on busy state
        color = "#FFA500" if is_busy else "#4CAF50"  # Orange for busy, green for ready
        self.output_queue.put({"type": "status", "text": status_text, "color": color})
    
    def print_jupiter_message(self, message):
        """Print a message from Jupiter with correct color"""
        self.output_queue.put({"type": "jupiter", "text": message})
    
    def clear_chat(self):
        """Clear the chat display"""
        self.output_queue.put({"type": "clear"})
    
    def get_user_input(self, prefix="User"):
        """Get input from user with correct color"""
        # Update prefix (remove colon if present)
        prefix = prefix.rstrip(':')
        self.user_prefix = prefix
        
        # Send update to GUI
        self.output_queue.put({"type": "update_prefix", "prefix": prefix})
        
        # Clear previous event
        self.input_ready.clear()
        
        # Wait for input only if GUI is still running, with timeout
        if self.is_running:
            # Wait with timeout to prevent deadlock
            if not self.input_ready.wait(timeout=3600):  # 1 hour timeout
                logger.warning("Input wait timed out")
                return "exit"
        else:
            # GUI was closed, return exit command
            return "exit"
        
        # Get input from queue
        try:
            user_input = self.input_queue.get(block=False)
            
            # Always display user message regardless of exit command
            # This ensures the message appears in the chat window with correct text
            self.output_queue.put({"type": "user", "text": user_input})
            
            return user_input
        except queue.Empty:
            logger.warning("Input queue empty after input_ready event was set")
            return self.last_user_input or "exit"
    
    def print_welcome(self):
        """Print welcome message"""
        self.print_jupiter_message("=== Jupiter Chat ===")
    
    def print_exit_instructions(self):
        """Print exit instructions - does nothing in GUI mode"""
        # Skip displaying exit instructions in GUI mode
        pass
    
    def handle_exit_command(self, user_input):
        """Check if user wants to exit"""
        if user_input and user_input.lower() in ['exit', 'quit']:
            self.print_jupiter_message("Ending chat session. Goodbye!")
            return True
        return False
    
    def handle_window_close(self):
        """Handle window close event (X button) with proper cleanup"""
        logger.info("Window close initiated")
        
        # Mark running state as false to stop threads
        self.is_running = False
        
        # Clean up any pending operations
        self._cleanup_pending_operations()
        
        # Put exit message in queue to break input waiting loop and ensure it's not empty
        try:
            while not self.input_queue.empty():
                self.input_queue.get_nowait()
        except queue.Empty:
            pass
        self.input_queue.put("exit")
        self.input_ready.set()
        
        # Clear queues to prevent memory leaks
        try:
            while not self.output_queue.empty():
                self.output_queue.get_nowait()
        except queue.Empty:
            pass
            
        try:
            while not self.knowledge_edit_queue.empty():
                self.knowledge_edit_queue.get_nowait()
        except queue.Empty:
            pass
            
        try:
            while not self.command_queue.empty():
                self.command_queue.get_nowait()
        except queue.Empty:
            pass
        
        # Stop message processor
        if hasattr(self, 'message_processor'):
            self.message_processor.stop()
        
        # Clean up other resources
        self._destroy_gui()
        
    def _destroy_gui(self):
        """Destroy the GUI with proper error handling"""
        try:
            # Cancel all scheduled callbacks
            if hasattr(self, 'root') and self.root and self.root.winfo_exists():
                try:
                    for after_id in self.root.tk.call('after', 'info'):
                        try:
                            self.root.after_cancel(after_id)
                        except Exception:
                            pass
                except Exception:
                    pass
                    
                # Destroy the window
                self.root.destroy()
                self.root = None
                
            # Force garbage collection
            gc.collect()
            
        except Exception as e:
            logger.error(f"Error destroying GUI: {e}")
        
    def exit_program(self):
        """Exit the program with proper cleanup"""
        logger.info("Exit program initiated")
        
        self.is_running = False
        self._cleanup_pending_operations()
        
        # Stop message processor
        if hasattr(self, 'message_processor'):
            self.message_processor.stop()
        
        # Clear all queues
        for q in [self.input_queue, self.output_queue, self.knowledge_edit_queue, self.command_queue]:
            try:
                while not q.empty():
                    q.get_nowait()
            except (queue.Empty, AttributeError):
                pass
        
        # Force garbage collection
        gc.collect()
        
        # Destroy GUI safely
        if hasattr(self, 'root') and self.root:
            try:
                self.root.after(0, self.root.destroy)
            except Exception:
                self._destroy_gui()
    
    def process_knowledge_edits(self):
        """Process all queued knowledge edits with thread safety"""
        try:
            # Create a local copy of edits to process to avoid long lock
            local_edits = []
            
            # Get all pending edits from the queue
            while not self.knowledge_edit_queue.empty():
                try:
                    edit = self.knowledge_edit_queue.get_nowait()
                    local_edits.append(edit)
                    self.knowledge_edit_queue.task_done()
                except Exception as e:
                    logger.error(f"Error getting edit from queue: {e}")
                    break
                    
            # If no edits, return early
            if not local_edits:
                return
                
            # Log edit count for debugging
            logger.info(f"Processing {len(local_edits)} knowledge edits")
            
            # Schedule processing on main thread
            self._schedule_safe_update(lambda: self._process_knowledge_edits_batch(local_edits))
                    
        except Exception as e:
            logger.error(f"Error processing knowledge edits: {e}")
            
    def _process_knowledge_edits_batch(self, edits):
        """Process a batch of knowledge edits on the main thread"""
        edits_processed = 0
        errors = 0
        
        for edit in edits:
            try:
                # Log for debugging
                logger.debug(f"Processing knowledge edit: {edit}")
                
                # In a real implementation, this would notify the chat engine
                # to update the user model
                edits_processed += 1
            except Exception as e:
                errors += 1
                logger.error(f"Error processing edit {edits_processed + errors}: {e}")
                
        # If we had errors, show a status message
        if errors > 0:
            if hasattr(self, 'status_bar') and self.status_bar:
                self.status_bar.set_status(f"Warning: {errors} edit(s) failed to process", False)
    
    def set_restart_callback(self, callback):
        """Set the callback for restart button"""
        self.restart_callback = callback
    
    def set_knowledge_callback(self, callback):
        """Set the callback for knowledge button"""
        self.knowledge_callback = callback
        
    def register_chat_engine(self, chat_engine):
        """Register chat engine for debugging access"""
        self._chat_engine = chat_engine