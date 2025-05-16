import csv
import re
import logging
from tqdm import tqdm
from typing import List, Dict
from bs4 import BeautifulSoup

"""
This script reads the saved HTML file containing transcript data from the Kosovo Parliament website,
processes each row to extract transcript metadata, generates unique transcript IDs, and saves the 
collected data to a CSV file.

The script uses BeautifulSoup for HTML parsing.
Each transcript entry contains a unique ID (format: kosovo_index_ddmmyyyy) and its download link.
"""

# Configure logging to write to a file in the same directory
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='scraping-parliaments-internally/kosovo/transcript_row_scraper.log',
    filemode='a'
)

# Map month names to numbers (assuming Albanian month names)
MONTH_MAP = {
    'Janar': '01', 'Shkurt': '02', 'Mars': '03', 'Prill': '04',
    'Maj': '05', 'Qershor': '06', 'Korrik': '07', 'Gusht': '08',
    'Shtator': '09', 'Tetor': '10', 'Nëntor': '11', 'Dhjetor': '12'
}

def extract_date(date_container, relative_link: str) -> str:
    """lv2 helper function that extracts and formats a date from a given date container element.
    Returns formatted date string in ddmmyyyy format."""
    day_span = date_container.find('span', class_='nr')
    month_time_span = date_container.find('span', class_='date-time')
    
    if not (day_span and month_time_span):
        return None
        
    day = day_span.text.strip().zfill(2)
    month_time = month_time_span.text.strip()
    month_name = month_time.split(' ')[0]
    month = MONTH_MAP.get(month_name)
    
    if not month:
        return None

    # Extract year from the link
    year_match = re.search(r'(\d{4})_', relative_link)
    if not year_match:
        return None
        
    year = year_match.group(1)
    return f"{day}{month}{year}"

def extract_transcript_data(html_file: str) -> List[Dict[str, str]]:
    """
    Function to extract transcript data from the saved HTML file.
    
    This function performs the following steps:
    1. Reads the saved HTML file
    2. Processes each row to extract transcript metadata
    3. Generates unique transcript IDs and collects download links
    
    Args:
        html_file: Path to the saved HTML file
    
    Returns:
        List[Dict[str, str]]: List of dictionaries containing transcript metadata
        Each dictionary has 'transcript_id' and 'transcript_link' keys
    """
    
    with open(html_file, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f, "html.parser")

    transcript_data = []

    logging.info("Finding all rows...")
    items = soup.find_all('div', class_='item')
    rows = []
    for item in items:
        row = item.find('div', class_='row', recursive=False)
        if row:
            rows.append(row)
    logging.info(f"Found {len(rows)} rows. Starting to process rows...")
    
    for i, row in tqdm(enumerate(rows), total=len(rows), desc="Processing rows"):
        date_container = row.find('div', class_='date-container')
        if not date_container:
            logging.warning("No date. Skipping this row.")
            continue

        transcript_link_tag = date_container.find('a', class_='file-icon', string='Transkript')

        if transcript_link_tag:
            relative_link = transcript_link_tag['href']
            absolute_link = "https://www.kuvendikosoves.org" + relative_link

            formatted_date = extract_date(date_container, relative_link)
            if formatted_date:
                transcript_data.append({
                    'transcript_id': f"kosovo_{i}_{formatted_date}",
                    'transcript_link': absolute_link
                })
                logging.info(transcript_data[-1])
        else:
            logging.warning(f"No transcript link found for row {i}.")

    return transcript_data

if __name__ == "__main__":
    html_file = "scraping-parliaments-internally/kosovo/loaded_transcript_page.html"

    transcript_data = extract_transcript_data(html_file)

    # Save transcript data to CSV
    with open("parliament_transcript_data.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, ["transcript_id", "transcript_link"])
        writer.writeheader()
        writer.writerows(transcript_data) 