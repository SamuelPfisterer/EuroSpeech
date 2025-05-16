import time
import logging
from botasaurus.browser import browser, Driver
from botasaurus.soupify import soupify

"""
This script navigates to the Kosovo Parliament website (www.kuvendikosoves.org),
clicks the "Show More" button until all sessions are loaded, and saves the loaded
HTML to a file for further processing.

The script uses Selenium with Botasaurus for web automation and BeautifulSoup for HTML parsing.
"""

# Configure logging to write to a file in the same directory
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='scraping-parliaments-internally/kosovo/transcript_page_scraper.log',
    filemode='w'
)

@browser(reuse_driver=False, headless=False)
def load_parliament_transcript_page(driver: Driver, url: str):
    """
    Function to load all transcript sessions on the Kosovo Parliament website.
    
    This function performs the following steps:
    1. Navigates to the provided URL
    2. Clicks "Show More" button until all sessions are loaded
    3. Saves the loaded HTML to a file
    
    Args:
        driver: Selenium WebDriver instance
        url: URL of the parliament sessions page
    """

    driver.get(url)
    
    time.sleep(10)
    soup = soupify(driver)
    # Load all rows by clicking the button
    while True:
        try:
            show_more_button = driver.select("#js-sessions-show-more")
            is_visible = show_more_button.run_js("""
                (el) => {
                    if (!el) return false;
                    const style = window.getComputedStyle(el);
                    const rect = el.getBoundingClientRect();
                    return (
                        style.display !== 'none' &&
                        style.visibility !== 'hidden' &&
                        style.opacity !== '0' &&
                        rect.width > 0 &&
                        rect.height > 0
                    );
                }
            """)
            if is_visible:
                show_more_button.click()
                logging.info("Clicked on 'TREGO MË SHUMË' button.")
                time.sleep(0.5)
            else:
                logging.info("The 'Load More' button is no longer visible. Proceeding to save HTML.")
                break
        except Exception as e:
            logging.error(f"An error occurred while trying to click 'Load More': {str(e)}")
            break

    # Extract and save HTML after loading all content
    time.sleep(5)
    page_html = str(soup.html)
    with open("scraping-parliaments-internally/kosovo/loaded_transcript_page.html", "w", encoding="utf-8") as f:
        f.write(page_html)
    logging.info("Saved full page HTML to loaded_transcript_page.html")

if __name__ == "__main__":
    url = "https://www.kuvendikosoves.org/shq/seancat/seancat/"
    load_parliament_transcript_page(url) 