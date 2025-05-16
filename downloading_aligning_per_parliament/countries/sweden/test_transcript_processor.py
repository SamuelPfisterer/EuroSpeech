import pandas as pd
import os
import logging
from transcript_processors import process_transcript_text
import random

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def test_transcript_processing():
    # Read the CSV file
    df = pd.read_csv('links/sweden_links.csv')
    
    # Select 10 random samples
    test_cases = df.sample(n=10)
    
    # Create test output directory
    test_dir = 'test_transcripts'
    os.makedirs(test_dir, exist_ok=True)
    
    # Process each test case
    results = []
    for idx, row in enumerate(test_cases.iterrows()):
        row = row[1]  # Get the row data from the tuple
        try:
            logging.info(f"\nProcessing test case {idx + 1}")
            logging.info(f"Title: {row['title']}")
            logging.info(f"Duration: {row['duration']}")
            
            # Process transcript
            transcript = process_transcript_text(row['processed_transcript_text_link'])
            
            # Save to file
            output_file = os.path.join(test_dir, f"test_transcript_{row['video_id']}.txt")
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(transcript)
            
            # Get file size
            size_kb = os.path.getsize(output_file) / 1024
            
            results.append({
                'status': 'Success',
                'video_id': row['video_id'],
                'duration': row['duration'],
                'output_file': output_file,
                'size_kb': f"{size_kb:.2f} KB"
            })
            
            logging.info(f"Successfully processed and saved to: {output_file}")
            logging.info(f"Transcript size: {size_kb:.2f} KB")
            
        except Exception as e:
            logging.error(f"Failed to process {row['video_id']}: {str(e)}")
            results.append({
                'status': 'Failed',
                'video_id': row['video_id'],
                'duration': row['duration'],
                'error': str(e)
            })
    
    # Print summary
    logging.info("\n=== Test Summary ===")
    for result in results:
        status = "✓" if result['status'] == 'Success' else "✗"
        logging.info(f"{status} {result['video_id']} ({result['duration']})")
        if result['status'] == 'Success':
            logging.info(f"   Saved to: {result['output_file']}")
            logging.info(f"   Size: {result['size_kb']}")
        else:
            logging.info(f"   Error: {result['error']}")

if __name__ == "__main__":
    test_transcript_processing() 