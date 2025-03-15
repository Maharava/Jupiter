import re

def extract_personal_info(message, current_data=None):
    """Extract personal info with improved accuracy"""
    if current_data is None:
        current_data = {}
    
    personal_info_shared = False
    updates = {}
    
    # Name extraction - improved with word boundaries and stricter context
    name_patterns = [
        r"my name is\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)",
        r"(?<!\w)I am\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)(?!\s+in\b|\s+from\b|\s+at\b)",
        r"(?<!\w)I'm\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)(?!\s+in\b|\s+from\b|\s+at\b)",
        r"call me\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)"
    ]
    
    for pattern in name_patterns:
        name_match = re.search(pattern, message, re.IGNORECASE)
        if name_match:
            potential_name = name_match.group(1).strip()
            # Validate name - must start with capital letter and be reasonable length
            if (len(potential_name) >= 2 and 
                len(potential_name) <= 30 and 
                potential_name[0].isalpha()):
                updates['name'] = potential_name.title()  # Proper capitalization
                personal_info_shared = True
                break
    
    # Location extraction - improved with word boundaries
    location_patterns = [
        r"I live in\s+([A-Za-z]+(?:[,\s]+[A-Za-z]+)*)",
        r"I'm from\s+([A-Za-z]+(?:[,\s]+[A-Za-z]+)*)",
        r"I am from\s+([A-Za-z]+(?:[,\s]+[A-Za-z]+)*)",
        r"my location is\s+([A-Za-z]+(?:[,\s]+[A-Za-z]+)*)"
    ]
    
    for pattern in location_patterns:
        location_match = re.search(pattern, message, re.IGNORECASE)
        if location_match:
            location = location_match.group(1).strip()
            # Validate location
            if len(location) >= 2 and len(location) <= 50:
                updates['location'] = location
                personal_info_shared = True
                break
    
    # Nationality extraction
    nationality_patterns = [
        r"I am from\s+([A-Za-z]+(?:\s+[A-Za-z]+)*)",
        r"I'm from\s+([A-Za-z]+(?:\s+[A-Za-z]+)*)",
        r"a (?:native of|citizen of)\s+([A-Za-z]+(?:\s+[A-Za-z]+)*)"
    ]
    
    for pattern in nationality_patterns:
        nationality_match = re.search(pattern, message, re.IGNORECASE)
        if nationality_match:
            nationality = nationality_match.group(1).strip()
            if len(nationality) >= 2 and len(nationality) <= 30:
                updates['nationality'] = nationality
                personal_info_shared = True
                break
    
    # Professional field extraction
    profession_patterns = [
        r"I work in\s+([A-Za-z]+(?:\s+[A-Za-z]+)*)",
        r"I am in\s+([A-Za-z]+(?:\s+[A-Za-z]+)*?)\s+(?:field|industry)",
        r"I'm in\s+([A-Za-z]+(?:\s+[A-Za-z]+)*?)\s+(?:field|industry)",
        r"my (?:field|profession) is\s+([A-Za-z]+(?:\s+[A-Za-z]+)*)"
    ]
    
    for pattern in profession_patterns:
        profession_match = re.search(pattern, message, re.IGNORECASE)
        if profession_match:
            profession = profession_match.group(1).strip()
            if len(profession) >= 2 and len(profession) <= 50:
                updates['professional_field'] = profession
                personal_info_shared = True
                break
    
    # Active projects extraction - need more precision to avoid false positives
    project_patterns = [
        r"working on\s+(?:a|an|the)?\s*([A-Za-z]+(?:\s+[A-Za-z]+){0,5}?)(?:\.|,|\s+and)",
        r"developing\s+(?:a|an|the)?\s*([A-Za-z]+(?:\s+[A-Za-z]+){0,5}?)(?:\.|,|\s+and)",
        r"building\s+(?:a|an|the)?\s*([A-Za-z]+(?:\s+[A-Za-z]+){0,5}?)(?:\.|,|\s+and)",
        r"creating\s+(?:a|an|the)?\s*([A-Za-z]+(?:\s+[A-Za-z]+){0,5}?)(?:\.|,|\s+and)"
    ]
    
    for pattern in project_patterns:
        project_match = re.search(pattern, message, re.IGNORECASE)
        if project_match:
            project = project_match.group(1).strip()
            if len(project) >= 2:
                project_entry = {
                    "name": project,
                    "mentioned_date": datetime.datetime.now().strftime("%Y-%m-%d")
                }
                
                if 'active_projects' not in updates:
                    # Check current_data first
                    if 'active_projects' in current_data:
                        # Copy existing projects
                        updates['active_projects'] = current_data['active_projects'].copy()
                    else:
                        updates['active_projects'] = []
                    
                # Check if project already exists
                existing_projects = [p["name"].lower() for p in updates['active_projects']]
                if project.lower() not in existing_projects:
                    updates['active_projects'].append(project_entry)
                    personal_info_shared = True
    
    # Return both the information updates and whether personal info was shared
    return updates, personal_info_shared
