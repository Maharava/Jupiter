import tkinter as tk
from tkinter import scrolledtext, PhotoImage
import os
import threading
import queue

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
        
        # Threading event for synchronization
        self.input_ready = threading.Event()
        self.gui_ready = threading.Event()
        
        # Flag to check if GUI is still running
        self.is_running = True
        
        # User info
        self.user_prefix = "User"
        
        # Button callbacks
        self.restart_callback = None
        self.knowledge_callback = None
        
        # Start GUI in a separate thread
        self.gui_thread = threading.Thread(target=self._run_gui)
        self.gui_thread.daemon = True
        self.gui_thread.start()
        
        # Wait for GUI to initialize
        self.gui_ready.wait()
    
    def _run_gui(self):
        """Run the GUI in a separate thread"""
        # Create main window
        self.root = tk.Tk()
        self.root.title("Jupiter Chat")
        self.root.configure(bg="black")
        self.root.geometry("400x600")  # Default size, but resizable
        
        # Set up window close handler
        self.root.protocol("WM_DELETE_WINDOW", self.handle_window_close)
        
        # Try to load icon
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
                except (ImportError, AttributeError):
                    pass
                    
                # Alternative approach for other platforms
                try:
                    png_path = os.path.join(assets_dir, "jupiter.png")
                    if os.path.exists(png_path):
                        icon_img = PhotoImage(file=png_path)
                        self.root.iconphoto(True, icon_img)
                except:
                    pass
            except Exception as e:
                print(f"Failed to load icon: {e}")
        
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
        
        # Create chat display
        chat_frame = tk.Frame(self.root, bg="black")
        chat_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create scrollable text area
        self.chat_text = scrolledtext.ScrolledText(
            chat_frame,
            wrap=tk.WORD,
            bg="black",
            fg="white",
            insertbackground="white",
            selectbackground="#666",
            selectforeground="white",
            font=("Helvetica", 10),
            padx=10,
            pady=10
        )
        self.chat_text.pack(fill=tk.BOTH, expand=True)
        self.chat_text.config(state=tk.DISABLED)  # Make read-only
        
        # Configure text tags for different message types
        self.chat_text.tag_configure("jupiter_prefix", foreground=self._get_color(self.jupiter_color))
        self.chat_text.tag_configure("jupiter_bubble", background=self._get_color(self.jupiter_color, 0.7), 
                                    foreground="black", relief=tk.SOLID, borderwidth=1, lmargin1=10, lmargin2=10, 
                                    rmargin=10, spacing1=3, spacing3=3)
        
        self.chat_text.tag_configure("user_prefix", foreground=self._get_color(self.user_color))
        self.chat_text.tag_configure("user_bubble", background=self._get_color(self.user_color, 0.7), 
                                    foreground="white", relief=tk.SOLID, borderwidth=1, lmargin1=10, lmargin2=10, 
                                    rmargin=10, spacing1=3, spacing3=3)
        
        # Create input area
        input_frame = tk.Frame(self.root, bg="black")
        input_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        # Create status label
        self.status_label = tk.Label(
            self.root,
            text="Ready",
            bg="black",
            fg="#4CAF50",  # Green color for ready status
            font=("Helvetica", 9, "italic"),
            anchor="w"
        )
        self.status_label.pack(fill=tk.X, padx=10, pady=(0, 5))
        
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
        
        # Create send button
        send_button = tk.Button(
            input_frame,
            text="Send",
            bg="#333",
            fg="white",
            relief=tk.FLAT,
            padx=5,
            pady=2
        )
        send_button.pack(side=tk.RIGHT, padx=(5, 0))
        
        # Handle send button click and Enter key
        def send_message(event=None):
            message = self.text_entry.get().strip()
            if message:
                # Clear entry
                self.text_entry.delete(0, tk.END)
                
                # Put message in queue
                self.input_queue.put(message)
                
                # Signal that input is ready
                self.input_ready.set()
                
                # Focus on text entry
                self.text_entry.focus_set()
        
        send_button.config(command=send_message)
        self.text_entry.bind("<Return>", send_message)
        
        # Set initial focus
        self.text_entry.focus_set()
        
        # Start message processor
        message_thread = threading.Thread(target=self._process_messages)
        message_thread.daemon = True
        message_thread.start()
        
        # Signal that GUI is ready
        self.gui_ready.set()
        
        # Start GUI event loop
        self.root.mainloop()
    
    def _handle_restart(self):
        """Handle restart button click"""
        if self.restart_callback:
            self.restart_callback()
        else:
            self.print_jupiter_message("Restart functionality not yet implemented.")
    
    def _handle_knowledge(self):
        """Handle knowledge button click"""
        if self.knowledge_callback:
            self.knowledge_callback()
        else:
            self.print_jupiter_message("Knowledge functionality not yet implemented.")
    
    def set_restart_callback(self, callback):
        """Set the callback for restart button"""
        self.restart_callback = callback
    
    def set_knowledge_callback(self, callback):
        """Set the callback for knowledge button"""
        self.knowledge_callback = callback
    
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
    
    def _process_messages(self):
        """Process messages in the output queue"""
        while True:
            try:
                # Get message from queue
                message = self.output_queue.get()
                
                # Process based on message type
                if message["type"] == "jupiter":
                    self._display_jupiter_message(message["text"])
                elif message["type"] == "user":
                    self._display_user_message(message["text"])
                elif message["type"] == "update_prefix":
                    self._update_user_prefix(message["prefix"])
                elif message["type"] == "status":
                    self._update_status(message["text"], message.get("color", "#4CAF50"))
                elif message["type"] == "clear":
                    self._clear_chat()
                
                # Mark as done
                self.output_queue.task_done()
            except Exception as e:
                print(f"Error processing message: {e}")
    
    def _display_jupiter_message(self, message):
        """Display a message from Jupiter in the chat"""
        def update_display():
            # Enable editing
            self.chat_text.config(state=tk.NORMAL)
            
            # Add prefix
            self.chat_text.insert(tk.END, "Jupiter: ", "jupiter_prefix")
            self.chat_text.insert(tk.END, "\n")
            
            # Add message in bubble
            bubble_start = self.chat_text.index(tk.INSERT)
            self.chat_text.insert(tk.END, f"{message}\n\n")
            bubble_end = self.chat_text.index(tk.INSERT)
            
            # Apply bubble tag
            self.chat_text.tag_add("jupiter_bubble", bubble_start, bubble_end)
            
            # Scroll to bottom
            self.chat_text.see(tk.END)
            
            # Disable editing
            self.chat_text.config(state=tk.DISABLED)
        
        # Schedule on main thread
        if self.root:
            self.root.after(0, update_display)
    
    def _display_user_message(self, message):
        """Display a message from the user in the chat"""
        def update_display():
            # Enable editing
            self.chat_text.config(state=tk.NORMAL)
            
            # Add prefix
            self.chat_text.insert(tk.END, f"{self.user_prefix}: ", "user_prefix")
            self.chat_text.insert(tk.END, "\n")
            
            # Add message in bubble
            bubble_start = self.chat_text.index(tk.INSERT)
            self.chat_text.insert(tk.END, f"{message}\n\n")
            bubble_end = self.chat_text.index(tk.INSERT)
            
            # Apply bubble tag
            self.chat_text.tag_add("user_bubble", bubble_start, bubble_end)
            
            # Scroll to bottom
            self.chat_text.see(tk.END)
            
            # Disable editing
            self.chat_text.config(state=tk.DISABLED)
        
        # Schedule on main thread
        if self.root:
            self.root.after(0, update_display)
    
    def _clear_chat(self):
        """Clear the chat display"""
        def update_display():
            # Enable editing
            self.chat_text.config(state=tk.NORMAL)
            
            # Clear all text
            self.chat_text.delete(1.0, tk.END)
            
            # Disable editing
            self.chat_text.config(state=tk.DISABLED)
        
        # Schedule on main thread
        if self.root:
            self.root.after(0, update_display)
    
    def _update_user_prefix(self, prefix):
        """Update the user prefix in the GUI"""
        def update():
            if self.user_label:
                self.user_label.config(text=f"{prefix}:")
        
        # Schedule on main thread
        if self.root:
            self.root.after(0, update)
    
    def _update_status(self, status_text, color="#4CAF50"):
        """Update the status label in the GUI"""
        def update():
            if self.status_label:
                self.status_label.config(text=status_text, fg=color)
        
        # Schedule on main thread
        if self.root:
            self.root.after(0, update)
            
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
        
        # Wait for input only if GUI is still running
        if self.is_running:
            self.input_ready.wait()
        else:
            # GUI was closed, return exit command
            return "exit"
        
        # Get input from queue
        user_input = self.input_queue.get()
        
        # Display user message (only if it's not an exit command from window closing)
        if user_input.lower() != "exit" or not self.input_queue.empty():
            self.output_queue.put({"type": "user", "text": user_input})
        
        return user_input
    
    def print_welcome(self):
        """Print welcome message"""
        self.print_jupiter_message("=== Jupiter Chat ===")
    
    def print_exit_instructions(self):
        """Print exit instructions - does nothing in GUI mode"""
        # Skip displaying exit instructions in GUI mode
        pass
    
    def handle_exit_command(self, user_input):
        """Check if user wants to exit"""
        if user_input.lower() in ['exit', 'quit']:
            self.print_jupiter_message("Ending chat session. Goodbye!")
            return True
        return False
    
    def handle_window_close(self):
        """Handle window close event (X button)"""
        self.is_running = False
        # Put exit message in queue to break the input waiting loop
        self.input_queue.put("exit")
        self.input_ready.set()
        # Destroy the window
        if self.root:
            self.root.destroy()
        
    def exit_program(self):
        """Exit the program"""
        self.is_running = False
        if self.root:
            self.root.after(0, self.root.destroy)