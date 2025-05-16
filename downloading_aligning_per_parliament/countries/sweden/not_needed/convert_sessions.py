import pandas as pd
import re

def extract_video_id(url):
    """Extract video ID from the URL."""
    # The video ID is the last part of the URL before the trailing slash
    # Example: .../debatt-om-forslag/utgiftsomrade-9-halsovard-sjukvard-och-social_hc01sou1/
    match = re.search(r'_([^/]+)/?$', url)
    return match.group(1) if match else None

def convert_sessions_csv():
    # Read the original CSV
    df = pd.read_csv('sessions.csv')
    
    # Extract video_id from the link column
    df['video_id'] = df['link'].apply(extract_video_id)
    
    # Add processed link columns using the same link
    df['processed_video_link'] = df['link']
    df['processed_transcript_html_link'] = df['link']
    
    # Reorder columns
    new_df = df[[
        'title',
        'date',
        'duration',
        'video_id',
        'processed_video_link',
        'processed_transcript_html_link'
    ]]
    
    # Save to new CSV
    new_df.to_csv('sessions_new.csv', index=False)
    print("Created new sessions_new.csv with updated format")

if __name__ == "__main__":
    convert_sessions_csv() 