import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime
import pandas as pd
from tqdm import tqdm

def parse_date_from_transcript_link(transcript_link):
    """Extracts the date from the transcript link and returns it as a datetime object."""
    match = re.search(r'/et/(\d{12})', transcript_link)
    if match:
        date_str = match.group(1)
        return datetime.strptime(date_str, '%Y%m%d%H%M').strftime('%Y-%m-%d %H:%M:%S')
    return None

def get_all_transcript_links(base_url):
    """Collects all transcript links from the website."""
    transcript_links = []
    page = 1
    total_links = 0
    total_pages = 0

    # First, count total pages
    print("Counting total pages...")
    while True:
        url = f"{base_url}&page={page}"
        response = requests.get(url)
        if response.status_code != 200:
            break
        soup = BeautifulSoup(response.text, 'html.parser')
        if not soup.find('a', href=re.compile(r'/et/\d{12}#')):
            break
        total_pages += 1
        page += 1

    print(f"\nFound {total_pages} pages to process")

    # Reset for actual scraping
    page = 1
    with tqdm(total=total_pages, desc="Processing pages") as pbar:
        while True:
            url = f"{base_url}&page={page}"
            response = requests.get(url)
            if response.status_code != 200:
                break

            soup = BeautifulSoup(response.text, 'html.parser')
            paragraphs = soup.find_all('p')
            found_links_on_page = 0

            for p in paragraphs:
                transcript_link_tag = p.find('a', href=re.compile(r'/et/\d{12}#'))
                if transcript_link_tag:
                    transcript_link = transcript_link_tag['href'].split('#')[0]
                    transcript_links.append(transcript_link)
                    found_links_on_page += 1

            total_links += found_links_on_page
            pbar.set_postfix({'Links found': total_links})
            pbar.update(1)
            page += 1
            if not found_links_on_page and total_pages > 0: # Stop if no links found on a page after the first
                break

    print(f"\nProcessing complete. Found {total_links} transcript links across {page-1} pages")
    return transcript_links

if __name__ == "__main__":
    start_year = 2014
    end_year = 2025  # Up to (but not including) this year

    all_transcript_data = []

    for year in range(start_year, end_year):
        base_url = f"https://stenogrammid.riigikogu.ee/et?rangeFrom=01.01.{year}&rangeTo=01.01.{year+1}&singleDate=&phrase=&type=ALL"
        print(f"\n--- Scraping transcript links for the year {year} ---")
        transcript_links = get_all_transcript_links(base_url)
        for link in transcript_links:
            date = parse_date_from_transcript_link(link)
            all_transcript_data.append({'transcript_link': link, 'date': date})

    # Create a Pandas DataFrame
    df = pd.DataFrame(all_transcript_data)

    # Save the DataFrame to a CSV file
    csv_filename = "scraping-parliaments-internally/Estonia/FlorianFix/transcript_links_with_dates.csv"
    df.to_csv(csv_filename, index=False)

    print(f"\nTranscript links and their dates have been saved to {csv_filename}")