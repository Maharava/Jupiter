import os
import datetime

def map_directory(root_dir='.', output_file='jupiter_structure.txt'):
    """
    Maps the structure and contents of the Jupiter project directory.
    
    Args:
        root_dir (str): The root directory to start mapping from. Defaults to current directory.
        output_file (str): The name of the output file. Defaults to 'jupiter_structure.txt'.
    """
    # Get absolute path of root directory
    root_dir = os.path.abspath(root_dir)
    
    # Prepare the output file
    with open(output_file, 'w', encoding='utf-8') as f:
        # Write header
        f.write(f"Jupiter Project Structure Map\n")
        f.write(f"Generated on: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Root directory: {root_dir}\n")
        f.write("=" * 80 + "\n\n")
        
        # Walk through directory tree
        for dirpath, dirnames, filenames in os.walk(root_dir):
            # Calculate relative path from root
            rel_path = os.path.relpath(dirpath, root_dir)
            
            # Skip .git directories and other hidden folders
            if '.git' in dirpath or any(part.startswith('.') for part in dirpath.split(os.sep)):
                continue
                
            # Determine the indent level based on directory depth
            indent = "│   " * (rel_path.count(os.sep))
            
            # Print current directory (use root if we're at the top level)
            if rel_path == '.':
                f.write(f"Jupiter/\n")
            else:
                f.write(f"{indent}├── {os.path.basename(dirpath)}/\n")
            
            # Sort directories and files for consistent output
            dirnames.sort()
            filenames.sort()
            
            # Print files in current directory
            file_indent = "│   " * (rel_path.count(os.sep) + 1)
            for i, filename in enumerate(filenames):
                # Skip hidden files
                if filename.startswith('.'):
                    continue
                    
                # Use different symbol for last item
                if i == len(filenames) - 1 and len(dirnames) == 0:
                    f.write(f"{file_indent}└── {filename}\n")
                else:
                    f.write(f"{file_indent}├── {filename}\n")
            
            # Add a blank line after each directory for better readability
            if filenames and not all(f.startswith('.') for f in filenames):
                f.write("\n")
    
    print(f"Structure map has been written to {output_file}")
    
    # Return path to the generated file
    return os.path.abspath(output_file)

if __name__ == "__main__":
    output_path = map_directory()
    
    # Optionally display the contents of the generated file
    try:
        with open(output_path, 'r', encoding='utf-8') as f:
            print("\nStructure Map Preview:")
            print("-" * 40)
            for i, line in enumerate(f):
                if i < 20:  # Show first 20 lines as a preview
                    print(line.rstrip())
                else:
                    print("...")
                    break
    except Exception as e:
        print(f"Error displaying preview: {e}")
