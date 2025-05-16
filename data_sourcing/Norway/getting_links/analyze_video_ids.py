import csv
import random
from urllib.parse import urlparse, parse_qs

def analyze_video_urls(csv_path: str, sample_size: int = 10):
    """Analyze video URLs from random samples to understand structure."""
    # Read all rows
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    
    # Get random samples
    samples = random.sample(rows, sample_size)
    
    print(f"\nAnalyzing {sample_size} random video URLs:\n")
    for i, row in enumerate(samples, 1):
        print(f"Sample {i}:")
        print(f"Date: {row['date']}")
        print(f"Video URL: {row['video_url']}")
        
        # Parse URL parameters
        parsed = urlparse(row['video_url'])
        params = parse_qs(parsed.query)
        
        print("URL Parameters:")
        for key, value in params.items():
            print(f"  {key}: {value[0]}")
        
        print(f"Video Type: {row['video_type']}")
        print(f"Video Format: {row['video_format']}")
        print()

if __name__ == "__main__":
    analyze_video_urls('output/combined_links.csv') 