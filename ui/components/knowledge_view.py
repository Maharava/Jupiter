import tkinter as tk
import logging
from ui.utils.ui_helpers import get_color

# Set up logging
logger = logging.getLogger("jupiter.gui.knowledge_view")

class KnowledgeView:
    """Knowledge view component for Jupiter GUI"""
    
    def __init__(self, parent, jupiter_color="yellow", clean_callback=None):
        """
        Initialize knowledge view component
        
        Args:
            parent: Parent tkinter container
            jupiter_color: Color for knowledge bubbles
            clean_callback: Callback for cleanup operations
        """
        self.parent = parent
        self.jupiter_color = jupiter_color
        self.clean_callback = clean_callback
        
        try:
            # Create knowledge frame
            self.frame = tk.Frame(parent, bg="black")
            
            # Create canvas with scrollbar for resizable content
            self.knowledge_canvas = tk.Canvas(self.frame, bg="black", highlightthickness=0)
            scrollbar = tk.Scrollbar(self.frame, orient="vertical", command=self.knowledge_canvas.yview)
            
            # Configure canvas scrolling
            self.knowledge_canvas.configure(yscrollcommand=scrollbar.set)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            self.knowledge_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            
            # Create frame inside canvas for content
            self.knowledge_content = tk.Frame(self.knowledge_canvas, bg="black")
            self.knowledge_canvas_window = self.knowledge_canvas.create_window(
                (0, 0), window=self.knowledge_content, anchor="nw"
            )
            
            # Add resize listeners
            self.knowledge_content.bind("<Configure>", self._on_content_configure)
            self.knowledge_canvas.bind("<Configure>", self._on_canvas_configure)
            
            # Add mousewheel binding for scrolling
            self._bind_mousewheel()
            
            # List bubbles tracking
            self._list_bubbles = []
            
        except Exception as e:
            logger.error(f"Error initializing knowledge view: {e}")
    
    def _bind_mousewheel(self):
        """Set up mousewheel scrolling (cross-platform) with error handling"""
        try:
            if not hasattr(self, 'knowledge_canvas') or not self.knowledge_canvas:
                return
                
            self.knowledge_canvas.bind("<MouseWheel>", self._on_mousewheel)  # Windows
            self.knowledge_canvas.bind("<Button-4>", self._on_mousewheel)    # Linux scroll up
            self.knowledge_canvas.bind("<Button-5>", self._on_mousewheel)    # Linux scroll down
            
            # For MacOS
            try:
                self.knowledge_canvas.bind("<MouseWheelEvent>", self._on_mousewheel)
            except:
                pass
                
        except Exception as e:
            logger.error(f"Error binding mousewheel events: {e}")
    
    def _on_mousewheel(self, event):
        """Handle mousewheel scrolling in knowledge view (cross-platform) with error handling"""
        try:
            if not hasattr(self, 'knowledge_canvas') or not self.knowledge_canvas:
                return
                
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
                    
        except Exception as e:
            logger.error(f"Error handling mousewheel event: {e}")
    
    def _on_content_configure(self, event):
        """Update the canvas scroll region when content size changes with error handling"""
        try:
            if hasattr(self, 'knowledge_canvas') and self.knowledge_canvas:
                self.knowledge_canvas.configure(scrollregion=self.knowledge_canvas.bbox("all"))
        except Exception as e:
            logger.error(f"Error updating scroll region: {e}")
    
    def _on_canvas_configure(self, event):
        """Update the width of the window to match canvas width and relayout tags with error handling"""
        try:
            if not hasattr(self, 'knowledge_canvas') or not self.knowledge_canvas:
                return
                
            # Update window width
            self.knowledge_canvas.itemconfig(self.knowledge_canvas_window, width=event.width)
            
            # Relayout tags
            for container, category, items in self._list_bubbles:
                if hasattr(container, 'winfo_exists') and container.winfo_exists():
                    self._create_tag_chips(container, category, items)
                    
        except Exception as e:
            logger.error(f"Error handling canvas resize: {e}")
    
    def create_knowledge_bubbles(self, user_data):
        """
        Create knowledge bubbles from user data with proper error handling
        
        Args:
            user_data: Dictionary of user knowledge data
        """
        try:
            if not hasattr(self, 'knowledge_content') or not self.knowledge_content:
                logger.error("Cannot create knowledge bubbles - content frame not available")
                return
                
            # Clear existing bubbles
            for widget in self.knowledge_content.winfo_children():
                try:
                    widget.destroy()
                except:
                    pass
            
            # Clear list bubble tracking
            self._list_bubbles = []
            
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
            
        except Exception as e:
            logger.error(f"Error creating knowledge bubbles: {e}")
    
    def create_knowledge_bubble(self, category, value):
        """
        Create a single knowledge bubble for simple values with proper error handling
        
        Args:
            category: Knowledge category
            value: Knowledge value
        
        Returns:
            Frame: The bubble frame or None on error
        """
        try:
            # Skip name as it's handled differently
            if category == 'name':
                return None
                
            # Check if knowledge content exists
            if not hasattr(self, 'knowledge_content') or not self.knowledge_content:
                logger.error("Cannot create knowledge bubble - content frame not available")
                return None
                
            bubble = tk.Frame(
                self.knowledge_content, 
                bg=get_color(self.jupiter_color, 0.7), 
                relief=tk.SOLID, 
                bd=1
            )
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
                command=lambda c=category, v=value: self._show_edit_dialog(c, v)
            )
            edit_btn.pack(side=tk.LEFT, padx=2)
            
            # Remove button with X symbol ❌
            remove_btn = tk.Button(
                controls, 
                text="❌", 
                bg=bubble["bg"], 
                bd=0,
                font=("Helvetica", 9),
                command=lambda c=category: self._show_remove_dialog(c)
            )
            remove_btn.pack(side=tk.LEFT, padx=2)
            
            return bubble
            
        except Exception as e:
            logger.error(f"Error creating knowledge bubble for {category}: {e}")
            return None
    
    def create_list_bubble(self, category, items):
        """
        Create a bubble for list values with tag/chip display and proper error handling
        
        Args:
            category: Knowledge category
            items: List of knowledge values
            
        Returns:
            Frame: The bubble frame or None on error
        """
        try:
            # Check if knowledge content exists
            if not hasattr(self, 'knowledge_content') or not self.knowledge_content:
                logger.error("Cannot create list bubble - content frame not available")
                return None
                
            bubble = tk.Frame(
                self.knowledge_content, 
                bg=get_color(self.jupiter_color, 0.7), 
                relief=tk.SOLID, 
                bd=1
            )
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
            
            # Create tag chips
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
                command=lambda c=category: self._show_add_item_dialog(c)
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
                command=lambda c=category: self._show_remove_dialog(c)
            )
            remove_btn.pack(side=tk.LEFT, padx=2)
            
            # Register this bubble for resize updates
            self._list_bubbles.append((tags_container, category, items))
            
            return bubble
            
        except Exception as e:
            logger.error(f"Error creating list bubble for {category}: {e}")
            return None
    
    def _create_tag_chips(self, container, category, items):
        """
        Create tag chips in the container with dynamic layout and proper error handling
        
        Args:
            container: Container frame for tags
            category: Knowledge category
            items: List of values to display as tags
        """
        try:
            # Check if container still exists
            if not hasattr(container, 'winfo_exists') or not container.winfo_exists():
                logger.error("Cannot create tag chips - container no longer exists")
                return
                
            # Clear existing tags
            for widget in container.winfo_children():
                try:
                    widget.destroy()
                except:
                    pass
            
            # Get actual container width
            container.update_idletasks()  # Ensure geometry is updated
            try:
                # Get actual width or use window width minus padding
                actual_width = container.winfo_width()
                if actual_width < 50:  # If not properly initialized
                    actual_width = self.parent.winfo_width() - 80
            except Exception as e:
                logger.debug(f"Error getting container width: {e}")
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
                test_label = tk.Label(self.parent, text=item)
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
                    command=lambda c=category, i=item: self._show_remove_item_dialog(c, i)
                )
                remove_tag_btn.pack(side=tk.LEFT)
                
                # Update row width
                row_width += item_width
                
        except Exception as e:
            logger.error(f"Error creating tag chips: {e}")
    
    def _show_edit_dialog(self, category, current_value):
        """
        Show dialog to edit a knowledge item with proper error handling
        
        Args:
            category: Knowledge category
            current_value: Current value
        """
        try:
            # Different editors based on category type
            if category in ['important_dates']:
                new_value = self._show_date_picker(category, current_value)
            elif category in ['age']:
                new_value = self._show_number_editor(category, current_value)
            else:
                new_value = self._show_text_editor(category, current_value)
            
            if new_value is not None and new_value != current_value:
                logger.info(f"Editing knowledge: {category} from '{current_value}' to '{new_value}'")
                # Call the parent to handle the edit
                if self.clean_callback and callable(self.clean_callback):
                    self.clean_callback()
                    
        except Exception as e:
            logger.error(f"Error showing edit dialog for {category}: {e}")
    
    def _show_remove_dialog(self, category):
        """
        Show dialog to confirm removing a knowledge item with proper error handling
        
        Args:
            category: Knowledge category
        """
        try:
            # Ask for confirmation
            if not self._show_confirm_dialog(
                f"Remove {category.capitalize()}?", 
                f"Are you sure you want to remove {category.capitalize()}?"
            ):
                return
            
            logger.info(f"Removing knowledge category: {category}")
            # Call the parent to handle the removal
            if self.clean_callback and callable(self.clean_callback):
                self.clean_callback()
                
        except Exception as e:
            logger.error(f"Error showing remove dialog for {category}: {e}")
    
    def _show_add_item_dialog(self, category):
        """
        Show dialog to add an item to a list with proper error handling
        
        Args:
            category: Knowledge category
        """
        try:
            new_item = self._show_text_editor(f"Add to {category}", "")
            if new_item:
                logger.info(f"Adding item to {category}: {new_item}")
                # Call the parent to handle the addition
                if self.clean_callback and callable(self.clean_callback):
                    self.clean_callback()
                    
        except Exception as e:
            logger.error(f"Error showing add item dialog for {category}: {e}")
    
    def _show_remove_item_dialog(self, category, item):
        """
        Show dialog to confirm removing an item from a list with proper error handling
        
        Args:
            category: Knowledge category
            item: The item to remove
        """
        try:
            # Ask for confirmation
            if not self._show_confirm_dialog(
                f"Remove Item", 
                f"Remove '{item}' from {category.capitalize()}?"
            ):
                return
                
            logger.info(f"Removing item from {category}: {item}")
            # Call the parent to handle the removal
            if self.clean_callback and callable(self.clean_callback):
                self.clean_callback()
                
        except Exception as e:
            logger.error(f"Error removing item {item} from {category}: {e}")
    
    def _show_text_editor(self, category, current_value):
        """
        Show an improved dialog for editing text values with proper error handling
        
        Args:
            category: Knowledge category
            current_value: Current value
            
        Returns:
            str: New value or None if cancelled
        """
        try:
            # Check if parent window exists
            if not hasattr(self, 'parent') or not self.parent or not self.parent.winfo_exists():
                logger.error("Cannot show text editor - parent window not available")
                return None
                
            # Create custom dialog with better keyboard support
            dialog = tk.Toplevel(self.parent)
            dialog.title(f"Edit {category.capitalize()}")
            dialog.grab_set()  # Modal window
            dialog.resizable(False, False)
            
            # Center dialog on parent window
            dialog_width = 350
            dialog_height = 150
            
            # Get parent window position and size
            root_x = self.parent.winfo_rootx()
            root_y = self.parent.winfo_rooty()
            root_width = self.parent.winfo_width()
            root_height = self.parent.winfo_height()
            
            # Calculate position (centered on parent)
            x_position = root_x + (root_width - dialog_width) // 2
            y_position = root_y + (root_height - dialog_height) // 2
            
            # Ensure dialog appears on screen if parent is near edge
            screen_width = self.parent.winfo_screenwidth()
            screen_height = self.parent.winfo_screenheight()
            
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
            
        except Exception as e:
            logger.error(f"Error showing text editor for {category}: {e}")
            return None
    
    def _show_number_editor(self, category, current_value):
        """
        Show dialog for editing number values with proper error handling
        
        Args:
            category: Knowledge category
            current_value: Current value
            
        Returns:
            str: New value or None if cancelled
        """
        try:
            # Check if parent window exists
            if not hasattr(self, 'parent') or not self.parent or not self.parent.winfo_exists():
                logger.error("Cannot show number editor - parent window not available")
                return None
                
            try:
                current_number = int(current_value)
            except (ValueError, TypeError):
                current_number = 0
                
            # Create custom dialog with number entry
            dialog = tk.Toplevel(self.parent)
            dialog.title(f"Edit {category.capitalize()}")
            dialog.grab_set()  # Modal window
            dialog.resizable(False, False)
            
            # Center dialog on parent
            dialog_width = 300
            dialog_height = 150
            
            # Position calculation
            x_position = self.parent.winfo_rootx() + (self.parent.winfo_width() - dialog_width) // 2
            y_position = self.parent.winfo_rooty() + (self.parent.winfo_height() - dialog_height) // 2
            
            dialog.geometry(f"{dialog_width}x{dialog_height}+{x_position}+{y_position}")
            
            # Instruction label
            tk.Label(
                dialog, 
                text=f"Enter new value for {category.capitalize()}:",
                anchor="w", 
                pady=10
            ).pack(fill=tk.X, padx=20)
            
            # Number entry with validation
            vcmd = (dialog.register(lambda P: P.isdigit() or P == ""), '%P')
            entry = tk.Entry(dialog, width=40, validate='key', validatecommand=vcmd)
            entry.pack(padx=20, pady=5)
            entry.insert(0, str(current_number))
            entry.select_range(0, tk.END)
            entry.focus_set()
            
            # Result variable
            result = [None]
            
            # Handlers
            def on_ok():
                try:
                    value = entry.get()
                    if value:
                        result[0] = value
                except ValueError:
                    pass
                dialog.destroy()
                
            def on_cancel():
                dialog.destroy()
            
            # Keyboard handling
            dialog.bind("<Return>", lambda e: on_ok())
            dialog.bind("<Escape>", lambda e: on_cancel())
            
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
            
        except Exception as e:
            logger.error(f"Error showing number editor for {category}: {e}")
            return None
    
    def _show_date_picker(self, category, current_value):
        """
        Show dialog for editing date values (simplified version) with proper error handling
        
        Args:
            category: Knowledge category
            current_value: Current value
            
        Returns:
            str: New value or None if cancelled
        """
        try:
            # For simplicity, we'll use a text editor but could be enhanced with a proper date picker
            return self._show_text_editor(category, current_value)
        except Exception as e:
            logger.error(f"Error showing date picker for {category}: {e}")
            return None
    
    def _show_confirm_dialog(self, title, message):
        """
        Show an improved confirmation dialog with proper error handling
        
        Args:
            title: Dialog title
            message: Dialog message
            
        Returns:
            bool: True if confirmed, False if cancelled
        """
        try:
            # Check if parent window exists
            if not hasattr(self, 'parent') or not self.parent or not self.parent.winfo_exists():
                logger.error("Cannot show confirm dialog - parent window not available")
                return False
                
            # Create dialog
            dialog = tk.Toplevel(self.parent)
            dialog.title(title)
            dialog.grab_set()  # Modal window
            dialog.resizable(False, False)
            
            # Center dialog on parent window
            dialog_width = 300
            dialog_height = 120
            
            x_position = self.parent.winfo_rootx() + (self.parent.winfo_width() - dialog_width) // 2
            y_position = self.parent.winfo_rooty() + (self.parent.winfo_height() - dialog_height) // 2
            
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
            dialog.bind("<Return>", lambda e: on_yes())
            dialog.bind("<Escape>", lambda e: on_no())
            
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
            
        except Exception as e:
            logger.error(f"Error showing confirm dialog: {e}")
            return False
    
    def pack(self, **kwargs):
        """Pack the knowledge view into its parent with proper error handling"""
        try:
            if hasattr(self, 'frame') and self.frame and self.frame.winfo_exists():
                self.frame.pack(**kwargs)
        except Exception as e:
            logger.error(f"Error packing knowledge view: {e}")
    
    def grid(self, **kwargs):
        """Grid the knowledge view into its parent with proper error handling"""
        try:
            if hasattr(self, 'frame') and self.frame and self.frame.winfo_exists():
                self.frame.grid(**kwargs)
        except Exception as e:
            logger.error(f"Error gridding knowledge view: {e}")
    
    def pack_forget(self):
        """Remove the knowledge view from the parent's layout with proper error handling"""
        try:
            if hasattr(self, 'frame') and self.frame and self.frame.winfo_exists():
                self.frame.pack_forget()
        except Exception as e:
            logger.error(f"Error hiding knowledge view: {e}")