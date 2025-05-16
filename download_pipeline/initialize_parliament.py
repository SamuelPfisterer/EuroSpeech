"""
Initialize a parliament entry in the Supabase database.
This script should be run once before starting the download jobs.
"""

import os
import argparse
import pandas as pd
from supabase_config import get_supabase

def initialize_parliament(parliament_id: str, csv_file: str) -> None:
    """
    Initialize a parliament entry in the database.
    
    Args:
        parliament_id: Identifier for the parliament (e.g., 'croatia')
        csv_file: Path to the CSV file containing the sessions to download
    """
    # Get base directory (croatia folder)
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # Construct full CSV path
    csv_path = os.path.join(base_dir, csv_file)
    print(f"Reading CSV from: {csv_path}")
    
    # Read CSV to get total number of sessions
    df = pd.read_csv(csv_path)
    total_sessions = len(df)
    
    # Create parliament entry
    client = get_supabase()
    
    # Check if entry already exists
    response = client.table('parliament_progress')\
        .select('*')\
        .eq('parliament_id', parliament_id)\
        .execute()
        
    if response.data:
        print(f"Parliament {parliament_id} already exists in database.")
        return
        
    # Create new entry
    client.table('parliament_progress').insert({
        'parliament_id': parliament_id,
        'total_sessions': total_sessions,
        'completed_videos': 0,
        'completed_transcripts': 0,
        'failed_downloads': 0,
        'active_downloads': 0
    }).execute()
    
    print(f"Initialized parliament {parliament_id} with {total_sessions} total sessions")

def main():
    parser = argparse.ArgumentParser(description='Initialize parliament in Supabase database')
    parser.add_argument('--parliament_id', type=str, required=True,
                      help='Identifier for the parliament (e.g., croatia)')
    parser.add_argument('--csv_file', type=str, required=True,
                      help='Path to CSV file relative to croatia directory (e.g., links/media_links/file.csv)')
    
    args = parser.parse_args()
    
    # Get absolute path of the CSV file
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    csv_path = os.path.join(base_dir, args.csv_file)
    
    # Ensure CSV file exists
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"CSV file not found: {csv_path}")
    
    initialize_parliament(args.parliament_id, args.csv_file)

if __name__ == '__main__':
    main() 