import tkinter as tk
from tkinter import scrolledtext, PhotoImage, simpledialog, ttk
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
        self.knowledge_edit_queue = queue.Queue()
        
        # Threading event for synchronization
        self.input_ready = threading.Event()
        self.gui_ready = threading.Event()
        
        # Flag to check if GUI is still running
        self.is_running = True
        
        # Current view state
        self.current_view = "chat"  # can be "chat" or "knowledge"
        
        # User info
        self.user_prefix = "User"
        
        # Button callbacks
        self.restart_callback = None
        self.knowledge_callback = None
        
        # Initialize tracking for pending operations
        self._pending_after_ids = []
        
        # Initialize list for tracking list bubbles
        self._list_bubbles = []
        
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
        
        # Create chat frame (initially visible)
        self.chat_frame = tk.Frame(self.root, bg="black")
        self.chat_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create scrollable text area for chat
        self.chat_text = scrolledtext.ScrolledText(
            self.chat_frame,
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
        
        # Create knowledge frame (initially hidden)
        self.create_knowledge_view()
        
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
            command=self.show_chat_view
        )
        
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
        
        self.send_button.config(command=send_message)
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
    
    def create_knowledge_view(self):
        """Create the knowledge view with a scrollable canvas"""
        self.knowledge_frame = tk.Frame(self.root, bg="black")
        
        # Create canvas with scrollbar for resizable content
        self.knowledge_canvas = tk.Canvas(self.knowledge_frame, bg="black", highlightthickness=0)
        scrollbar = tk.Scrollbar(self.knowledge_frame, orient="vertical", command=self.knowledge_canvas.yview)
        
        # Configure canvas scrolling
        self.knowledge_canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.knowledge_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Create frame inside canvas for content
        self.knowledge_content = tk.Frame(self.knowledge_canvas, bg="black")
        self.knowledge_canvas_window = self.knowledge_canvas.create_window((0, 0), window=self.knowledge_content, anchor="nw")
        
        # Add resize listeners
        self.knowledge_content.bind("<Configure>", self._on_knowledge_content_configure)
        self.knowledge_canvas.bind("<Configure>", self._on_knowledge_canvas_configure)
        
        # Add mousewheel binding for scrolling (cross-platform support)
        self.knowledge_canvas.bind("<MouseWheel>", self._on_mousewheel)  # Windows
        self.knowledge_canvas.bind("<Button-4>", self._on_mousewheel)    # Linux scroll up
        self.knowledge_canvas.bind("<Button-5>", self._on_mousewheel)    # Linux scroll down
        
        # For MacOS
        try:
            self.knowledge_canvas.bind("<MouseWheelEvent>", self._on_mousewheel)
        except:
            pass
    
    def _on_mousewheel(self, event):
        """Handle mousewheel scrolling in knowledge view"""
        # Cross-platform scroll handling
        if hasattr(event, 'num'):  # Linux
            if event.num == 4:
                self.knowledge_canvas.yview_scroll(-1, "units")
            elif event.num == 5:
                self.knowledge_canvas.yview_scroll(1, "units")
        elif hasattr(event, 'delta'):  # Windows
            if event.delta > 0:
                self.knowledge_canvas.yview_scroll(-1, "units")
            else:
                self.knowledge_canvas.yview_scroll(1, "units")
    
    def _on_knowledge_content_configure(self, event):
        """Update the canvas scroll region when content size changes"""
        self.knowledge_canvas.configure(scrollregion=self.knowledge_canvas.bbox("all"))
    
    def _on_knowledge_canvas_configure(self, event):
        """Update the width of the window to match canvas width and relayout tags"""
        self.knowledge_canvas.itemconfig(self.knowledge_canvas_window, width=event.width)
        
        # Relayout tags if we have any list bubbles
        if hasattr(self, '_list_bubbles'):
            for container, category, items in self._list_bubbles:
                if container.winfo_exists():
                    self._create_tag_chips(container, category, items)
    
    def show_knowledge_view(self):
        """Switch to knowledge view with proper cleanup"""
        try:
            if self.current_view == "knowledge":
                return
                    
            # Clean up any pending operations
            self._cleanup_pending_operations()
                    
            # Hide chat frame but keep input frame in its current position
            self.chat_frame.pack_forget()
            
            # Show knowledge frame
            self.knowledge_frame.pack(fill=tk.BOTH, expand=True)
            
            # Change button in input area
            self.send_button.pack_forget()
            self.close_button.pack(side=tk.RIGHT, padx=(5, 0))
            
            # Update state
            self.current_view = "knowledge"
            
            # Update status
            self.set_status("Viewing Knowledge", False)
        except Exception as e:
            self._show_error(f"Error showing knowledge view: {str(e)}")
            # Fall back to chat view
            self.show_chat_view()
    
    def show_chat_view(self):
        """Switch back to chat view with proper cleanup"""
        try:
            if self.current_view == "chat":
                return
                
            # Clean up any pending operations
            self._cleanup_pending_operations()
                
            # Properly handle UI repositioning
            self.knowledge_frame.pack_forget()
            
            # Remove all existing widgets from chat frame to avoid layout issues
            for widget in self.chat_frame.winfo_children():
                widget.pack_forget()
            
            # Re-add chat text with proper layout
            self.chat_text.pack(fill=tk.BOTH, expand=True)
            
            # Now show chat frame
            self.chat_frame.pack(fill=tk.BOTH, expand=True)
            
            # Change button in input area
            self.close_button.pack_forget()
            self.send_button.pack(side=tk.RIGHT, padx=(5, 0))
            
            # Update state
            self.current_view = "chat"
            
            # Process any knowledge edits
            self.process_knowledge_edits()
            
            # Update status
            self.set_status("Ready", False)
        except Exception as e:
            self._show_error(f"Error showing chat view: {str(e)}")
    
    def _cleanup_pending_operations(self):
        """Clean up any pending operations to prevent memory leaks"""
        try:
            # Clear any stored bubble references
            if hasattr(self, '_list_bubbles'):
                self._list_bubbles = []
                
            # Cancel any pending after() calls (requires tracking them)
            if hasattr(self, '_pending_after_ids'):
                for after_id in self._pending_after_ids:
                    try:
                        self.root.after_cancel(after_id)
                    except:
                        pass
                self._pending_after_ids = []
        except Exception as e:
            print(f"Error during cleanup: {e}")
    
    def create_knowledge_bubbles(self, user_data):
        """Create knowledge bubbles from user data"""
        # Clear existing bubbles
        for widget in self.knowledge_content.winfo_children():
            widget.destroy()
        
        # Add title
        title_label = tk.Label(
            self.knowledge_content,
            text="User Knowledge",
            bg="black",
            fg="white",
            font=("Helvetica", 12, "bold")
        )
        title_label.pack(pady=(10, 20))
        
        # Skip empty user data
        if not user_data or len(user_data) <= 1:  # Only contains name
            no_data_label = tk.Label(
                self.knowledge_content,
                text="No knowledge available about this user yet.",
                bg="black",
                fg="white",
                font=("Helvetica", 10)
            )
            no_data_label.pack(pady=10)
            return
        
        # Group categories
        basic_info = ["name", "age", "gender", "location", "profession"]
        preferences = ["likes", "dislikes", "interests", "hobbies"]
        context = ["family", "goals", "important_dates"]
        
        # Track processed keys
        processed_keys = set()
        
        # Add section header for Basic Information
        has_basic = any(key in user_data for key in basic_info)
        if has_basic:
            section_label = tk.Label(
                self.knowledge_content,
                text="Basic Information",
                bg="black",
                fg="white",
                font=("Helvetica", 11, "bold")
            )
            section_label.pack(anchor=tk.W, padx=10, pady=(10, 5))
            
            # Create bubbles for basic info
            for key in basic_info:
                if key in user_data and user_data[key]:
                    processed_keys.add(key)
                    self.create_knowledge_bubble(key, user_data[key])
        
        # Add section header for Preferences
        has_preferences = any(key in user_data for key in preferences)
        if has_preferences:
            section_label = tk.Label(
                self.knowledge_content,
                text="Preferences",
                bg="black",
                fg="white",
                font=("Helvetica", 11, "bold")
            )
            section_label.pack(anchor=tk.W, padx=10, pady=(20, 5))
            
            # Create bubbles for preferences
            for key in preferences:
                if key in user_data and user_data[key]:
                    processed_keys.add(key)
                    if isinstance(user_data[key], list):
                        self.create_list_bubble(key, user_data[key])
                    else:
                        self.create_knowledge_bubble(key, user_data[key])
        
        # Add section header for Context
        has_context = any(key in user_data for key in context)
        if has_context:
            section_label = tk.Label(
                self.knowledge_content,
                text="Context",
                bg="black",
                fg="white",
                font=("Helvetica", 11, "bold")
            )
            section_label.pack(anchor=tk.W, padx=10, pady=(20, 5))
            
            # Create bubbles for context
            for key in context:
                if key in user_data and user_data[key]:
                    processed_keys.add(key)
                    if isinstance(user_data[key], list):
                        self.create_list_bubble(key, user_data[key])
                    else:
                        self.create_knowledge_bubble(key, user_data[key])
        
        # Add section for other information
        remaining_keys = [key for key in user_data.keys() if key not in processed_keys]
        if remaining_keys:
            section_label = tk.Label(
                self.knowledge_content,
                text="Other Information",
                bg="black",
                fg="white",
                font=("Helvetica", 11, "bold")
            )
            section_label.pack(anchor=tk.W, padx=10, pady=(20, 5))
            
            # Create bubbles for remaining keys
            for key in remaining_keys:
                if user_data[key]:
                    if isinstance(user_data[key], list):
                        self.create_list_bubble(key, user_data[key])
                    else:
                        self.create_knowledge_bubble(key, user_data[key])
        
        # Add some padding at the bottom
        bottom_padding = tk.Frame(self.knowledge_content, height=20, bg="black")
        bottom_padding.pack(fill=tk.X)
    
    def create_knowledge_bubble(self, category, value):
        """Create a single knowledge bubble for simple values"""
        # Skip name as it's handled differently
        if category == 'name':
            return
            
        bubble = tk.Frame(self.knowledge_content, bg=self._get_color(self.jupiter_color, 0.7), 
                        relief=tk.SOLID, bd=1)
        bubble.pack(fill=tk.X, padx=10, pady=5)
        
        # Content frame with padding
        content_frame = tk.Frame(bubble, bg=bubble["bg"], padx=10, pady=10)
        content_frame.pack(fill=tk.X)
        
        # Category label
        category_label = tk.Label(
            content_frame, 
            text=category.capitalize(), 
            font=("Helvetica", 10, "bold"), 
            bg=bubble["bg"]
        )
        category_label.pack(anchor=tk.W)
        
        # Value label
        value_label = tk.Label(
            content_frame, 
            text=str(value), 
            bg=bubble["bg"],
            wraplength=350  # Allow wrapping for long text
        )
        value_label.pack(anchor=tk.W, pady=(2, 0))
        
        # Control buttons frame
        controls = tk.Frame(content_frame, bg=bubble["bg"])
        controls.pack(anchor=tk.SE, pady=(5, 0))
        
        # Edit button with pencil symbol ✏️
        edit_btn = tk.Button(
            controls, 
            text="✏️", 
            bg=bubble["bg"], 
            bd=0,
            font=("Helvetica", 9),
            command=lambda: self.edit_knowledge(category, value)
        )
        edit_btn.pack(side=tk.LEFT, padx=2)
        
        # Remove button with X symbol ❌
        remove_btn = tk.Button(
            controls, 
            text="❌", 
            bg=bubble["bg"], 
            bd=0,
            font=("Helvetica", 9),
            command=lambda: self.remove_knowledge(category)
        )
        remove_btn.pack(side=tk.LEFT, padx=2)
    
    def create_list_bubble(self, category, items):
        """Create a bubble for list values with tag/chip display that adapts to container width"""
        bubble = tk.Frame(self.knowledge_content, bg=self._get_color(self.jupiter_color, 0.7), 
                        relief=tk.SOLID, bd=1)
        bubble.pack(fill=tk.X, padx=10, pady=5)
        
        # Store info for tag relayout
        bubble.category = category
        bubble.items = items
        
        # Content frame with padding
        content_frame = tk.Frame(bubble, bg=bubble["bg"], padx=10, pady=10)
        content_frame.pack(fill=tk.X)
        
        # Header with category name
        header = tk.Frame(content_frame, bg=bubble["bg"])
        header.pack(fill=tk.X, pady=(0, 5))
        
        category_label = tk.Label(
            header, 
            text=category.capitalize(), 
            font=("Helvetica", 10, "bold"), 
            bg=bubble["bg"]
        )
        category_label.pack(side=tk.LEFT)
        
        # Container for tag chips
        tags_container = tk.Frame(content_frame, bg=bubble["bg"])
        tags_container.pack(fill=tk.X)
        
        # Tags will be created in an update method that can be called on resize
        self._create_tag_chips(tags_container, category, items)
        
        # Add new item button in a separate row
        button_row = tk.Frame(content_frame, bg=bubble["bg"])
        button_row.pack(fill=tk.X, pady=(2, 0))
        
        add_btn = tk.Button(
            button_row, 
            text="➕ Add Item", 
            bg="#333", 
            fg="white",
            relief=tk.FLAT,
            padx=5,
            pady=2,
            font=("Helvetica", 8),
            command=lambda: self.add_list_item(category)
        )
        add_btn.pack(side=tk.LEFT, pady=2)
        
        # Control buttons frame for the entire list
        controls = tk.Frame(content_frame, bg=bubble["bg"])
        controls.pack(anchor=tk.SE, pady=(5, 0))
        
        # Remove all button with X symbol ❌
        remove_btn = tk.Button(
            controls, 
            text="❌ Remove All", 
            bg=bubble["bg"], 
            bd=0,
            font=("Helvetica", 8),
            command=lambda: self.remove_knowledge(category)
        )
        remove_btn.pack(side=tk.LEFT, padx=2)
        
        # Register this bubble for resize updates
        if not hasattr(self, '_list_bubbles'):
            self._list_bubbles = []
        self._list_bubbles.append((tags_container, category, items))
        
        return bubble
    
    def _create_tag_chips(self, container, category, items):
        """Create tag chips in the container with dynamic layout"""
        # Clear existing tags
        for widget in container.winfo_children():
            widget.destroy()
        
        # Get actual container width
        container.update_idletasks()  # Ensure geometry is updated
        try:
            # Get actual width or use window width minus padding
            actual_width = container.winfo_width()
            if actual_width < 50:  # If not properly initialized
                actual_width = self.root.winfo_width() - 80
        except:
            # Fallback to a reasonable default
            actual_width = 320
        
        # Frame to hold each row of tags
        current_row = tk.Frame(container, bg=container["bg"])
        current_row.pack(fill=tk.X, pady=(0, 2))
        
        row_width = 0
        max_width = max(200, actual_width - 20)  # Minimum reasonable width with padding
        
        # Create a chip for each item
        for item in items:
            # Create test label to measure width
            test_label = tk.Label(self.root, text=item)
            item_width = test_label.winfo_reqwidth() + 35  # Add space for X button and padding
            test_label.destroy()
            
            # Check if we need a new row
            if row_width + item_width > max_width:
                current_row = tk.Frame(container, bg=container["bg"])
                current_row.pack(fill=tk.X, pady=(0, 2))
                row_width = 0
            
            # Create tag chip
            tag_chip = tk.Frame(current_row, bg="#555", bd=0, padx=5, pady=2)
            tag_chip.pack(side=tk.LEFT, padx=2, pady=2)
            
            # Tag text
            tag_text = tk.Label(tag_chip, text=item, fg="white", bg="#555")
            tag_text.pack(side=tk.LEFT)
            
            # Remove button for tag
            remove_tag_btn = tk.Button(
                tag_chip, 
                text="×", 
                bg="#555", 
                fg="white", 
                bd=0,
                font=("Helvetica", 9),
                command=lambda i=item: self.remove_list_item(category, i)
            )
            remove_tag_btn.pack(side=tk.LEFT)
            
            # Update row width
            row_width += item_width
    
    def edit_knowledge(self, category, current_value):
        """Edit a knowledge item with thread safety"""
        # Different editors based on category type
        if category in ['important_dates']:
            new_value = self.show_date_picker(category, current_value)
        elif category in ['age']:
            new_value = self.show_number_editor(category, current_value)
        else:
            new_value = self.show_text_editor(category, current_value)
        
        if new_value is not None and new_value != current_value:
            # Queue the edit for processing
            self.knowledge_edit_queue.put({
                "action": "edit",
                "category": category,
                "old_value": current_value,
                "new_value": new_value
            })
            
            # Update UI using a threadsafe approach
            self.root.after(0, lambda: self._update_knowledge_ui(category, current_value, new_value))
    
    def _update_knowledge_ui(self, category, old_value, new_value):
        """Thread-safe method to update knowledge UI after edit"""
        try:
            for widget in self.knowledge_content.winfo_children():
                if isinstance(widget, tk.Frame) and widget.winfo_children():
                    for child in widget.winfo_children():
                        if isinstance(child, tk.Frame):
                            # Look for category label
                            for subchild in child.winfo_children():
                                if isinstance(subchild, tk.Label) and subchild.cget("text") == category.capitalize():
                                    # Find value label
                                    for value_widget in child.winfo_children():
                                        if isinstance(value_widget, tk.Label) and value_widget.cget("text") == str(old_value):
                                            value_widget.config(text=str(new_value))
                                            return
        except Exception as e:
            print(f"Error updating knowledge UI: {e}")
    
    def remove_knowledge(self, category):
        """Remove a knowledge item with thread safety"""
        # Ask for confirmation
        if not self.show_confirm_dialog(f"Remove {category.capitalize()}?", 
                                       f"Are you sure you want to remove {category.capitalize()}?"):
            return
        
        # Queue the removal for processing
        self.knowledge_edit_queue.put({
            "action": "remove",
            "category": category
        })
        
        # Use thread-safe approach to update UI
        self.root.after(0, lambda: self._remove_knowledge_ui(category))
    
    def _remove_knowledge_ui(self, category):
        """Thread-safe method to update UI after knowledge removal"""
        try:
            for widget in self.knowledge_content.winfo_children():
                if isinstance(widget, tk.Frame):
                    # Check if this frame contains the category we want to remove
                    for child in widget.winfo_children():
                        if isinstance(child, tk.Frame):
                            for subchild in child.winfo_children():
                                if isinstance(subchild, tk.Label) and subchild.cget("text") == category.capitalize():
                                    # Found the bubble to remove
                                    widget.destroy()
                                    return
        except Exception as e:
            print(f"Error removing knowledge UI element: {e}")
    
    def add_list_item(self, category):
        """Add an item to a list with thread safety"""
        new_item = self.show_text_editor(f"Add to {category}", "")
        if new_item:
            # Queue the addition for processing
            self.knowledge_edit_queue.put({
                "action": "add_list_item",
                "category": category,
                "value": new_item
            })
            
            # Update UI - using a safer approach
            self.root.after(10, self.refresh_knowledge_view)
    
    def remove_list_item(self, category, item):
        """Remove an item from a list with thread safety"""
        # Queue the removal for processing
        self.knowledge_edit_queue.put({
            "action": "remove_list_item",
            "category": category,
            "value": item
        })
        
        # Update UI using thread-safe approach
        self.root.after(10, self.refresh_knowledge_view)
    
    def refresh_knowledge_view(self):
        """Thread-safe method to refresh the knowledge view"""
        try:
            if self.knowledge_callback and callable(self.knowledge_callback):
                self.knowledge_callback()
        except Exception as e:
            print(f"Error refreshing knowledge view: {e}")
    
    def show_text_editor(self, category, current_value):
        """Show an improved dialog for editing text values"""
        # Create custom dialog with better keyboard support
        dialog = tk.Toplevel(self.root)
        dialog.title(f"Edit {category.capitalize()}")
        dialog.grab_set()  # Modal window
        dialog.resizable(False, False)
        
        # Center dialog on parent window
        dialog_width = 350
        dialog_height = 150
        
        # Get parent window position and size
        root_x = self.root.winfo_rootx()
        root_y = self.root.winfo_rooty()
        root_width = self.root.winfo_width()
        root_height = self.root.winfo_height()
        
        # Calculate position (centered on parent)
        x_position = root_x + (root_width - dialog_width) // 2
        y_position = root_y + (root_height - dialog_height) // 2
        
        # Ensure dialog appears on screen if parent is near edge
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        if x_position + dialog_width > screen_width:
            x_position = screen_width - dialog_width - 10
        if y_position + dialog_height > screen_height:
            y_position = screen_height - dialog_height - 10
        
        dialog.geometry(f"{dialog_width}x{dialog_height}+{x_position}+{y_position}")
        
        # Instruction label
        tk.Label(
            dialog, 
            text=f"Enter new value for {category.capitalize()}:",
            anchor="w", 
            pady=10
        ).pack(fill=tk.X, padx=20)
        
        # Text entry
        entry = tk.Entry(dialog, width=40)
        entry.pack(padx=20, pady=5)
        entry.insert(0, current_value)
        entry.select_range(0, tk.END)  # Select all text
        entry.focus_set()  # Set focus to entry
        
        # Result variable
        result = [None]
        
        # Handlers
        def on_ok():
            result[0] = entry.get()
            dialog.destroy()
            
        def on_cancel():
            dialog.destroy()
        
        # Keyboard handling
        def on_key(event):
            if event.keysym == "Return":
                on_ok()
            elif event.keysym == "Escape":
                on_cancel()
        
        dialog.bind("<Key>", on_key)
        
        # Buttons
        button_frame = tk.Frame(dialog)
        button_frame.pack(fill=tk.X, padx=20, pady=15)
        
        cancel_btn = tk.Button(button_frame, text="Cancel", command=on_cancel)
        cancel_btn.pack(side=tk.RIGHT, padx=5)
        
        ok_btn = tk.Button(button_frame, text="OK", command=on_ok)
        ok_btn.pack(side=tk.RIGHT, padx=5)
        
        # Wait for dialog to close
        dialog.wait_window()
        
        return result[0]
    
    def show_number_editor(self, category, current_value):
        """Show dialog for editing number values"""
        try:
            current_number = int(current_value)
        except (ValueError, TypeError):
            current_number = 0
            
        result = simpledialog.askinteger(
            f"Edit {category.capitalize()}", 
            f"Enter new value for {category.capitalize()}:",
            initialvalue=current_number,
            parent=self.root
        )
        
        return str(result) if result is not None else None
    
    def show_date_picker(self, category, current_value):
        """Show dialog for editing date values"""
        # For simplicity, we'll use a text editor but could be enhanced with a proper date picker
        return self.show_text_editor(category, current_value)
    
    def show_confirm_dialog(self, title, message):
        """Show an improved confirmation dialog"""
        dialog = tk.Toplevel(self.root)
        dialog.title(title)
        dialog.grab_set()  # Modal window
        dialog.resizable(False, False)
        
        # Center dialog on parent window
        dialog_width = 300
        dialog_height = 120
        
        # Get parent window position and size
        root_x = self.root.winfo_rootx()
        root_y = self.root.winfo_rooty()
        root_width = self.root.winfo_width()
        root_height = self.root.winfo_height()
        
        # Calculate position (centered on parent)
        x_position = root_x + (root_width - dialog_width) // 2
        y_position = root_y + (root_height - dialog_height) // 2
        
        # Ensure dialog appears on screen if parent is near edge
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        if x_position + dialog_width > screen_width:
            x_position = screen_width - dialog_width - 10
        if y_position + dialog_height > screen_height:
            y_position = screen_height - dialog_height - 10
        
        dialog.geometry(f"{dialog_width}x{dialog_height}+{x_position}+{y_position}")
        
        # Message
        msg_label = tk.Label(dialog, text=message, wraplength=280, pady=10)
        msg_label.pack(fill=tk.X, padx=10)
        
        # Result variable
        result = [False]
        
        # Handlers
        def on_yes():
            result[0] = True
            dialog.destroy()
            
        def on_no():
            dialog.destroy()
        
        # Keyboard handling
        def on_key(event):
            if event.keysym == "Return":
                on_yes()
            elif event.keysym == "Escape":
                on_no()
        
        dialog.bind("<Key>", on_key)
        
        # Buttons frame
        btn_frame = tk.Frame(dialog)
        btn_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Buttons
        no_btn = tk.Button(
            btn_frame,
            text="No",
            bg="#333",
            fg="white",
            relief=tk.FLAT,
            padx=10,
            pady=2,
            command=on_no
        )
        no_btn.pack(side=tk.RIGHT, padx=5)
        
        yes_btn = tk.Button(
            btn_frame,
            text="Yes",
            bg="#333",
            fg="white",
            relief=tk.FLAT,
            padx=10,
            pady=2,
            command=on_yes
        )
        yes_btn.pack(side=tk.RIGHT, padx=5)
        
        # Set initial focus to the No button (safer default)
        no_btn.focus_set()
        
        # Wait for dialog to close
        dialog.wait_window()
        
        return result[0]
    
    def _show_error(self, message):
        """Show error message to user in a more user-friendly way"""
        try:
            print(f"GUI Error: {message}")
            
            # Use a statusbar message first for non-critical errors
            self.set_status(f"Error: {message[:50]}...", False)
            
            # For critical errors, show dialog
            if "critical" in message.lower() or "failed" in message.lower():
                self.root.after(0, lambda: self._show_error_dialog("Error", message))
        except:
            # Last resort if even error showing fails
            print(f"Critical GUI error: {message}")
    
    def _show_error_dialog(self, title, message):
        """Show an error dialog to the user"""
        try:
            dialog = tk.Toplevel(self.root)
            dialog.title(title)
            dialog.grab_set()
            
            # Setup
            dialog_width = 400
            dialog_height = 150
            
            # Center on parent
            root_x = self.root.winfo_rootx()
            root_y = self.root.winfo_rooty()
            root_width = self.root.winfo_width()
            root_height = self.root.winfo_height()
            
            x_position = root_x + (root_width - dialog_width) // 2
            y_position = root_y + (root_height - dialog_height) // 2
            
            dialog.geometry(f"{dialog_width}x{dialog_height}+{x_position}+{y_position}")
            
            # Error icon (use a text symbol since we might not have an image)
            header = tk.Frame(dialog, bg="#FFF0F0")
            header.pack(fill=tk.X)
            
            tk.Label(header, text="⚠️", font=("Arial", 24), bg="#FFF0F0").pack(side=tk.LEFT, padx=15, pady=10)
            tk.Label(header, text="An error occurred", font=("Arial", 12, "bold"), bg="#FFF0F0").pack(side=tk.LEFT, pady=10)
            
            # Error message
            message_frame = tk.Frame(dialog)
            message_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)
            
            msg = tk.Label(message_frame, text=message, wraplength=350, justify="left", anchor="w")
            msg.pack(fill=tk.BOTH, expand=True)
            
            # Close button
            btn_frame = tk.Frame(dialog)
            btn_frame.pack(fill=tk.X, padx=15, pady=(0, 10))
            
            close_btn = tk.Button(btn_frame, text="Close", width=10, command=dialog.destroy)
            close_btn.pack(side=tk.RIGHT)
            
            # Handle Escape key
            dialog.bind("<Escape>", lambda e: dialog.destroy())
            
            # Set focus to button
            close_btn.focus_set()
        except Exception as e:
            print(f"Critical error showing error dialog: {e}")
    
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
        
        # Always display user message regardless of exit command
        # This ensures the message appears in the chat window
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
    
    def process_knowledge_edits(self):
        """Process all queued knowledge edits with error handling"""
        edits_processed = 0
        errors = 0
        
        try:
            # Process all edits in the queue
            while not self.knowledge_edit_queue.empty():
                try:
                    edit = self.knowledge_edit_queue.get()
                    # Print for debugging
                    print(f"Processing knowledge edit: {edit}")
                    
                    # In a real implementation, this would be passed to the chat engine
                    # which would update the user model
                    edits_processed += 1
                except Exception as e:
                    errors += 1
                    print(f"Error processing edit {edits_processed + errors}: {e}")
                    
            # If we had errors, show a status message
            if errors > 0:
                self.set_status(f"Warning: {errors} edit(s) failed to process", False)
        except Exception as e:
            self._show_error(f"Error processing knowledge edits: {e}")