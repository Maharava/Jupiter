import os
import json
import datetime
import requests

class InfoExtractor:
    """
    Module that analyzes previous chat logs to extract important user information.
    Processes logs during startup and ensures each log is only processed once.
    """
    
    def __init__(self, jupiter_chat, kobold_api_url="http://localhost:5001"):
        self.jupiter = jupiter_chat
        self.kobold_api_url = kobold_api_url
        
        # Load extraction prompt
        self.extraction_prompt = self.load_extraction_prompt()
        
        # File to track processed logs
        self.processed_logs_file = os.path.join(self.jupiter.logs_folder, "processed_logs.json")
        
        # Initialize processed logs tracking
        self.processed_logs = self.load_processed_logs()
    
    def load_extraction_prompt(self):
        """Load the information extraction prompt from file or create default"""
        prompt_path = os.path.join(self.jupiter.prompt_folder, "extraction_prompt.txt")
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
        # Get all log files
        all_logs = []
        for file in os.listdir(self.jupiter.logs_folder):
            if file.startswith("jupiter_chat_") and file.endswith(".log"):
                all_logs.append(os.path.join(self.jupiter.logs_folder, file))
        
        # Filter out already processed logs
        unprocessed_logs = [log for log in all_logs if log not in self.processed_logs["processed"]]
        
        return unprocessed_logs
    
    def read_log_file(self, log_file):
        """Read and parse a log file into a list of messages"""
        messages = []
        user_prefix = None
        
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
                    
                    if role != "Jupiter:" and role != "InfoExtractor:" and role != "InfoExtractor Error:":
                        user_prefix = role
                    
                    # Only include actual conversation messages
                    if role == "Jupiter:" or (user_prefix and role == user_prefix):
                        messages.append(f"{role} {message}")
        
        return messages
    
    def send_to_llm(self, messages):
        """Send messages to the LLM for analysis and return extracted information"""
        try:
            # Format the messages
            formatted_content = "\n".join(messages)
            
            # Complete prompt to send to LLM
            prompt = f"{self.extraction_prompt}\n\nHere is the conversation to analyze:\n\n{formatted_content}\n\nExtracted information:"
            
            payload = {
                "prompt": prompt,
                "max_length": 300,
                "temperature": 0.2,  # Lower temperature for more deterministic extraction
                "top_p": 0.9,
                "top_k": 40,
                "rep_pen": 1.1
            }
            
            endpoint = f"{self.kobold_api_url}/api/v1/generate"
            response = requests.post(endpoint, json=payload, timeout=60)
            
            if response.status_code == 200:
                response_json = response.json()
                if 'results' in response_json and len(response_json['results']) > 0:
                    # Return the LLM's response text
                    return response_json['results'][0]['text'].strip()
                else:
                    print(f"InfoExtractor Error: Unexpected response format from LLM API.")
                    return None
            else:
                print(f"InfoExtractor Error: Could not connect to LLM API (Status: {response.status_code}).")
                return None
                
        except Exception as e:
            print(f"InfoExtractor Error: Error communicating with LLM: {str(e)}")
            return None
    
    def parse_llm_response(self, response):
        """Parse the JSON response from the LLM"""
        if not response:
            return []
        
        try:
            # Find JSON in response (it might have extra text)
            import re
            json_match = re.search(r'({[\s\S]*})', response)
            if json_match:
                response = json_match.group(1)
            
            # Parse JSON
            data = json.loads(response)
            
            # Return extracted information
            if 'extracted_info' in data:
                return data['extracted_info']
            return []
        except json.JSONDecodeError:
            print(f"InfoExtractor Error: Failed to parse JSON response: {response}")
            return []
        except Exception as e:
            print(f"InfoExtractor Error: Error processing LLM response: {str(e)}")
            return []
    
    def update_user_data(self, extracted_info, username):
        """Update user data with extracted information"""
        if not extracted_info:
            return
        
        # Load all user data
        all_user_data = self.jupiter.load_user_data()
        
        # Ensure known_users exists
        if 'known_users' not in all_user_data:
            all_user_data['known_users'] = {}
        
        # Get user data for this specific user
        if username in all_user_data['known_users']:
            user_data = all_user_data['known_users'][username]
        else:
            # If user doesn't exist yet, create new entry
            user_data = {'name': username}
        
        # Keep track of updates made
        updates = []
        
        for item in extracted_info:
            if 'category' in item and 'value' in item:
                category = item['category']
                value = item['value']
                
                # Skip empty values
                if not value or value.strip() == "":
                    continue
                
                # Special case for name
                if category == 'name':
                    # Only update name if the current one is generic
                    if user_data.get('name') == 'User':
                        user_data['name'] = value
                        updates.append(f"name: {value}")
                    continue
                
                # For lists (likes, dislikes, etc.)
                if category in ['likes', 'dislikes', 'interests', 'hobbies']:
                    if category not in user_data:
                        user_data[category] = []
                    
                    # Only add if not already present
                    if value not in user_data[category]:
                        user_data[category].append(value)
                        updates.append(f"{category}: {value}")
                else:
                    # For simple key-value pairs
                    # Only update if different from current value
                    if category not in user_data or user_data[category] != value:
                        user_data[category] = value
                        updates.append(f"{category}: {value}")
        
        # Save updates if any were made
        if updates:
            # Update user data in the main structure
            all_user_data['known_users'][username] = user_data
            
            # Save to file
            with open(self.jupiter.user_data_file, 'w', encoding='utf-8') as f:
                json.dump(all_user_data, f, indent=4)
            
            print(f"InfoExtractor: Updated user data for {username}: {', '.join(updates)}")
            
        return updates
    
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
                        from collections import Counter
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
        print(f"InfoExtractor: Processing log file {os.path.basename(log_file)}")
        
        # Read messages from log
        messages = self.read_log_file(log_file)
        if not messages:
            print(f"InfoExtractor: No messages found in log file {os.path.basename(log_file)}")
            self.mark_log_as_processed(log_file)
            return
        
        # Identify username from the log
        username = self.identify_username_from_log(log_file)
        
        # Send to LLM for analysis
        llm_response = self.send_to_llm(messages)
        
        # Parse LLM response
        extracted_info = self.parse_llm_response(llm_response)
        
        # Update user data with extracted information
        self.update_user_data(extracted_info, username)
        
        # Mark log as processed
        self.mark_log_as_processed(log_file)
    
    def process_all_unprocessed_logs(self):
        """Process all unprocessed log files"""
        # Get unprocessed logs
        unprocessed_logs = self.get_unprocessed_logs()
        
        if not unprocessed_logs:
            print("InfoExtractor: No new logs to process")
            return
        
        print(f"InfoExtractor: Found {len(unprocessed_logs)} unprocessed log files")
        
        # Process each log
        for log_file in unprocessed_logs:
            self.process_log_file(log_file)
            
        print(f"InfoExtractor: Finished processing {len(unprocessed_logs)} log files")
