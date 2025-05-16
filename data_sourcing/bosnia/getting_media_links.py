import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
import csv
from concurrent.futures import ThreadPoolExecutor
import tqdm
import os

# Set UTF-8 encoding explicitly
os.environ['PYTHONIOENCODING'] = 'utf-8'

def get_document_links(row):
    """Extract document links from a session page."""
    session_url = row['link_to_session']
    try:
        # Create a session to reuse for all requests
        session = requests.Session()
        response = session.get(session_url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find the session-box section
        session_box = soup.find('aside', class_='session-box')
        if not session_box:
            return None
        
        # Extract all links and their names
        links = {}
        for li in session_box.find_all('li'):
            link = li.find('a')
            if link:
                name = link.text.strip()
                href = link['href']
                if href.startswith('/'):
                    href = f"https://parlament.ba{href}"
                # Follow the redirect and get the final URL
                try:
                    redirect_response = session.get(href, allow_redirects=True)
                    final_url = redirect_response.url
                    links[name] = final_url
                except Exception as e:
                    print(f"Error following redirect for {href}: {str(e)}")
                    links[name] = href  # Fall back to original URL if redirect fails
        
        # Return all the data we need
        return {
            'session_date': row['date'],
            'session_title': row['session_title'],
            'session_url': session_url,
            'documents': links
        }
    except Exception as e:
        print(f"Error processing {session_url}: {str(e)}")
        return None

def main():
    # Read the CSV file with session links
    df = pd.read_csv('bosnia_HoR_session_links.csv')
    
    # Convert date strings to datetime objects for filtering
    df['date'] = pd.to_datetime(df['date'], format='%d.%m.%Y', errors='coerce')
    
    # Filter for sessions after 2007
    df = df[df['date'].dt.year > 2007].copy()
    
    print(f"\nProcessing {len(df)} sessions after 2007...")
    
    # Process sessions using ThreadPoolExecutor instead of ProcessPool
    all_results = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        # Create a list of futures
        future_to_row = {executor.submit(get_document_links, row): row for _, row in df.iterrows()}
        
        # Process results as they complete
        for future in tqdm.tqdm(future_to_row, desc="Processing sessions"):
            try:
                result = future.result()
                if result:
                    all_results.append(result)
            except Exception as e:
                print(f"Error processing session: {str(e)}")
            time.sleep(0.1)  # Small delay between requests
    
    # Collect all unique document types
    document_types = set()
    for result in all_results:
        document_types.update(result['documents'].keys())
    
    # Create fieldnames with session info and all document types
    fieldnames = ['session_date', 'session_title', 'session_url'] + sorted(list(document_types))
    
    # Convert results to rows for CSV
    csv_rows = []
    for result in all_results:
        row = {
            'session_date': result['session_date'],
            'session_title': result['session_title'],
            'session_url': result['session_url']
        }
        # Add document URLs
        for doc_type in document_types:
            row[doc_type] = result['documents'].get(doc_type, '')
        csv_rows.append(row)
    
    # Sort rows by date
    csv_rows.sort(key=lambda x: pd.to_datetime(x['session_date'], format='%d.%m.%Y'), reverse=True)
    
    # Save to CSV file
    output_file = 'session_documents.csv'
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(csv_rows)
    
    print(f"\nFinished! Document links have been saved to {output_file}")
    print(f"Processed {len(csv_rows)} sessions with {len(document_types)} different document types")

if __name__ == "__main__":
    main()
