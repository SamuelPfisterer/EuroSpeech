import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from typing import Optional, List
import pandas as pd
import time
from tqdm import tqdm

def get_video_url(url: str) -> Optional[str]:
    """
    Extract video URL from a session page using direct HTML parsing.
    """
    selectors = [
        'video', 'source', 'a', 'link', 
        '[type*="video"]',
        '[src*=".mp4"], [src*=".m3u8"], [src*=".mpd"]',
        '[href*=".mp4"], [href*=".m3u8"], [href*=".mpd"]'
    ]
    
    media_extensions = [
        '.mp4', '.m4v', '.m4s', '.m3u8', '.m3u', 
        '.mpd', '.webm', '.mkv', '.ts', '.mov', '.avi'
    ]

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Check all potential video sources
        for selector in selectors:
            elements = soup.select(selector)
            for element in elements:
                for attr in ['src', 'href', 'data-src', 'data-video']:
                    if value := element.get(attr):
                        video_url = urljoin(url, value)
                        if any(video_url.lower().endswith(ext) for ext in media_extensions):
                            try:
                                if requests.head(video_url, timeout=5).status_code == 200:
                                    return video_url
                            except:
                                continue
        return None
    except Exception as e:
        print(f"Error processing URL {url}: {str(e)}")
        return None

def main():
    # Read the sessions CSV file
    try:
        df = pd.read_csv('sweden/sessions.csv')
    except Exception as e:
        print(f"Error reading sessions.csv: {str(e)}")
        return

    # Add a new column for video URLs if it doesn't exist
    if 'video_url' not in df.columns:
        df['video_url'] = None

    # Process each session
    print("Extracting video URLs...")
    for idx in tqdm(df.index):
        if pd.isna(df.at[idx, 'video_url']):  # Only process rows without video URL
            session_url = df.at[idx, 'url']
            video_url = get_video_url(session_url)
            
            if video_url:
                df.at[idx, 'video_url'] = video_url
            
            # Add a small delay to avoid overwhelming the server
            time.sleep(0.5)

    # Save the updated DataFrame
    try:
        df.to_csv('sweden/sessions.csv', index=False)
        print("Successfully updated sessions.csv with video URLs")
    except Exception as e:
        print(f"Error saving sessions.csv: {str(e)}")

if __name__ == "__main__":
    main()
