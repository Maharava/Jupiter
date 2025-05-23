import os
import json
import re
import datetime
from collections import Counter

class InfoExtractor:
    """Analyzes chat logs to extract important user information"""
    
    def __init__(self, llm_client, user_data_manager, logs_folder, prompt_folder, ui=None, test_mode=False):
        """Initialize the info extractor"""
        self.llm_client = llm_client
        self.user_data_manager = user_data_manager
        self.logs_folder = logs_folder
        self.prompt_folder = prompt_folder
        self.ui = ui
        self.test_mode = test_mode
        
        # Load extraction prompt
        self.extraction_prompt = self.load_extraction_prompt()
        
        # File to track processed logs
        self.processed_logs_file = os.path.join(logs_folder, "processed_logs.json")
        
        # Initialize processed logs tracking
        self.processed_logs = self.load_processed_logs()
        
        if self.test_mode:
            print(f"🧪 InfoExtractor initialized in TEST MODE - No log processing will occur")
    
    def load_extraction_prompt(self):
        """Load extraction prompt from file or create default"""
        prompt_path = os.path.join(self.prompt_folder, "extraction_prompt.txt")
        if os.path.exists(prompt_path):
            with open(prompt_path, 'r', encoding='utf-8') as f:
                return f.read()
        else:
            # Create default extraction prompt
            default_prompt = """
You are an information extraction agent for Jupiter, an AI assistant. Your task is to analyze conversation logs and identify important information about the user that Jupiter should remember.

IMPORTANT: You are NOT told what information to look for. Use your judgment to determine what's important.

When you identify important information, respond in this exact JSON format:
{
  "extracted_info": [
    {"category": "name", "value": "John Smith"},
    {"category": "likes", "value": "vintage cars"}
  ]
}

If you don't find any important information, respond with:
{
  "extracted_info": []
}

DO NOT include any explanations outside the JSON. ONLY return valid JSON.
"""
            # Create prompt folder if it doesn't exist
            os.makedirs(self.prompt_folder, exist_ok=True)
            
            # Save default prompt
            with open(prompt_path, 'w', encoding='utf-8') as f:
                f.write(default_prompt)
                
            return default_prompt
    
    def load_processed_logs(self):
        """Load list of already processed log files"""
        if os.path.exists(self.processed_logs_file):
            with open(self.processed_logs_file, 'r', encoding='utf-8') as f:
                try:
                    return json.load(f)
                except json.JSONDecodeError:
                    return {"processed": []}
        else:
            # Create new processed logs file if it doesn't exist
            processed_logs = {"processed": []}
            with open(self.processed_logs_file, 'w', encoding='utf-8') as f:
                json.dump(processed_logs, f, indent=4)
            return processed_logs
    
    def save_processed_logs(self):
        """Save list of processed log files"""
        with open(self.processed_logs_file, 'w', encoding='utf-8') as f:
            json.dump(self.processed_logs, f, indent=4)
    
    def mark_log_as_processed(self, log_file):
        """Add log file to list of processed logs"""
        if log_file not in self.processed_logs["processed"]:
            self.processed_logs["processed"].append(log_file)
            self.save_processed_logs()
    
    def get_unprocessed_logs(self):
        """Get list of log files that haven't been processed yet"""
        # Get all log files (only .log format)
        all_logs = []
        for file in os.listdir(self.logs_folder):
            if file.startswith("jupiter_chat_") and file.endswith(".log"):
                all_logs.append(os.path.join(self.logs_folder, file))
        
        # Filter out already processed logs
        unprocessed_logs = [log for log in all_logs if log not in self.processed_logs["processed"]]
        
        return unprocessed_logs
    
    def read_log_file(self, log_file):
        """Read and parse a log file into a list of messages"""
        messages = []
        user_prefix = None
        
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
                for line in lines:
                    # Skip empty lines and the header
                    if not line.strip() or "===" in line:
                        continue
                    
                    # Parse log line format: [timestamp] Role: Message
                    match = re.search(r'\[(.*?)\] (.*?):(.*)', line)
                    if match:
                        timestamp, role, message = match.groups()
                        role = role.strip()
                        message = message.strip()
                        
                        # Make sure role includes colon
                        if not role.endswith(':'):
                            role_with_colon = f"{role}:"
                        else:
                            role_with_colon = role
                        
                        # Identify user_prefix (any non-system role)
                        system_roles = ["Jupiter:", "InfoExtractor:", "InfoExtractor Error:"]
                        if role_with_colon not in system_roles:
                            if not user_prefix:  # Only set if not already set
                                user_prefix = role_with_colon
                        
                        # Only include actual conversation messages
                        if role_with_colon == "Jupiter:" or role_with_colon == user_prefix:
                            messages.append({"role": role_with_colon, "message": message})
        except Exception as e:
            print(f"InfoExtractor Error: Failed to read log file {log_file}: {str(e)}")
        
        return messages, user_prefix
    
    def parse_llm_response(self, response):
        """Parse the JSON response from the LLM"""
        if not response:
            return []
        
        try:
            # Find JSON in response (it might have extra text)
            json_match = re.search(r'({[\s\S]*})', response)
            if json_match:
                response = json_match.group(1)
            
            # Parse JSON
            data = json.loads(response)
            
            # Return extracted information
            if 'extracted_info' in data:
                return data['extracted_info']
            return []
        except Exception as e:
            print(f"InfoExtractor Error: Failed to parse LLM response: {str(e)}")
            return []
    
    def identify_username_from_log(self, log_file):
        """Try to extract the username from a log file"""
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
                # Look for user prefix pattern
                user_matches = re.findall(r'\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\] ([^:]+):', content)
                
                if user_matches:
                    # Filter out Jupiter and system messages
                    user_prefixes = [m for m in user_matches if m != "Jupiter" and 
                                     not m.startswith("InfoExtractor")]
                    
                    if user_prefixes:
                        # Get the most common user prefix
                        prefix_counter = Counter(user_prefixes)
                        most_common = prefix_counter.most_common(1)[0][0]
                        
                        # If it ends with a colon, remove it
                        if most_common.endswith(':'):
                            most_common = most_common[:-1]
                        
                        return most_common
            
            # If no user name found, return default
            return "User"
        except Exception as e:
            print(f"InfoExtractor Error: Failed to identify username from log: {str(e)}")
            return "User"
    
    def process_log_file(self, log_file):
        """Process a single log file and extract information"""
        if self.test_mode:
            print(f"TEST MODE: Skipping log processing for {os.path.basename(log_file)}")
            self.mark_log_as_processed(log_file)
            return
            
        print(f"InfoExtractor: Processing log file {os.path.basename(log_file)}")
        
        # Read messages from log
        messages, user_prefix = self.read_log_file(log_file)
        if not messages:
            print(f"InfoExtractor: No messages found in log file {os.path.basename(log_file)}")
            self.mark_log_as_processed(log_file)
            return
        
        # Filter to only include user messages
        user_messages = []
        for msg in messages:
            if msg["role"] != "Jupiter:":
                user_messages.append(f"{msg['role']} {msg['message']}")
        
        if not user_messages:
            print(f"InfoExtractor: No user messages found in log file {os.path.basename(log_file)}")
            self.mark_log_as_processed(log_file)
            return
        
        # Identify username from the log
        username = user_prefix.rstrip(':') if user_prefix else self.identify_username_from_log(log_file)
        
        # Send user messages to LLM for analysis
        formatted_content = "\n".join(user_messages)
        llm_response = self.llm_client.extract_information(self.extraction_prompt, formatted_content)
        
        # Parse LLM response
        extracted_info = self.parse_llm_response(llm_response)
        
        # Get user data - now with name history support
        user_data = self.user_data_manager.get_user(username)
        if not user_data:
            # Create new user if not found
            user_data = {'name': username}
            user_id = self.user_data_manager.create_user(user_data)
            user_data['user_id'] = user_id
        
        # Set as current user
        self.user_data_manager.set_current_user(user_data)
        
        # Update user data with extracted information
        updates = self.user_data_manager.update_user_info(extracted_info)
        
        if updates:
            print(f"InfoExtractor: Updated user data for {username}: {', '.join(updates)}")
        
        # Mark log as processed
        self.mark_log_as_processed(log_file)
    
    def process_all_unprocessed_logs(self):
        """Process all unprocessed log files"""
        if self.test_mode:
            print("TEST MODE: Skipping log processing")
            return
                
        # Get unprocessed logs
        unprocessed_logs = self.get_unprocessed_logs()
        
        if not unprocessed_logs:
            print("InfoExtractor: No new logs to process")
            # Update status if UI is available
            if self.ui and hasattr(self.ui, 'set_status'):
                self.ui.set_status("Ready", False)
            return
        
        print(f"InfoExtractor: Found {len(unprocessed_logs)} unprocessed log files")
        
        # Process each log
        for log_file in unprocessed_logs:
            self.process_log_file(log_file)
                
        print(f"InfoExtractor: Finished processing {len(unprocessed_logs)} log files")
        # Update status if UI is available
        if self.ui and hasattr(self.ui, 'set_status'):
            self.ui.set_status("Ready", False)