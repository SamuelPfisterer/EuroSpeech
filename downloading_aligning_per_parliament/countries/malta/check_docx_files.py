import os
from docx import Document

def check_docx_file(file_path):
    try:
        doc = Document(file_path)
        # If the file opens without errors, it's considered valid
        return True
    except Exception as e:
        print(f"Error in file {file_path}: {e}")
        return False

def check_docx_files_in_directory(directory):
    valid_count = 0
    invalid_count = 0

    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith(".docx") or file.endswith(".doc"):
                file_path = os.path.join(root, file)
                if check_docx_file(file_path):
                    valid_count += 1
                else:
                    invalid_count += 1

    print(f"Valid files: {valid_count}")
    print(f"Invalid files: {invalid_count}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Usage: python check_docx_files.py <directory>")
        sys.exit(1)
    
    directory = sys.argv[1]
    check_docx_files_in_directory(directory)