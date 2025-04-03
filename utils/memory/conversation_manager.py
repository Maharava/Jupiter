import os
import json
import uuid
import time
from datetime import datetime
from typing import List, Dict, Any, Optional, Union
import tiktoken  # For token counting
from models.user_data_manager import UserDataManager

class ConversationManager:
    """
    Manages conversations for Jupiter, handling both short-term context
    and long-term persistent storage of conversations with user tracking.
    """
    
    def __init__(self, config, user_data_manager):
        """
        Initialize the ConversationManager.
        
        Args:
            config: Application configuration
            user_data_manager: Reference to the user data manager
        """
        self.config = config
        self.user_data_manager = user_data_manager
        
        # Initialize storage paths
        self.storage_path = os.path.join(config['paths']['data_folder'], 'conversations')
        os.makedirs(self.storage_path, exist_ok=True)
        
        # Initialize current context
        self.context = []
        self.current_conversation_id = None
        self.max_context_messages = config.get('chat', {}).get('max_history_messages', 100)
        
        # Load tokenizer for counting context length
        self.tokenizer = tiktoken.get_encoding("cl100k_base")  # Used by modern models
        
        # Cache for active conversations
        self.conversation_cache = {}
    
    # ===== Context Management =====
    
    def start_conversation(self, participants: List[str] = None) -> str:
        """
        Start a new conversation and return its ID.
        
        Args:
            participants: List of user_ids participating in the conversation
            
        Returns:
            conversation_id: The UUID of the new conversation
        """
        if participants is None:
            # If no participants provided, use current user
            current_user_id = self.user_data_manager.current_user.get('user_id')
            participants = [current_user_id] if current_user_id else []
        
        conversation_id = str(uuid.uuid4())
        timestamp = int(time.time())
        
        conversation = {
            "conversation_id": conversation_id,
            "created_at": timestamp,
            "title": f"Conversation on {datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M')}",
            "participants": participants,
            "messages": []
        }
        
        # Save the new conversation
        self._save_conversation(conversation)
        
        # Set as current conversation
        self.current_conversation_id = conversation_id
        self.context = []
        
        # Add this conversation to each participant's history
        for user_id in participants:
            self._add_conversation_to_user(user_id, conversation_id)
        
        return conversation_id
    
    def add_to_context(self, sender_id: str, content: str, message_type: str) -> None:
        """
        Add a message to the current context and save to permanent storage.
        
        Args:
            sender_id: ID of the message sender (user_id or "jupiter")
            content: The message content
            message_type: "user" or "assistant"
        """
        if not self.current_conversation_id:
            self.start_conversation()
        
        message = {
            "message_id": str(uuid.uuid4()),
            "timestamp": int(time.time()),
            "sender_id": sender_id,
            "content": content,
            "type": message_type
        }
        
        # Add to context
        self.context.append(message)
        
        # Trim context if needed
        if len(self.context) > self.max_context_messages:
            self.context = self.context[-self.max_context_messages:]
        
        # Save to permanent storage
        self._add_message_to_conversation(self.current_conversation_id, message)
    
    def truncate_context(self, token_limit: int, system_prompt_size: int) -> List[Dict[str, Any]]:
        """
        Smartly truncate context to fit within token limit, accounting for system prompt.
        
        Args:
            token_limit: Maximum tokens allowed
            system_prompt_size: Size of the system prompt in tokens
            
        Returns:
            List of messages that fit within the token limit
        """
        # Reserve tokens for system prompt and some buffer
        available_tokens = token_limit - system_prompt_size - 100  # Buffer of 100 tokens
        
        if available_tokens <= 0:
            return []
        
        # Count tokens for each message, starting from most recent
        token_count = 0
        included_messages = []
        
        for message in reversed(self.context):
            message_tokens = len(self.tokenizer.encode(message["content"]))
            
            if token_count + message_tokens <= available_tokens:
                included_messages.insert(0, message)  # Add to start to maintain order
                token_count += message_tokens
            else:
                break
        
        return included_messages
    
    def prepare_for_llm(self, user_input: str, system_prompt: str, token_limit: int) -> str:
        """
        Prepare the full message for the LLM including context.
        
        Args:
            user_input: Current user input
            system_prompt: System prompt text
            token_limit: Maximum tokens allowed for the model
            
        Returns:
            Formatted message for LLM with history and user input
        """
        # Calculate system prompt size
        system_prompt_size = len(self.tokenizer.encode(system_prompt))
        
        # Get truncated context
        preserved_context = self.truncate_context(token_limit, system_prompt_size)
        
        # Build the full message
        full_message = system_prompt + "\n\n"
        
        # Add preserved context
        for msg in preserved_context:
            if msg["type"] == "user":
                sender = self._get_user_name(msg["sender_id"])
                full_message += f"{sender}: {msg['content']}\n"
            else:
                full_message += f"Jupiter: {msg['content']}\n"
        
        # Add current input
        user_name = self._get_user_name(self.user_data_manager.current_user.get('user_id', 'User'))
        full_message += f"{user_name}: {user_input}\nJupiter (respond as Jupiter ONLY):"
        
        return full_message
    
    # ===== Persistence Functions =====
    
    def _save_conversation(self, conversation: Dict[str, Any]) -> None:
        """Save a conversation to disk."""
        file_path = os.path.join(self.storage_path, f"{conversation['conversation_id']}.json")
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(conversation, f, ensure_ascii=False, indent=2)
        
        # Update cache
        self.conversation_cache[conversation['conversation_id']] = conversation
    
    def _add_message_to_conversation(self, conversation_id: str, message: Dict[str, Any]) -> None:
        """Add a message to a conversation and save."""
        conversation = self.get_conversation(conversation_id)
        
        if conversation:
            conversation["messages"].append(message)
            self._save_conversation(conversation)
    
    def _add_conversation_to_user(self, user_id: str, conversation_id: str) -> None:
        """Link a conversation to a user's history."""
        user = self.user_data_manager.get_user_by_id(user_id)
        
        if user:
            # Initialize conversations list if it doesn't exist
            if "conversations" not in user:
                user["conversations"] = []
            
            # Add if not already present
            if conversation_id not in user["conversations"]:
                user["conversations"].append(conversation_id)
                self.user_data_manager.update_user(user_id, user)
    
    def get_conversation(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a conversation by ID.
        
        Args:
            conversation_id: UUID of the conversation
            
        Returns:
            Conversation object or None if not found
        """
        # Check cache first
        if conversation_id in self.conversation_cache:
            return self.conversation_cache[conversation_id]
        
        # Load from disk
        file_path = os.path.join(self.storage_path, f"{conversation_id}.json")
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    conversation = json.load(f)
                    
                # Update cache
                self.conversation_cache[conversation_id] = conversation
                return conversation
            except (json.JSONDecodeError, IOError) as e:
                print(f"Error loading conversation {conversation_id}: {e}")
        
        return None
    
    def get_user_conversations(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get a user's conversation history.
        
        Args:
            user_id: ID of the user
            limit: Maximum number of conversations to return
            
        Returns:
            List of conversation objects
        """
        user = self.user_data_manager.get_user_by_id(user_id)
        
        if not user or "conversations" not in user:
            return []
        
        conversations = []
        
        # Get most recent conversations first
        for conv_id in user["conversations"][-limit:]:
            conv = self.get_conversation(conv_id)
            if conv:
                # Create a summary version with limited messages
                summary = {
                    "conversation_id": conv["conversation_id"],
                    "title": conv["title"],
                    "created_at": conv["created_at"],
                    "participants": conv["participants"],
                    "preview": conv["messages"][0]["content"] if conv["messages"] else "",
                    "message_count": len(conv["messages"])
                }
                conversations.append(summary)
        
        return sorted(conversations, key=lambda x: x["created_at"], reverse=True)
    
    def search_conversations(self, user_id: str, query: str) -> List[Dict[str, Any]]:
        """
        Search a user's conversations for specific content.
        
        Args:
            user_id: ID of the user
            query: Search query string
            
        Returns:
            List of matching conversations with context
        """
        user = self.user_data_manager.get_user_by_id(user_id)
        
        if not user or "conversations" not in user:
            return []
        
        results = []
        query = query.lower()
        
        for conv_id in user["conversations"]:
            conv = self.get_conversation(conv_id)
            
            if not conv:
                continue
                
            matches = []
            
            # Search through messages
            for message in conv["messages"]:
                if query in message["content"].lower():
                    matches.append(message)
            
            if matches:
                # Create a result with conversation info and matching messages
                result = {
                    "conversation_id": conv["conversation_id"],
                    "title": conv["title"],
                    "created_at": conv["created_at"],
                    "matches": matches,
                    "match_count": len(matches)
                }
                results.append(result)
        
        return sorted(results, key=lambda x: x["match_count"], reverse=True)
    
    # ===== Helper Functions =====
    
    def _get_user_name(self, user_id: str) -> str:
        """Get a user's name from their ID."""
        if user_id == "jupiter":
            return "Jupiter"
            
        user = self.user_data_manager.get_user_by_id(user_id)
        return user.get("name", "User") if user else "User"
    
    def add_participant(self, conversation_id: str, user_id: str) -> bool:
        """
        Add a user to an existing conversation.
        
        Args:
            conversation_id: ID of the conversation
            user_id: ID of the user to add
            
        Returns:
            True if successful, False otherwise
        """
        conversation = self.get_conversation(conversation_id)
        
        if not conversation:
            return False
            
        if user_id not in conversation["participants"]:
            conversation["participants"].append(user_id)
            self._save_conversation(conversation)
            self._add_conversation_to_user(user_id, conversation_id)
            return True
            
        return False
    
    def get_shared_conversations(self, user_ids: List[str]) -> List[Dict[str, Any]]:
        """
        Find conversations shared between multiple users.
        
        Args:
            user_ids: List of user IDs to check
            
        Returns:
            List of shared conversation summaries
        """
        if not user_ids:
            return []
            
        # Get first user's conversations
        user = self.user_data_manager.get_user_by_id(user_ids[0])
        
        if not user or "conversations" not in user:
            return []
            
        # Start with all of first user's conversations
        potential_shared = set(user["conversations"])
        
        # Intersect with each additional user's conversations
        for user_id in user_ids[1:]:
            user = self.user_data_manager.get_user_by_id(user_id)
            
            if not user or "conversations" not in user:
                return []
                
            potential_shared.intersection_update(user["conversations"])
        
        # Retrieve the shared conversations
        results = []
        for conv_id in potential_shared:
            conv = self.get_conversation(conv_id)
            if conv:
                # Create a summary with limited info
                summary = {
                    "conversation_id": conv["conversation_id"],
                    "title": conv["title"],
                    "created_at": conv["created_at"],
                    "participants": conv["participants"],
                    "message_count": len(conv["messages"])
                }
                results.append(summary)
                
        return sorted(results, key=lambda x: x["created_at"], reverse=True)