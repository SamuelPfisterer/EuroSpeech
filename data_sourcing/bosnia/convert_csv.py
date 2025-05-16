import pandas as pd
import re

def extract_session_id(url):
    """Extract session ID from the session URL."""
    match = re.search(r'id=(\d+)', url)
    return match.group(1) if match else None

def convert_csv(input_file='session_documents.csv', output_file='bosnia_herzegovina_media_links_ready_to_download.csv'):
    # Read input CSV
    df = pd.read_csv(input_file)
    
    # Create new dataframe with required format
    new_df = pd.DataFrame()
    
    # Extract session ID as video_id
    new_df['video_id'] = df['session_url'].apply(extract_session_id)
    
    # Map audio links (they will be converted to opus format by the download script)
    new_df['mp4_video_link'] = df['Audio zapis']
    
    # Map PDF transcript links
    new_df['pdf_link'] = df['Stenogram']
    
    # Add session metadata as additional columns
    new_df['session_date'] = df['session_date']
    new_df['session_title'] = df['session_title']
    new_df['session_url'] = df['session_url']
    
    # Drop rows if either audio or transcript is missing
    new_df = new_df.dropna(subset=['mp4_video_link', 'pdf_link'], how='any')
    
    # Save to new CSV file
    new_df.to_csv(output_file, index=False)
    print(f"Converted CSV saved to {output_file}")
    print("Note: PDFs will be downloaded to the pdf_transcripts subfolder")

if __name__ == "__main__":
    convert_csv() 