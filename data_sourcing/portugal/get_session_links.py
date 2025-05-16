import requests
from bs4 import BeautifulSoup
from dataclasses import dataclass
from typing import List, Dict
import re
import csv
from pathlib import Path

@dataclass
class SessionRecording:
    cycle: int
    legislation: int
    session_title: str
    session_number: int
    session_date: str
    link_to_session: str

# Dictionary mapping cycles to their number of legislations
CYCLE_LEGISLATION_MAP = {
    10: 4,
    11: 2,
    12: 4,
    13: 4,
    14: 3,
    15: 2,
    16: 1
}

def extract_session_info(session_div, cycle: int, legislation: int) -> SessionRecording:
    # Find the h4 element containing the session title and link
    h4_element = session_div.find('h4', class_='h6')
    if not h4_element or not h4_element.a:
        return None
    
    # Get the link and full title text
    link = h4_element.a['href']
    full_title = h4_element.a.text.strip()
    
    # Extract session number and date using regex
    match = re.search(r'Reunião N.º (\d+) \((\d{2}/\d{2}/\d{4})\)', full_title)
    if not match:
        return None
    
    session_number = int(match.group(1))
    session_date = match.group(2)
    
    return SessionRecording(
        cycle=cycle,
        legislation=legislation,
        session_title=full_title,
        session_number=session_number,
        session_date=session_date,
        link_to_session=f"https://av.parlamento.pt{link}"
    )

def get_session_recordings(cycle: int, legislation: int) -> List[SessionRecording]:
    url = f"https://av.parlamento.pt/videos/Plenary/{cycle}/{legislation}"
    
    try:
        # Send GET request to the URL
        response = requests.get(url)
        response.raise_for_status()
        
        # Parse the HTML content
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find the container div with all sessions
        sessions_container = soup.find('div', id='panel-meeting-sessions')
        if not sessions_container:
            print(f"No sessions found for cycle {cycle}, legislation {legislation}")
            return []
        
        # Find all session divs
        session_divs = sessions_container.find_all('div', class_='grid-x grid-margin-x')
        
        # Extract information from each session div
        sessions = []
        for div in session_divs:
            session = extract_session_info(div, cycle, legislation)
            if session:
                sessions.append(session)
        
        return sessions
    except Exception as e:
        print(f"Error processing cycle {cycle}, legislation {legislation}: {e}")
        return []

def save_to_csv(sessions: List[SessionRecording], filename: str):
    if not sessions:
        print("No sessions to save")
        return
    
    fieldnames = ['cycle', 'legislation', 'session_number', 'session_title', 'session_date', 'link_to_session']
    
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for session in sessions:
            writer.writerow({
                'cycle': session.cycle,
                'legislation': session.legislation,
                'session_number': session.session_number,
                'session_title': session.session_title,
                'session_date': session.session_date,
                'link_to_session': session.link_to_session
            })

def main():
    all_sessions = []
    
    # Create output directory if it doesn't exist
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    
    # Iterate through all cycles and their legislations
    for cycle, num_legislations in CYCLE_LEGISLATION_MAP.items():
        print(f"\nProcessing cycle {cycle}")
        for legislation in range(1, num_legislations + 1):
            print(f"  Processing legislation {legislation}")
            sessions = get_session_recordings(cycle, legislation)
            print(f"    Found {len(sessions)} sessions")
            all_sessions.extend(sessions)
    
    # Save all sessions to CSV
    output_file = output_dir / "all_session_recordings.csv"
    save_to_csv(all_sessions, str(output_file))
    print(f"\nTotal sessions found: {len(all_sessions)}")
    print(f"Results saved to: {output_file}")

if __name__ == "__main__":
    main()
