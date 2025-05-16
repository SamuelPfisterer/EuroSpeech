#!/usr/bin/env python3
"""
Local testing script for the download pipeline.
This script helps test the download functionality without Supabase integration.
"""

import os
import sys
import random
import argparse
import pandas as pd
from pathlib import Path
import logging
from typing import List, Optional

# Import main script
from main import main
from supabase_config import SUPABASE_ENABLED

def setup_logging():
    """Configure basic logging for the testing script."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler()]
    )

def check_directory_structure() -> tuple[bool, str]:
    """
    Check if the required directory structure exists.
    
    Returns:
        tuple[bool, str]: (is_valid, message)
    """
    current_dir = Path(os.path.dirname(os.path.abspath(__file__)))
    parent_dir = current_dir.parent
    
    # Required files
    required_files = [
        current_dir / 'main.py',
        current_dir / 'download_utils.py',
        current_dir / 'supabase_config.py'
    ]
    
    # Required directories
    required_dirs = [
        parent_dir / 'links',
        parent_dir / 'downloaded_audio',
        parent_dir / 'downloaded_transcript',
        parent_dir / 'downloaded_subtitle',
        parent_dir / 'logs'
    ]
    
    # Check files
    missing_files = [f for f in required_files if not f.exists()]
    if missing_files:
        return False, f"Missing required files: {', '.join(str(f) for f in missing_files)}"
    
    # Check directories
    missing_dirs = [d for d in required_dirs if not d.exists()]
    if missing_dirs:
        return False, f"Missing required directories: {', '.join(str(d) for d in missing_dirs)}"
    
    return True, "Directory structure is valid"

def find_csv_files() -> List[Path]:
    """Find all CSV files in the links directory."""
    parent_dir = Path(os.path.dirname(os.path.abspath(__file__))).parent
    links_dir = parent_dir / 'links'
    
    if not links_dir.exists():
        return []
    
    return list(links_dir.rglob('*.csv'))

def validate_csv(csv_path: Path) -> tuple[bool, str, Optional[pd.DataFrame]]:
    """
    Validate that the CSV file contains required columns.
    
    Returns:
        tuple[bool, str, Optional[pd.DataFrame]]: (is_valid, message, dataframe)
    """
    try:
        df = pd.read_csv(csv_path)
        
        # Check if any download link columns exist
        link_columns = [col for col in df.columns if any(
            keyword in col.lower() for keyword in 
            ['link', 'url', 'video', 'transcript', 'subtitle']
        )]
        
        if not link_columns:
            return False, "No link columns found in CSV", None
            
        return True, f"Found link columns: {', '.join(link_columns)}", df
        
    except Exception as e:
        return False, f"Error reading CSV: {str(e)}", None

def create_directory_structure():
    """Create the required directory structure if it doesn't exist."""
    current_dir = Path(os.path.dirname(os.path.abspath(__file__)))
    parent_dir = current_dir.parent
    
    # Create required directories
    dirs_to_create = [
        parent_dir / 'links',
        parent_dir / 'downloaded_audio',
        parent_dir / 'downloaded_transcript',
        parent_dir / 'downloaded_subtitle',
        parent_dir / 'logs'
    ]
    
    for directory in dirs_to_create:
        directory.mkdir(parents=True, exist_ok=True)
        logging.info(f"Created directory: {directory}")

def main_test():
    """Main testing function."""
    setup_logging()
    
    # Check if Supabase is disabled
    if SUPABASE_ENABLED:
        logging.error("Please disable Supabase by setting SUPABASE_ENABLED = False in supabase_config.py")
        return
    
    # Check directory structure
    is_valid, message = check_directory_structure()
    if not is_valid:
        logging.error(f"Invalid directory structure: {message}")
        create = input("Would you like to create the required directories? (y/n): ")
        if create.lower() == 'y':
            create_directory_structure()
        else:
            return
    
    # Find CSV files
    csv_files = find_csv_files()
    if not csv_files:
        logging.error("No CSV files found in the links directory")
        logging.info("Please place your CSV file in the 'links' directory")
        return
    
    # Let user select CSV file
    print("\nAvailable CSV files:")
    for i, csv_file in enumerate(csv_files, 1):
        print(f"{i}. {csv_file.relative_to(csv_file.parent.parent)}")
    
    while True:
        try:
            choice = int(input("\nSelect CSV file number: ")) - 1
            if 0 <= choice < len(csv_files):
                selected_csv = csv_files[choice]
                break
            print("Invalid choice. Please try again.")
        except ValueError:
            print("Please enter a number.")
    
    # Validate CSV
    is_valid, message, df = validate_csv(selected_csv)
    if not is_valid:
        logging.error(f"Invalid CSV file: {message}")
        return
    
    logging.info(message)
    total_rows = len(df)
    
    # Ask user for test type
    print("\nTest types:")
    print("1. Test first N rows")
    print("2. Test random N rows")
    
    while True:
        try:
            test_type = int(input("\nSelect test type (1 or 2): "))
            if test_type in [1, 2]:
                break
            print("Invalid choice. Please try again.")
        except ValueError:
            print("Please enter a number.")
    
    # Get number of rows to test
    while True:
        try:
            n_rows = int(input(f"\nHow many rows to test? (max {total_rows}): "))
            if 0 < n_rows <= total_rows:
                break
            print(f"Please enter a number between 1 and {total_rows}")
        except ValueError:
            print("Please enter a number.")
    
    # Prepare row indices to test
    if test_type == 1:
        # Test first N rows
        indices = [(0, n_rows)]
        logging.info(f"Testing first {n_rows} rows")
    else:
        # Test random N rows
        random_indices = sorted(random.sample(range(total_rows), n_rows))
        # Group consecutive indices to minimize main.py calls
        indices = []
        start = random_indices[0]
        prev = start
        for idx in random_indices[1:] + [random_indices[-1] + 2]:
            if idx > prev + 1:
                indices.append((start, prev + 1))
                start = idx
            prev = idx
        logging.info(f"Testing {n_rows} random rows")
    
    # Run tests
    for start_idx, end_idx in indices:
        logging.info(f"\nTesting rows {start_idx} to {end_idx-1}")
        try:
            main(
                start_idx=start_idx,
                end_idx=end_idx,
                csv_file=str(selected_csv.relative_to(selected_csv.parent.parent)),
                batch_storage=False
            )
        except Exception as e:
            logging.error(f"Error testing rows {start_idx} to {end_idx-1}: {str(e)}")

if __name__ == "__main__":
    main_test() 