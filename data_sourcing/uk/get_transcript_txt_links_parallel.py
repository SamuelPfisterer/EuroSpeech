import pandas as pd
import random
import time
import logging
from typing import List, Dict
from botasaurus.browser import browser, Driver
from botasaurus.soupify import soupify
from urllib.parse import urljoin
import multiprocessing
from concurrent.futures import ProcessPoolExecutor

# Configure logging
logging.basicConfig(
    filename='scraping-parliaments-internally/uk/transcript_txt_links_parallel_log.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Define the function to extract TXT file link from a transcript page
@browser(reuse_driver=True, headless=True)
def extract_txt_link(driver: Driver, url: str) -> str:
    """
    Extracts the TXT file download link from a given transcript URL.

    Args:
        driver: The Botasaurus WebDriver instance.
        url: The URL of the transcript page to extract the TXT link from.

    Returns:
        The absolute URL of the TXT file if found, None if not found.
    """
    try:
        driver.get(url)
        time.sleep(random.uniform(2, 3))  # Reduced sleep time for parallel processing
        soup = soupify(driver)  # Use Botasaurus's soupify to get BeautifulSoup object

        # Find the TXT download link element
        element = soup.select_one('div.col-md-6:nth-child(1) > a:nth-child(1)')
        if element and "href" in element.attrs:
            relative_url = element.get("href")
            absolute_url = urljoin(url, relative_url)
            logging.info(f"Process {multiprocessing.current_process().name} found txt file: {absolute_url}")
            return absolute_url
        else:
            logging.warning(f"Process {multiprocessing.current_process().name} did not find TXT link on {url}")
            return None

    except Exception as e:
        logging.error(f"Process {multiprocessing.current_process().name} error extracting TXT link from {url}: {e}")
        return None  # Return None on error to indicate failure

def process_url(row: dict) -> dict:
    url = row['location_link']
    try:
        txt_link = extract_txt_link(url)
        row['txt_link'] = txt_link if txt_link else url
    except Exception as e:
        logging.error(f"Error processing URL {url}: {e}")
        row['txt_link'] = url
    return row


def parallel_process_csv(file_path: str) -> pd.DataFrame:
    """
    Reads a CSV file and parallelly processes the 'location_link' column
    to extract TXT file links.

    Args:
        file_path: The path to the CSV file.

    Returns:
        The modified pandas DataFrame with the 'txt_link' column.
        Returns an empty DataFrame on file reading error.
    """
    try:
        df = pd.read_csv(file_path)
    except FileNotFoundError:
        logging.error(f"File not found at {file_path}")
        return pd.DataFrame()
    except Exception as e:
        logging.error(f"Error reading CSV file: {e}")
        return pd.DataFrame()

    if 'location_link' not in df.columns:
        logging.error("'location_link' column not found in the CSV file.")
        return df

    # Initialize the 'txt_link' column with the original 'location_link' values
    df['txt_link'] = df['location_link']

    num_cores = 4
    logging.info(f"Using {num_cores} cores for processing.")

    with ProcessPoolExecutor(max_workers=num_cores) as executor:
        results = list(executor.map(process_url, df.to_dict(orient='records')))

    modified_df = pd.DataFrame(results)

    return modified_df

if __name__ == "__main__":
    # Specify the path to your CSV file
    csv_file_path = 'scraping-parliaments-internally/uk/transcript_links_temp_2012-2025.csv'  # Replace with your actual file path

    # Process the CSV file in parallel
    modified_df = parallel_process_csv(csv_file_path)

    # Check if the DataFrame is empty (indicating an error)
    if not modified_df.empty:
        # Log the first few rows of the modified DataFrame
        logging.info(f"First few rows of modified DataFrame:\n{modified_df.head()}")

        # Optionally, save the modified DataFrame to a new CSV file
        modified_df.to_csv('scraping-parliaments-internally/uk/transcript_links_parallel.csv', index=False)
        logging.info("Modified data saved to transcript_links_parallel.csv")
    else:
        logging.error("Error occurred during parallel processing. No output generated.")