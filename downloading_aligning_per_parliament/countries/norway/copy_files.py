import os
import shutil
import sys

def copy_files_from_sources(source_dirs, prefix):
    # Get current directory
    target_dir = os.getcwd()
    
    # Process each source directory
    for source_dir in source_dirs:
        # Check if source directory exists
        if not os.path.exists(source_dir):
            print(f"Warning: Source directory '{source_dir}' does not exist")
            continue
        
        # Get all files in source directory that start with the prefix
        matching_files = [f for f in os.listdir(source_dir) 
                         if f.startswith(prefix) and os.path.isfile(os.path.join(source_dir, f))]
        
        if not matching_files:
            print(f"No files found in '{source_dir}' starting with '{prefix}'")
            continue
        
        # Copy each matching file
        for filename in matching_files:
            source_path = os.path.join(source_dir, filename)
            target_path = os.path.join(target_dir, filename)
            shutil.copy(source_path, target_path)
            print(f"Copied: {filename} from {source_dir}")

# Main execution
if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python copy_files_from_multiple_sources.py <prefix> <source_dir1> [source_dir2 ...]")
        sys.exit(1)
    
    prefix = sys.argv[1]
    source_dirs = sys.argv[2:]
    
    copy_files_from_sources(source_dirs, prefix)
