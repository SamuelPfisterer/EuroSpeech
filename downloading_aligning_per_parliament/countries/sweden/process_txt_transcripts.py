import os
import re
from pathlib import Path
from tqdm import tqdm

def extract_content(file_text):
    """Extract only the content part from each speech in the text."""
    # Pattern to match content sections
    content_pattern = re.compile(r'Content:\n(.*?)(?=\n={80}|\Z)', re.DOTALL)
    
    # Find all content sections
    content_matches = content_pattern.findall(file_text)
    
    # Concatenate all content sections
    combined_content = '\n\n'.join(match.strip() for match in content_matches)
    
    return combined_content

def process_files():
    """Process all transcript files."""
    # Define paths
    processed_dir = Path('downloaded_transcript/processed_text_transcripts')
    cleaned_dir = Path('downloaded_transcript/cleaned_text_transcripts')
    
    # Create destination directory if it doesn't exist
    cleaned_dir.mkdir(exist_ok=True, parents=True)
    
    # Get list of files to process
    file_paths = list(processed_dir.glob('*.txt'))
    
    # Process each file in the processed directory with progress bar
    for file_path in tqdm(file_paths, desc="Processing transcripts"):
        try:
            # Read the source file
            with open(file_path, 'r', encoding='utf-8') as f:
                file_text = f.read()
            
            # Extract content
            cleaned_content = extract_content(file_text)
            
            # Create destination file with same name
            dest_file = cleaned_dir / file_path.name
            
            # Write the cleaned content to the destination file
            with open(dest_file, 'w', encoding='utf-8') as f:
                f.write(cleaned_content)
            
        except Exception as e:
            print(f"Error processing {file_path.name}: {e}")

if __name__ == "__main__":
    process_files()
    print("Processing complete.")
