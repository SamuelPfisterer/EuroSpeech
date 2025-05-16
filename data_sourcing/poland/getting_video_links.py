from botasaurus.browser import browser, Driver
from botasaurus.soupify import soupify
from botasaurus.browser import Wait
import csv
import time
import pandas as pd

def get_session_video_links():
    # Read the CSV file
    df = pd.read_csv('poland_session_links.csv')
    # Get only rows where video_link is not null/empty
    video_links = df[df['video_link'].notna()][['link_to_session', 'video_link']]
    # Return only first 3 links for testing
    return video_links.to_dict('records')

@browser(
    reuse_driver=True,
    headless=False,
    data=get_session_video_links()
)
def scrape_video_links(driver: Driver, session_data):
    original_video_link = session_data['video_link']
    session_link = session_data['link_to_session']
    
    print(f"\nProcessing video page: {original_video_link}")
    
    # Visit the video page
    driver.get(original_video_link)
    
    # Wait for the content container
    time.sleep(2)  # Add small delay
    container = driver.select(".modul-posiedzenia", wait=Wait.VERY_LONG)
    
    # Get the page source as BeautifulSoup object
    soup = soupify(driver)
    
    results = []
    # Find all links that contain 'av8.senat.pl'
    links = soup.find_all('a', href=lambda href: href and 'av8.senat.pl' in href)
    
    for link in links:
        video_url = link['href']
        video_text = link.get_text(strip=True)
        
        results.append({
            'session_link': session_link,
            'original_video_link': original_video_link,
            'video_url': video_url,
            'video_text': video_text
        })
    
    if results:
        print(f"Found {len(results)} video link(s)")
    else:
        print("No video links found")
    
    return results

def save_results(all_results):
    # Save all results to CSV
    csv_file = 'poland_video_links.csv'
    fieldnames = ["session_link", "original_video_link", "video_url", "video_text"]
    
    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_results)
    
    print(f"Results saved to '{csv_file}'")

if __name__ == "__main__":
    # Get results for all video pages
    results_per_page = scrape_video_links()
    
    # Flatten the list of results
    flattened_results = []
    for page_results in results_per_page:
        if page_results:  # Check if we got valid results
            flattened_results.extend(page_results)
    
    print(f"Total video links found: {len(flattened_results)}")
    # Save all results to CSV
    save_results(flattened_results)
