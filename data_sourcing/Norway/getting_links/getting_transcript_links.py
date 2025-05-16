import requests
from bs4 import BeautifulSoup
import csv

BASE_URL = "https://www.stortinget.no"

def generate_year_urls(start_year=2010, end_year=2024):
    """Generate URLs for all years from start_year to end_year."""
    urls = []
    for year in range(start_year, end_year):
        session = f"{year}-{year+1}"
        url = f"{BASE_URL}/no/Saker-og-publikasjoner/Publikasjoner/Referater/Stortinget/{session}/?all=true"
        urls.append(url)
    return urls

def get_transcript_links_with_dates(year_url):
    """Extract transcript links and their dates from a given year URL."""
    response = requests.get(year_url)
    if response.status_code != 200:
        print(f"Failed to fetch {year_url}")
        return []
    
    soup = BeautifulSoup(response.text, "html.parser")
    transcript_data = []
    
    # Find the ul with class 'listing-simple' and extract all <a> tags inside it
    list_items = soup.find("ul", class_="listing-simple")
    if list_items:
        for li in list_items.find_all("li", class_="listitem"):
            a_tag = li.find("a")
            if a_tag and "href" in a_tag.attrs:
                # Extract the full URL
                relative_url = a_tag["href"]
                full_url = BASE_URL + relative_url
                
                # Extract the meeting date from the link text
                date_text = a_tag.get_text(strip=True)
                
                # Append to results
                transcript_data.append({
                    "date": date_text,
                    "link": full_url
                })
    
    return transcript_data

def main():
    # Step 1: Generate URLs for all years
    year_urls = generate_year_urls(2010, 2024)
    all_transcripts = []

    # Step 2: Fetch transcript links and dates for each year
    for year_url in year_urls:
        print(f"Processing year URL: {year_url}")
        transcript_data = get_transcript_links_with_dates(year_url)
        all_transcripts.extend(transcript_data)
    
    # Step 3: Save links and dates to a CSV file
    with open("transcript_links_with_dates.csv", "w", newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=["date", "link"])
        writer.writeheader()
        writer.writerows(all_transcripts)
    
    print(f"Extracted {len(all_transcripts)} transcript entries.")

if __name__ == "__main__":
    main()
