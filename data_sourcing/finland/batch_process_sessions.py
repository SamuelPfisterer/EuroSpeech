import csv
import os
from process_session import process_session
from typing import List, Dict, Optional
import time
from datetime import datetime

def read_session_links(csv_path: str) -> List[Dict[str, str]]:
    """
    Read session links from CSV file.
    
    Args:
        csv_path: Path to the CSV file containing session links
        
    Returns:
        List of dictionaries containing session information
    """
    sessions = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            sessions.append(row)
    return sessions

def extract_session_id(url: str) -> Optional[str]:
    """
    Extract session ID from URL in format PTK_X_YYYY.
    
    Args:
        url: URL of the session
        
    Returns:
        Session ID in format PTK_X_YYYY or None if not found
    """
    try:
        # Example URL: https://verkkolahetys.eduskunta.fi/fi/taysistunnot/taysistunto-125-2024
        parts = url.strip('/').split('-')
        session_num = parts[-2]
        year = parts[-1]
        return f"PTK_{session_num}_{year}"
    except Exception as e:
        print(f"Error extracting session ID from URL {url}: {e}")
        return None

def batch_process_sessions(csv_path: str, output_base_dir: str = "processed_sessions", 
                        start_from: int = 0, delay: int = 2, limit: Optional[int] = None):
    """
    Process all sessions from the CSV file.
    
    Args:
        csv_path: Path to the CSV file containing session links
        output_base_dir: Base directory for output files
        start_from: Index to start processing from (useful for resuming)
        delay: Delay in seconds between processing sessions
        limit: Maximum number of sessions to process (None for all)
    """
    # Create output directory
    os.makedirs(output_base_dir, exist_ok=True)
    
    # Read session links
    sessions = read_session_links(csv_path)
    total_sessions = len(sessions)
    
    if limit:
        sessions = sessions[start_from:start_from + limit]
        print(f"\nProcessing {len(sessions)} sessions (limited from {total_sessions} total)")
    else:
        sessions = sessions[start_from:]
        print(f"\nProcessing all remaining sessions: {len(sessions)} of {total_sessions}")
    
    print(f"Starting from index {start_from}")
    print(f"Output directory: {output_base_dir}")
    
    # Create a log file
    log_file = os.path.join(output_base_dir, f"processing_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
    
    for i, session in enumerate(sessions, start=start_from):
        url = session['link']
        session_id = extract_session_id(url)
        
        if not session_id:
            continue
            
        print(f"\nProcessing session {i+1}/{total_sessions}: {session_id}")
        print(f"URL: {url}")
        
        # Create session-specific output directory
        session_dir = os.path.join(output_base_dir, session_id)
        os.makedirs(session_dir, exist_ok=True)
        
        try:
            # Process the session
            result = process_session(session_id, session_dir)
            
            # Log the result
            with open(log_file, 'a', encoding='utf-8') as f:
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                if result:
                    stats = result['metadata']['statistics']
                    log_entry = (
                        f"{timestamp} - Success - {session_id} - "
                        f"Speeches: {stats['regular_speech_count']}, "
                        f"Chairman: {stats['chairman_statement_count']}, "
                        f"Total: {stats['total_items']}\n"
                    )
                else:
                    log_entry = f"{timestamp} - Failed - {session_id}\n"
                f.write(log_entry)
            
            # Add delay between requests
            if i < len(sessions) - 1:  # Don't delay after the last session
                print(f"Waiting {delay} seconds before next session...")
                time.sleep(delay)
                
        except Exception as e:
            print(f"Error processing session {session_id}: {e}")
            with open(log_file, 'a', encoding='utf-8') as f:
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                f.write(f"{timestamp} - Error - {session_id} - {str(e)}\n")
            continue

if __name__ == "__main__":
    csv_path = "session_links.csv"
    output_dir = "processed_sessions"
    start_from = 0  # Start from the beginning
    delay = 2  # 2 seconds delay between sessions
    limit = 3  # Process only the first 3 sessions
    
    batch_process_sessions(csv_path, output_dir, start_from, delay, limit) 