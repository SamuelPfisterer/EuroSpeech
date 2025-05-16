import pandas as pd
import random
from getting_speech_segments import extract_speeches_with_playwright
import json
from pathlib import Path
import time

def test_random_transcripts(num_samples=5):
    # Load transcript links
    df = pd.read_csv('transcript_links_with_dates.csv')
    
    # Sample random links and append /?all=true if not already present
    sample_links = df.sample(n=num_samples)
    sample_links['link'] = sample_links['link'].apply(lambda x: x if x.endswith('/?all=true') else f"{x}{'/' if not x.endswith('/') else ''}?all=true")
    
    results = []
    
    print(f"\nTesting {num_samples} random transcripts:")
    print("-" * 50)
    
    for idx, row in sample_links.iterrows():
        print(f"\nProcessing transcript {idx + 1}/{num_samples}")
        print(f"Date: {row['date']}")
        print(f"URL: {row['link']}")
        
        try:
            # Add a delay between requests
            if idx > 0:
                time.sleep(3)
            
            speeches = extract_speeches_with_playwright(row['link'])
            
            result = {
                'date': row['date'],
                'url': row['link'],
                'num_speeches': len(speeches),
                'success': True,
                'speeches': speeches
            }
            print(f"Successfully extracted {len(speeches)} speeches")
            
        except Exception as e:
            result = {
                'date': row['date'],
                'url': row['link'],
                'num_speeches': 0,
                'success': False,
                'error': str(e)
            }
            print(f"Failed to extract speeches: {str(e)}")
        
        results.append(result)
        print("-" * 50)
    
    # Save results to JSON for inspection
    output_dir = Path('test_results')
    output_dir.mkdir(exist_ok=True)
    
    with open(output_dir / 'speech_extraction_test.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print("\nTest Summary:")
    successful = sum(1 for r in results if r['success'])
    print(f"Successful extractions: {successful}/{num_samples}")
    total_speeches = sum(r['num_speeches'] for r in results if r['success'])
    print(f"Total speeches extracted: {total_speeches}")
    print(f"\nDetailed results saved to: test_results/speech_extraction_test.json")

if __name__ == "__main__":
    test_random_transcripts() 