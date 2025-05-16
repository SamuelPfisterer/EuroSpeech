import requests
import json
import os
from typing import Optional, Dict
from session_parser import parse_session_json

def fetch_session_json(session_id: str) -> Optional[Dict]:
    """
    Fetch the raw JSON data for a parliamentary session from the API.
    
    Args:
        session_id: The session ID in format 'PTK_X_YYYY' where X is session number and YYYY is year
    
    Returns:
        Dict containing the raw JSON data if successful, None otherwise
    """
    # Convert session ID format from PTK_125_2024 to PTK 125/2024 vp
    session_num, year = session_id.split('_')[1:]
    formatted_id = f"PTK {session_num}/{year} vp"
    url_encoded_id = formatted_id.replace(' ', '+').replace('/', '%2F')
    
    # Base URL from the working example
    url = f'https://verkkolahetys.eduskunta.fi/api/v1/eventmetas/transcripts/{url_encoded_id}'
    
    # Headers required for the API request
    headers = {
        'accept': 'application/json, text/plain, */*',
        'accept-language': 'en-GB,en-US;q=0.9,en;q=0.8',
        'dnt': '1',
        'referer': f'https://verkkolahetys.eduskunta.fi/fi/taysistunnot/taysistunto-{session_num}-{year}',
        'sec-ch-ua': '"Chromium";v="131", "Not_A Brand";v="24"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"macOS"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
    }
    
    try:
        print(f"Trying URL: {url}")
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        # Parse the JSON response
        data = response.json()
        if not data:
            print(f"No data found for session {session_id}")
            return None
            
        return data
        
    except requests.RequestException as e:
        print(f"Error fetching data: {e}")
        print(f"Response: {response.text if 'response' in locals() else 'No response'}")
        return None
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}")
        return None

def process_session(session_id: str, output_dir: str = None) -> Optional[Dict]:
    """
    Process a parliamentary session: fetch the raw JSON and parse it.
    
    Args:
        session_id: The session ID in format 'PTK_X_YYYY'
        output_dir: Optional directory to save the output files
    
    Returns:
        Dict containing the parsed session data if successful, None otherwise
    """
    # Fetch the raw JSON
    print(f"Fetching data for session {session_id}...")
    raw_data = fetch_session_json(session_id)
    if not raw_data:
        return None
    
    # Save raw JSON if output directory is specified
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        raw_json_path = os.path.join(output_dir, f"raw_{session_id}.json")
        with open(raw_json_path, "w", encoding="utf-8") as f:
            json.dump(raw_data, f, indent=2, ensure_ascii=False)
        print(f"Raw JSON saved to {raw_json_path}")
    
    # Parse the JSON
    print("Parsing session data...")
    parsed_data = parse_session_json(raw_data)
    
    # Save parsed JSON if output directory is specified
    if output_dir:
        parsed_json_path = os.path.join(output_dir, f"parsed_{session_id}.json")
        with open(parsed_json_path, "w", encoding="utf-8") as f:
            json.dump(parsed_data, f, indent=2, ensure_ascii=False)
        print(f"Parsed JSON saved to {parsed_json_path}")
    
    # Print session statistics
    stats = parsed_data["metadata"]["statistics"]
    print(f"\nSession {session_id} statistics:")
    print(f"Regular speeches: {stats['regular_speech_count']}")
    print(f"Chairman statements: {stats['chairman_statement_count']}")
    print(f"Total items: {stats['total_items']}")
    
    print("\nSpeakers in this session:")
    for speaker in parsed_data["metadata"]["speakers"]:
        print(f"- {speaker['name']} ({speaker['party']})")
    
    return parsed_data

if __name__ == "__main__":
    # Example usage
    session_id = "PTK_125_2024"  # Example session ID
    output_dir = "output"  # Directory to save output files
    
    parsed_data = process_session(session_id, output_dir) 