import pandas as pd
from playwright.sync_api import sync_playwright
import time
import csv

def extract_speech_segments(page):
    segments = []
    # Find all speech segments
    speech_containers = page.query_selector_all("div.singleContentContainer")
    
    for container in speech_containers:
        # Extract speaker name
        speaker_element = container.query_selector("div.contentHeader.speaker h2")
        if not speaker_element:
            continue
        speaker = speaker_element.inner_text()
        
        # Extract speech text
        text_element = container.query_selector("dd.textColor")
        if not text_element:
            continue
        text = text_element.inner_text()
        
        segments.append({
            'speaker': speaker,
            'text': text
        })
    
    return segments

def main():
    # Read the CSV file with transcript links
    df = pd.read_csv('Croatia/croatian_parliament_data.csv')
    
    # Create a new CSV file for the speech segments
    with open('Croatia/speech_segments.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['transcript_url', 'speaker', 'text'])
        writer.writeheader()
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()
            
            for idx, row in df.iterrows():
                transcript_url = row['transcript_url']
                print(f"Processing transcript {idx + 1}/{len(df)}: {transcript_url}")
                
                try:
                    page.goto(transcript_url)
                    # Wait for the content to load
                    page.wait_for_selector("div.singleContentContainer", timeout=10000)
                    
                    # Extract speech segments
                    segments = extract_speech_segments(page)
                    
                    # Write segments to CSV
                    for segment in segments:
                        writer.writerow({
                            'transcript_url': transcript_url,
                            'speaker': segment['speaker'],
                            'text': segment['text']
                        })
                    
                    # Small delay to be nice to the server
                    time.sleep(1)
                    
                except Exception as e:
                    print(f"Error processing {transcript_url}: {str(e)}")
                    continue
            
            browser.close()

if __name__ == "__main__":
    main()
