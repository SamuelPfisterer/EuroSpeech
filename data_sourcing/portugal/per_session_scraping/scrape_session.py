import requests
from bs4 import BeautifulSoup
import pandas as pd
from dataclasses import dataclass
from typing import List, Optional
from pathlib import Path
import csv
import re

@dataclass
class Intervention:
    session_link: str
    intervention_number: int
    start_time: float
    end_time: float
    speaker_name: str
    party: str
    party_full: str
    duration: str
    intervention_type: str
    individual_link: str

@dataclass
class SessionDetails:
    session_link: str
    video_link: str
    transcript_link: Optional[str]
    interventions: List[Intervention]

def extract_duration_and_type(text: str) -> tuple[str, str]:
    """Extract duration and intervention type from the text."""
    parts = text.strip().split('\n')
    duration = parts[0].strip()
    intervention_type = parts[1].strip() if len(parts) > 1 else ""
    return duration, intervention_type

def extract_party_info(party_text: str) -> tuple[str, str]:
    """Extract party abbreviation and full name."""
    party_text = party_text.strip()
    match = re.match(r'([^\s-]+)(?:\s*-\s*(.+))?', party_text)
    if match:
        return match.group(1), match.group(2) or match.group(1)
    return party_text, party_text

def scrape_session_details(session_link: str) -> SessionDetails:
    """Scrape all details for a single session."""
    try:
        print(f"\nProcessing session: {session_link}")
        response = requests.get(session_link)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Get transcript link
        transcript_link = None
        transcript_anchor = soup.find('a', string=re.compile(r'Ver diário nos Debates Parlamentares'))
        if transcript_anchor:
            transcript_link = transcript_anchor['href']
            print(f"Found transcript link: {transcript_link}")
        
        # Get interventions
        interventions = []
        intervention_container = soup.find('div', class_='meeting-intervention-container')
        
        if intervention_container:
            intervention_divs = intervention_container.find_all('div', class_='meeting-intervention-holder')
            print(f"Found {len(intervention_divs)} interventions")
            
            for div in intervention_divs:
                # Extract intervention data
                intervention_number = int(div['data-intervention-number'])
                start_time = float(div['data-intervention-start-time'])
                end_time = float(div['data-intervention-end-time'])
                
                # Get speaker name
                speaker_div = div.find('div', class_='video-list-single-line-information-holder')
                speaker_name = speaker_div.find('strong').text.strip() if speaker_div else "Unknown"
                
                # Get party information
                party_div = speaker_div.find_next('div', class_='video-list-single-line-information-holder')
                party_text = party_div.text.strip() if party_div else ""
                party_abbrev, party_full = extract_party_info(party_text)
                
                # Get duration and type
                info_div = party_div.find_next('div', class_='video-list-single-line-information-holder')
                duration, intervention_type = extract_duration_and_type(info_div.text) if info_div else ("", "")
                
                # Get individual intervention link
                individual_link = ""
                link_element = div.find('a', class_='new-window')
                if link_element:
                    individual_link = f"https://av.parlamento.pt{link_element['href']}"
                
                intervention = Intervention(
                    session_link=session_link,
                    intervention_number=intervention_number,
                    start_time=start_time,
                    end_time=end_time,
                    speaker_name=speaker_name,
                    party=party_abbrev,
                    party_full=party_full,
                    duration=duration,
                    intervention_type=intervention_type,
                    individual_link=individual_link
                )
                interventions.append(intervention)
        
        return SessionDetails(
            session_link=session_link,
            video_link=session_link,  # Using the same link as provided
            transcript_link=transcript_link,
            interventions=interventions
        )
    
    except Exception as e:
        print(f"Error processing session {session_link}: {e}")
        return None

def save_session_details(sessions: List[SessionDetails], output_dir: Path):
    """Save session details and interventions to separate CSV files."""
    # Create output directory if it doesn't exist
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save session details
    sessions_data = [
        {
            'session_link': s.session_link,
            'video_link': s.video_link,
            'transcript_link': s.transcript_link
        }
        for s in sessions if s is not None
    ]
    pd.DataFrame(sessions_data).to_csv(
        output_dir / 'session_details.csv',
        index=False
    )
    
    # Save interventions
    interventions_data = [
        {
            'session_link': i.session_link,
            'intervention_number': i.intervention_number,
            'start_time': i.start_time,
            'end_time': i.end_time,
            'speaker_name': i.speaker_name,
            'party': i.party,
            'party_full': i.party_full,
            'duration': i.duration,
            'intervention_type': i.intervention_type,
            'individual_link': i.individual_link
        }
        for s in sessions if s is not None
        for i in s.interventions
    ]
    pd.DataFrame(interventions_data).to_csv(
        output_dir / 'interventions.csv',
        index=False
    )

def main():
    # Read the session links CSV
    input_csv = Path('../session_links/all_session_recordings.csv')
    output_dir = Path('scraped_data')
    
    # Read session links
    df = pd.read_csv(input_csv)
    
    # Process each session
    all_sessions = []
    total = len(df)
    
    for idx, row in df.iterrows():
        print(f"\nProcessing session {idx + 1}/{total}")
        session_details = scrape_session_details(row['link_to_session'])
        if session_details:
            all_sessions.append(session_details)
            # Save intermediate results every 10 sessions
            if (idx + 1) % 10 == 0:
                save_session_details(all_sessions, output_dir)
                print(f"Saved intermediate results after {idx + 1} sessions")
    
    # Save final results
    save_session_details(all_sessions, output_dir)
    print(f"\nProcessing complete. Results saved in {output_dir}")
    print(f"Total sessions processed successfully: {len(all_sessions)} out of {total}")

if __name__ == "__main__":
    main()
