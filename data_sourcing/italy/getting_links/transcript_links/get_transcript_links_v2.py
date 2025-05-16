from playwright.sync_api import sync_playwright
import pandas as pd
from datetime import datetime
import re
import os
from typing import Dict, List, Optional, Tuple
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class SenateScraper:
    def __init__(self):
        self.base_url = "https://www.senato.it/static/bgt/listaresaula"
        self.legislation_periods = {
            15: (2006, 2008),
            16: (2008, 2013),
            17: (2013, 2018),
            18: (2018, 2024),
            19: (2022, 2024)
        }
        
    def get_url_for_year(self, legislation: int, year: Optional[int] = None) -> str:
        """Generate URL for specific legislation and year."""
        if year:
            return f"{self.base_url}/{legislation}/{year}/index.html?static=true"
        return f"{self.base_url}/{legislation}/index.html?null"

    def extract_links_modern_format(self, table) -> List[Dict]:
        """Extract links from modern format (18th and 19th legislation)."""
        results = []
        current_month = None
        
        for row in table.query_selector_all("tr"):
            # Check if it's a month separator
            month_cell = row.query_selector("td.tabSep")
            if month_cell:
                current_month = month_cell.inner_text().strip()
                continue
                
            cells = row.query_selector_all("td")
            if len(cells) != 4:
                continue
                
            date_text = cells[0].inner_text().strip()
            sitting_number = cells[1].inner_text().strip()
            
            html_link = cells[2].query_selector("a")
            pdf_link = cells[3].query_selector("a")
            
            if html_link and pdf_link:
                results.append({
                    'date': date_text,
                    'sitting_number': sitting_number,
                    'html_link': html_link.get_attribute('href'),
                    'pdf_link': pdf_link.get_attribute('href'),
                    'month': current_month
                })
        
        return results

    def extract_session_number(self, element) -> Optional[str]:
        """Extract session number from link title or text."""
        # First try to get it from the title attribute
        title = element.get_attribute('title')
        if title:
            match = re.search(r'Seduta n\. (\d+)', title)
            if match:
                return match.group(1)
        
        # If not found in title, try the link text
        text = element.inner_text().strip()
        match = re.search(r'Seduta n\. (\d+)', text)
        if match:
            return match.group(1)
            
        return None

    def extract_links_old_format(self, table) -> List[Dict]:
        """Extract links from old format (15th-17th legislation)."""
        results = []
        current_month = None
        
        for row in table.query_selector_all("tr"):
            # Check if it's a month separator
            month_cell = row.query_selector("td.tabSep")
            if month_cell:
                current_month = month_cell.inner_text().strip()
                continue
                
            cells = row.query_selector_all("td")
            if len(cells) != 4:
                continue
                
            date_text = cells[0].inner_text().strip()
            
            # Check each column (morning, afternoon, night) for links
            for cell in cells[1:]:
                html_link = cell.query_selector("a[href*='showdoc']")
                if not html_link:
                    continue
                    
                sitting_number = self.extract_session_number(html_link)
                pdf_link = cell.query_selector("a[href*='PDF']")
                
                if html_link and pdf_link:
                    results.append({
                        'date': date_text,
                        'sitting_number': sitting_number,
                        'html_link': html_link.get_attribute('href'),
                        'pdf_link': pdf_link.get_attribute('href'),
                        'month': current_month
                    })
        
        return results

    def scrape_legislation_period(self, legislation: int):
        """Scrape all sessions for a specific legislation period."""
        start_year, end_year = self.legislation_periods[legislation]
        all_results = []
        
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            
            for year in range(start_year, end_year + 1):
                url = self.get_url_for_year(legislation, year)
                logging.info(f"Scraping {url}")
                
                try:
                    page.goto(url)
                    table = page.query_selector("table")
                    
                    if not table:
                        logging.warning(f"No table found for {url}")
                        continue
                    
                    # Determine which format to use based on legislation
                    if legislation >= 18:
                        results = self.extract_links_modern_format(table)
                    else:
                        results = self.extract_links_old_format(table)
                    
                    for result in results:
                        result['legislation'] = legislation
                        result['year'] = year
                    
                    all_results.extend(results)
                    
                except Exception as e:
                    logging.error(f"Error scraping {url}: {str(e)}")
            
            browser.close()
        
        return all_results

    def save_results(self, results: List[Dict], output_dir: str):
        """Save results to CSV file."""
        if not results:
            logging.warning("No results to save")
            return
            
        os.makedirs(output_dir, exist_ok=True)
        df = pd.DataFrame(results)
        
        # Save one file per legislation period
        for legislation in df['legislation'].unique():
            legislation_df = df[df['legislation'] == legislation]
            output_file = os.path.join(output_dir, f'transcripts_legislation_{legislation}.csv')
            legislation_df.to_csv(output_file, index=False)
            logging.info(f"Saved results for legislation {legislation} to {output_file}")

def main():
    scraper = SenateScraper()
    output_dir = "transcript_links_v2"
    
    # Only scrape legislations 15-17 as requested
    for legislation in [15, 16, 17]:
        logging.info(f"Starting scraping for legislation {legislation}")
        results = scraper.scrape_legislation_period(legislation)
        scraper.save_results(results, output_dir)
        logging.info(f"Completed scraping for legislation {legislation}")

if __name__ == "__main__":
    main() 