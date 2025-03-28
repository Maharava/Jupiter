import json
import os
import uuid
import time
import logging

# Set up logging
logger = logging.getLogger("jupiter.user_data")

class UserDataManager:
    """Unified manager for user data storage and operations with cross-platform ID support"""
    
    def __init__(self, user_data_file):
        """Initialize with path to user data file"""
        self.user_data_file = user_data_file
        self.current_user = {}
        
        # Create empty user data file if it doesn't exist
        if not os.path.exists(user_data_file):
            # Create directory if needed
            dir_name = os.path.dirname(user_data_file)
            if dir_name:
                os.makedirs(dir_name, exist_ok=True)
            # Initialize with new data structure
            self._initialize_data_file()
    
    def _initialize_data_file(self):
        """Initialize the user data file with the new structure"""
        initial_data = {
            "users": {},
            "name_map": {},
            "platform_map": {
                "gui": {},
                "discord": {}
            },
            "metadata": {
                "version": 2,
                "last_cleanup": time.time()
            }
        }
        self.save_user_data(initial_data)
    
    def _migrate_legacy_data(self, legacy_data):
        """Migrate legacy data to new format if needed"""
        if "known_users" in legacy_data:
            # This is legacy data - migrate it
            new_data = {
                "users": {},
                "name_map": {},
                "platform_map": {
                    "gui": {},
                    "discord": {}
                },
                "metadata": {
                    "version": 2,
                    "last_cleanup": time.time()
                }
            }
            
            # Migrate each user
            for name, user_info in legacy_data["known_users"].items():
                # Generate ID for legacy user
                user_id = str(uuid.uuid4())
                
                # Add platform info
                user_info["platforms"] = {"gui": True}
                
                # Store user with ID as key
                new_data["users"][user_id] = user_info
                
                # Add to name map
                new_data["name_map"][name.lower()] = user_id
                
                # Add to platform map
                new_data["platform_map"]["gui"][name.lower()] = user_id
            
            return new_data
        return legacy_data
    
    def load_user_data(self):
        """Load all user data from file with migration if needed"""
        if os.path.exists(self.user_data_file):
            with open(self.user_data_file, 'r', encoding='utf-8') as f:
                try:
                    data = json.load(f)
                    
                    # Check if migration is needed
                    if "known_users" in data:
                        logger.info("Migrating legacy user data to new ID-based format")
                        data = self._migrate_legacy_data(data)
                        # Save migrated data
                        self.save_user_data(data)
                    
                    return data
                except json.JSONDecodeError:
                    logger.error("Error decoding user data JSON, initializing new structure")
                    return self._initialize_data_file()
        else:
            return self._initialize_data_file()
    
    def save_user_data(self, data):
        """Save all user data to file"""
        with open(self.user_data_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
    
    def get_user_by_id(self, user_id):
        """Get user data by ID"""
        data = self.load_user_data()
        return data["users"].get(user_id)
    
    def get_user_by_name(self, username, platform="gui"):
        """Get a user by name (case-insensitive)"""
        data = self.load_user_data()
        username_lower = username.lower()
        
        # Check platform-specific map first
        if platform in data["platform_map"] and username_lower in data["platform_map"][platform]:
            user_id = data["platform_map"][platform][username_lower]
            return data["users"].get(user_id), user_id
        
        # Fall back to global name map
        if username_lower in data["name_map"]:
            user_id = data["name_map"][username_lower]
            return data["users"].get(user_id), user_id
            
        return None, None
    
    def get_user(self, username, platform="gui"):
        """Get user data - backward compatibility method"""
        user, _ = self.get_user_by_name(username, platform)
        return user
    
    def identify_user(self, username, platform="gui"):
        """Identify a user by username, create if doesn't exist"""
        data = self.load_user_data()
        username_lower = username.lower()
        
        # Check if user exists in platform map
        if platform in data["platform_map"] and username_lower in data["platform_map"][platform]:
            user_id = data["platform_map"][platform][username_lower]
            user_data = data["users"].get(user_id)
            
            # Update last_seen timestamp
            if user_data:
                user_data["last_seen"] = time.time()
                user_data["platforms"][platform] = True
                data["users"][user_id] = user_data
                self.save_user_data(data)
                return user_data, user_data.get("name", username)
        
        # Check global name map as fallback
        if username_lower in data["name_map"]:
            user_id = data["name_map"][username_lower]
            user_data = data["users"].get(user_id)
            
            # Update platform info and last_seen
            if user_data:
                user_data["last_seen"] = time.time()
                if "platforms" not in user_data:
                    user_data["platforms"] = {}
                user_data["platforms"][platform] = True
                
                # Update platform map
                if platform in data["platform_map"]:
                    data["platform_map"][platform][username_lower] = user_id
                
                data["users"][user_id] = user_data
                self.save_user_data(data)
                return user_data, user_data.get("name", username)
        
        # Create new user with UUID
        user_id = str(uuid.uuid4())
        user_data = {
            "name": username,
            "user_id": user_id,
            "created_at": time.time(),
            "last_seen": time.time(),
            "platforms": {
                platform: True
            }
        }
        
        # Update data structures
        data["users"][user_id] = user_data
        data["name_map"][username_lower] = user_id
        
        if platform in data["platform_map"]:
            data["platform_map"][platform][username_lower] = user_id
        
        self.save_user_data(data)
        return user_data, username
    
    def set_current_user(self, user_data):
        """Set the current user data"""
        self.current_user = user_data
    
    def save_current_user(self):
        """Save the current user data to file"""
        if not self.current_user or 'user_id' not in self.current_user:
            logger.warning("Attempted to save user without ID")
            return
            
        data = self.load_user_data()
        user_id = self.current_user['user_id']
        
        # Update user data
        data["users"][user_id] = self.current_user
        
        # Update name mapping if name changed
        if 'name' in self.current_user:
            name_lower = self.current_user['name'].lower()
            
            # Check if we need to update name_map
            for old_name, mapped_id in list(data["name_map"].items()):
                if mapped_id == user_id and old_name != name_lower:
                    # Remove old name mapping
                    del data["name_map"][old_name]
            
            # Add current name mapping
            data["name_map"][name_lower] = user_id
            
            # Update platform maps
            if "platforms" in self.current_user:
                for platform in self.current_user["platforms"]:
                    if platform in data["platform_map"]:
                        # Remove old mappings
                        for old_name, mapped_id in list(data["platform_map"][platform].items()):
                            if mapped_id == user_id and old_name != name_lower:
                                del data["platform_map"][platform][old_name]
                        
                        # Add current mapping
                        data["platform_map"][platform][name_lower] = user_id
        
        self.save_user_data(data)
    
    def update_user_info(self, extracted_info):
        """Update current user with extracted information"""
        if not self.current_user or 'user_id' not in self.current_user:
            return []
        
        # Keep track of updates made
        updates = []
        
        for item in extracted_info:
            if 'category' in item and 'value' in item:
                category = item['category']
                value = item['value']
                
                # Skip empty values
                if not value or value.strip() == "":
                    continue
                
                # For lists (likes, dislikes, etc.)
                if category in ['likes', 'dislikes', 'interests', 'hobbies']:
                    if category not in self.current_user:
                        self.current_user[category] = []
                    
                    # Only add if not already present
                    if value not in self.current_user[category]:
                        self.current_user[category].append(value)
                        updates.append(f"{category}: {value}")
                else:
                    # For simple key-value pairs
                    # Only update if different from current value
                    if category not in self.current_user or self.current_user[category] != value:
                        self.current_user[category] = value
                        updates.append(f"{category}: {value}")
        
        # Save updates if any were made
        if updates:
            self.save_current_user()
            
        return updates
    
    def link_platform_identities(self, source_platform, source_name, target_platform, target_name):
        """Link user identities across platforms"""
        data = self.load_user_data()
        
        # Convert to lowercase for consistency
        source_name_lower = source_name.lower()
        target_name_lower = target_name.lower()
        
        # Check if source user exists
        if source_platform not in data["platform_map"] or source_name_lower not in data["platform_map"][source_platform]:
            return False, "Source user not found"
        
        # Check if target user exists
        if target_platform not in data["platform_map"] or target_name_lower not in data["platform_map"][target_platform]:
            return False, "Target user not found"
        
        # Get user IDs
        source_id = data["platform_map"][source_platform][source_name_lower]
        target_id = data["platform_map"][target_platform][target_name_lower]
        
        # If same ID, already linked
        if source_id == target_id:
            return True, "Identities already linked"
        
        # Merge user data (source into target)
        source_data = data["users"][source_id]
        target_data = data["users"][target_id]
        
        # Combine platforms
        if "platforms" not in target_data:
            target_data["platforms"] = {}
        
        for platform, enabled in source_data.get("platforms", {}).items():
            target_data["platforms"][platform] = enabled
        
        # Combine other data (non-system fields)
        for key, value in source_data.items():
            if key not in ["user_id", "name", "platforms", "created_at"]:
                # For lists, combine
                if isinstance(value, list) and key in target_data and isinstance(target_data[key], list):
                    # Add items not already in target
                    for item in value:
                        if item not in target_data[key]:
                            target_data[key].append(item)
                # For other fields, only copy if not in target
                elif key not in target_data:
                    target_data[key] = value
        
        # Update target data
        data["users"][target_id] = target_data
        
        # Update platform mappings
        for platform, names in data["platform_map"].items():
            for name, user_id in list(names.items()):
                if user_id == source_id:
                    data["platform_map"][platform][name] = target_id
        
        # Update name mappings
        for name, user_id in list(data["name_map"].items()):
            if user_id == source_id:
                data["name_map"][name] = target_id
        
        # Remove source user
        del data["users"][source_id]
        
        # Save updated data
        self.save_user_data(data)
        
        return True, f"Successfully linked {source_platform}/{source_name} to {target_platform}/{target_name}"
    
    def get_user_id_info(self, username, platform="gui"):
        """Get user ID and platform information for display"""
        data = self.load_user_data()
        username_lower = username.lower()
        
        # Check platform-specific map
        if platform in data["platform_map"] and username_lower in data["platform_map"][platform]:
            user_id = data["platform_map"][platform][username_lower]
            user_data = data["users"].get(user_id)
            
            if user_data:
                platforms = user_data.get("platforms", {})
                platform_list = [p for p, enabled in platforms.items() if enabled]
                
                return {
                    "user_id": user_id,
                    "name": user_data.get("name", username),
                    "platforms": platform_list,
                    "created_at": user_data.get("created_at", 0),
                    "last_seen": user_data.get("last_seen", 0)
                }
        
        return None
    
    def cleanup_old_users(self, max_age_days=180):
        """Clean up unused user profiles"""
        data = self.load_user_data()
        
        # Calculate cutoff time
        now = time.time()
        cutoff = now - (max_age_days * 24 * 60 * 60)
        
        # Track removed users
        removed_count = 0
        
        # Find old users
        for user_id, user_data in list(data["users"].items()):
            last_seen = user_data.get("last_seen", 0)
            
            if last_seen < cutoff:
                # Remove from users
                del data["users"][user_id]
                
                # Remove from name map
                for name, mapped_id in list(data["name_map"].items()):
                    if mapped_id == user_id:
                        del data["name_map"][name]
                
                # Remove from platform maps
                for platform, platform_map in data["platform_map"].items():
                    for name, mapped_id in list(platform_map.items()):
                        if mapped_id == user_id:
                            del platform_map[name]
                
                removed_count += 1
        
        # Update metadata
        data["metadata"]["last_cleanup"] = now
        
        # Save updated data
        if removed_count > 0:
            self.save_user_data(data)
            logger.info(f"Cleaned up {removed_count} old user profiles")
        
        return removed_count