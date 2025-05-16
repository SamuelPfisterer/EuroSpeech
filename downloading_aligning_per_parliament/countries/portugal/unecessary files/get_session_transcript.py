import requests
from bs4 import BeautifulSoup
from pathlib import Path
from urllib.parse import urlparse
import re
import time

def get_transcript_link(session_link: str) -> str:
    """Extract transcript link from a parliamentary session page."""
    try:
        print(f"Processing session: {session_link}")
        response = requests.get(session_link)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        transcript_anchor = soup.find('a', string=re.compile(r'Ver diário nos Debates Parlamentares'))
        if transcript_anchor:
            transcript_link = transcript_anchor['href']
            print(f"Found transcript link: {transcript_link}")
            return transcript_link
        else:
            print("No transcript link found")
            return None
    except Exception as e:
        print(f"Error processing session {session_link}: {e}")
        return None

def download_transcript(transcript_url: str, output_dir: str = "transcripts") -> bool:
    """Download transcript text from debates.parlamento.pt."""
    try:
        if not transcript_url:
            return False

        # Create output directory if it doesn't exist
        Path(output_dir).mkdir(exist_ok=True)

        # Parse the URL to extract parameters
        parsed_url = urlparse(transcript_url)
        path_parts = parsed_url.path.split('/')

        # Extract parameters from URL path
        parameters = {
            "periodo": path_parts[2],
            "publicacao": path_parts[3],
            "serie": path_parts[4],
            "legis": path_parts[5],
            "sessao": path_parts[6],
            "numero": path_parts[7],
            "data": path_parts[8],
            "exportType": "txt",
            "exportControl": "documentoCompleto"
        }

        # Create filename from parameters
        filename = f"transcript_{parameters['legis']}_{parameters['sessao']}_{parameters['numero']}.txt"
        
        # Make the POST request
        response = requests.post("https://debates.parlamento.pt/pagina/export", data=parameters)
        
        if response.status_code == 200:
            file_path = Path(output_dir) / filename
            with open(file_path, "w", encoding="utf-8") as file:
                file.write(response.text)
            print(f"Transcript saved to: {file_path}")
            return True
        else:
            print(f"Failed to download transcript. Status code: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"Error downloading transcript: {e}")
        return False

def main():
    """Test the functions with a few example links."""
    # Test with actual links from our dataset
    test_links = [
        "https://av.parlamento.pt/videos/Plenary/10/1/128",
        "https://av.parlamento.pt/videos/Plenary/12/3/85",
        "https://av.parlamento.pt/videos/Plenary/15/1/154",
        "https://av.parlamento.pt/videos/Plenary/13/4/24",
        "https://av.parlamento.pt/videos/Plenary/15/1/106"
    ]
    
    for i, session_link in enumerate(test_links, 1):
        print(f"\nProcessing session {i} of {len(test_links)}")
        transcript_link = get_transcript_link(session_link)
        if transcript_link:
            download_transcript(transcript_link)
        
        # Wait 2 seconds before next session (except for the last one)
        if i < len(test_links):
            print("\nWaiting 2 seconds before next session...")
            time.sleep(2)

if __name__ == "__main__":
    main() 