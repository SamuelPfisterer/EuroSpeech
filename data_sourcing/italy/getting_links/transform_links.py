import pandas as pd
import requests
from urllib.parse import urlparse, parse_qs
import random
from collections import defaultdict

def html_to_akn_link(html_link):
    # Parse the URL and get query parameters
    parsed = urlparse(html_link)
    params = parse_qs(parsed.query)
    
    # Extract leg and id parameters
    leg = params.get('leg', [''])[0]
    doc_id = params.get('id', [''])[0]
    
    if not leg or not doc_id:
        return None
        
    # Construct AKN link
    akn_link = f"https://www.senato.it/leg/{leg}/BGT/Testi/Resaula/0{doc_id}.akn"
    return akn_link

def create_full_html_link(html_link):
    # Add the doc_dc parameter to the HTML link
    return f"{html_link}&part=doc_dc"

def validate_url(url):
    try:
        response = requests.head(url, timeout=5)
        return response.status_code == 200
    except:
        return False

# Read the CSV file
df = pd.read_csv('italian_senate_meetings_ready_to_download_no_duplicates.csv')

# Add full HTML links column
df['full_html'] = df['html_link'].apply(create_full_html_link)

# Test random samples from each legislature
print("\nTesting full HTML links for sample records:")
print("-" * 80)

for leg in sorted(df['legislation'].unique()):
    leg_df = df[df['legislation'] == leg]
    sample_size = min(2, len(leg_df))
    samples = leg_df.sample(n=sample_size)
    
    print(f"\nLegislature {leg} Samples:")
    print("-" * 40)
    for _, row in samples.iterrows():
        print(f"Date: {row['date']}")
        print(f"Sitting number: {row['sitting_number']}")
        print(f"Full HTML: {row['full_html']}")
        
        # Test link validity
        is_valid = validate_url(row['full_html'])
        print(f"Link valid: {'Yes' if is_valid else 'No'}")
        print("-" * 40)

# Save updated CSV
df.to_csv('italian_senate_meetings_with_full_html.csv', index=False)
print("\nUpdated CSV saved with full HTML links") 