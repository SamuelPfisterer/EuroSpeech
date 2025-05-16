import pandas as pd
import os

def process_croatian_data():
    # Read the input CSV
    input_file = "Croatia/croatian_parliament_data.csv"
    df = pd.read_csv(input_file)
    
    # Create unique IDs by combining convocation, session, and order_no
    df['transcript_id'] = df.apply(lambda row: f"{row['convocation']}_{row['session']}_{row['order_no']}", axis=1)
    
    # Rename columns to match required format
    df['html_link'] = df['transcript_url']
    df['generic_video_link'] = df['recording_url']
    
    # Select and reorder columns according to documentation
    output_df = df[['transcript_id', 'generic_video_link', 'html_link']]
    
    # Remove rows where video link is empty (ends with tdrid=)
    output_df = output_df[~output_df['generic_video_link'].str.endswith('tdrid=')]
    
    # Create output directory if it doesn't exist
    os.makedirs('Croatia', exist_ok=True)
    
    # Save to new CSV file
    output_file = "Croatia/croatian_parliament_media_links_ready_to_download.csv"
    output_df.to_csv(output_file, index=False)
    
    print(f"Processed {len(df)} rows")
    print(f"Output saved to {output_file}")
    print(f"Final dataset contains {len(output_df)} rows with valid video links")

if __name__ == "__main__":
    process_croatian_data() 