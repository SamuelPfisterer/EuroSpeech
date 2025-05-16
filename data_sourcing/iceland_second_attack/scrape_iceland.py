import csv
from camoufox.sync_api import Camoufox
import pandas as pd


BASE_URL = "https://www.althingi.is"
OUTPUT_FILE = "iceland_links.csv"
PROXY = {
    'server': 'gate.decodo.com:7000',
    'username': 'sph4b47do7',
    'password': 'fsv5fKD+wvTzLwt628'
}

def scrape_period(page, ltg):
    """Scrapes data for a single legislative period."""
    url = f"{BASE_URL}/thingstorf/thingfundir-og-raedur/fundargerdir-og-upptokur/?ltg={ltg}"
    print(f"Scraping: {url}")
    try:
        page.goto(url, wait_until='domcontentloaded', timeout=60000)
    except Exception as e:
        print(f"Error navigating to {url}: {e}")
        return []

    rows_data = []
    # Locate the table rows within the tbody
    rows = page.query_selector_all("table tbody tr")
    if not rows:
        print(f"No table rows found for ltg={ltg}")
        return []

    for row in rows:
        # Find the cell containing the transcript link
        num_cell = row.query_selector("td.num a")
        if not num_cell:
            continue

        transcript_href = num_cell.get_attribute("href")
        transcript_url = f"{BASE_URL}{transcript_href}" if transcript_href else ""

        # Find the video link
        video_link_element = row.query_selector('td a:has-text("Horfa")')
        video_url = ""
        if video_link_element:
            video_href = video_link_element.get_attribute("href")
            video_url = f"{BASE_URL}{video_href}" if video_href else ""

        rows_data.append({
            "ltg": ltg,
            "transcript_url": transcript_url,
            "video_link": video_url
        })

    return rows_data

def main():
    all_data = []
    start_ltg = 141
    end_ltg = 156
    
    with Camoufox(
        geoip=True,
        proxy=PROXY,
        headless=False
    ) as browser:
        page = browser.new_page()

        for ltg in range(start_ltg, end_ltg + 1):
            period_data = scrape_period(page, ltg)
            all_data.extend(period_data)

        browser.close()

    if all_data:
        df = pd.DataFrame(all_data)
        df.to_csv(OUTPUT_FILE, index=False, quoting=csv.QUOTE_ALL)
        print(f"Data successfully scraped and saved to {OUTPUT_FILE}")
    else:
        print("No data was scraped.")

if __name__ == "__main__":
    try:
        import pandas
    except ImportError:
        print("Pandas not found. Please install it: pip install pandas")
    else:
        main() 