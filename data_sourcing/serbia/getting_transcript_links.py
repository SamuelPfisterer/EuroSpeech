import time
import random
import re
from tqdm import tqdm
from typing import List, Dict
from bs4 import BeautifulSoup
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from botasaurus.browser import browser, Driver
from botasaurus.soupify import soupify
from botasaurus.browser import Wait
from tenacity import retry, stop_after_attempt, wait_exponential
import csv
import json

CONVOCATIONS = {
    "2012": "https://otvoreniparlament.rs/transkript?od=&do=&saziv=60&kljucnaRec=&govornik=",
    "2014": "https://otvoreniparlament.rs/transkript?od=&do=&saziv=61&kljucnaRec=&govornik=",
    "2016": "https://otvoreniparlament.rs/transkript?od=&do=&saziv=62&kljucnaRec=&govornik=",
    "2020": "https://otvoreniparlament.rs/transkript?od=&do=&saziv=63&kljucnaRec=&govornik=",
    "2022": "https://otvoreniparlament.rs/transkript?od=&do=&saziv=64&kljucnaRec=&govornik=",
    "2024": "https://otvoreniparlament.rs/transkript?od=&do=&saziv=65&kljucnaRec=&govornik="
}

PAGES = {
    "2012": 18,
    "2014": 24,
    "2016": 40,
    "2020": 15,
    "2022": 8,
    "2024": 4
}

def scrape_transcripts():
    """
    Iterates through the CONVOCATIONS dictionary where values are URLs,
    scrapes transcript data from each page and saves to CSV.
    """
    transcript_data = []
    
    for convocation, url in CONVOCATIONS.items():
        # We assign each transcript of a convocation a unique no., starting from 0
        current_numbering = 0
        for page in tqdm(range(1, PAGES[convocation] + 1), desc=f"Pages for {convocation}"):
            print(f"Processing convocation {convocation} and page {page}")
            try:
                url = url + f"&page={page}"
                # We pass a dictionary, since this function somehow can only take one additional argument
                d = {"convocation": convocation, "url": url, "current_numbering": current_numbering}
                convocation_data, current_numbering = scrape_convocation_pages(d)
                transcript_data.extend(convocation_data)
            except Exception as e:
                print(f"Error processing convocation {convocation}: {e}")
                
        print(f"Finished processing convocation {convocation} with {current_numbering} transcripts.")
    return transcript_data

@browser(reuse_driver=False, headless=False)
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=5, max=60))
def scrape_convocation_pages(driver: Driver, d: Dict) -> List[Dict]:
    """
    Scrapes all pages for a given convocation URL.
    Uses Botosaurus to bypass Cloudflare and Selenium for page interactions.
    We only need the convocation for the transcript_id.
    """
    # extract the url and convocation from the dictionary
    url = d["url"]
    convocation = d["convocation"]
    current_numbering = d["current_numbering"]
    page = int(url.split('page=')[-1])  # Extract page number from URL

    transcript_data = []

    # Randomized delay before request
    time.sleep(random.uniform(3, 7))

    driver.get(url)
    
    time.sleep(15)
    soup = soupify(driver)
    
    rows = soup.find_all('div', class_='row')
    num_rows = len(rows)
    
    # Log if number of rows is not 10
    if num_rows != 23:
        abnormal_rows = {
            'convocation': convocation,
            'page': page,
            'num_rows': num_rows
        }
        # Append to JSON file
        try:
            with open('abnormal_row_counts.json', 'r') as f:
                data = json.load(f)
        except FileNotFoundError:
            data = []
        
        data.append(abnormal_rows)
        
        with open('abnormal_row_counts.json', 'w') as f:
            json.dump(data, f, indent=4)

    print("Found", num_rows, "rows")
    #print(rows)

    # Initialize counter for rows with link elements
    rows_with_links = 0
    
    for row in rows:
        # Look for anchor tag containing transcript link. This is because there are abundant rows that we ignore.
        link_element = row.find('a', href=lambda x: x and '/transkript/' in x)
        #link_element = row.select('a[href*="/transkript/"]')
        # Skip if no transcript link found
        if not link_element:
            #print("No transcript link found for row", row)
            continue
        
        # Increment counter when link is found
        #print(f"Found transcript link for row {row} (Total links found: {rows_with_links})")
        # Skip if the row contains other rows as children. This is because the parent obj is also a row.
        child_rows = row.find_all('div', class_='row')
        if len(child_rows) > 1:
            print("Child rows found")
            print(row)
            continue
        #print(row)
        rows_with_links += 1

            
        # Rest of your existing code for processing valid rows
        transcript_link = link_element['href']
        if not transcript_link.startswith('http'):
            print(f"Transcript link does not start with http: {transcript_link}. Should've never happened." )
            transcript_link = f"https://otvoreniparlament.rs{transcript_link}"
        
        # Extract title from h4
        title = link_element.find('h4').text.strip()
        
        # Extract date and convert to ddmmyyyyformat
        date_div = row.find('div', class_='col-xs-4 text-right')
        if date_div:
            date_str = date_div.text.strip()
            date_parts = date_str.rstrip('.').split('.')
            date = ''.join(date_parts)
        else:
            print(f"No date found for transcript {transcript_link}. Should've never happened.")
            date = ''
            
        transcript_data.append({
            'transcript_id': f"serbia_{convocation}_{current_numbering}_{date}",
            'processed_transcript_text_link': transcript_link,
            'title': title,
        })
        current_numbering += 1
    
        print(f"Found {rows_with_links} transcript links for convocation {convocation}")
    time.sleep(random.uniform(2, 5))
    return transcript_data, current_numbering


def main():
    data = scrape_transcripts()
    
    # Save to CSV
    with open("serbia_transcript_links.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, ["transcript_id", "processed_transcript_text_link", "title"])
        writer.writeheader()
        writer.writerows(data)

if __name__ == "__main__":
    main()
