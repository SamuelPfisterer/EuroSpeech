import pandas as pd
import random
import time
from typing import List, Dict
from botasaurus.browser import browser, Driver
from botasaurus.soupify import soupify
from urllib.parse import urljoin
from tqdm import tqdm

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
        time.sleep(random.uniform(4, 5))  # Simulate human-like behavior
        soup = soupify(driver)  # Use Botasaurus's soupify to get BeautifulSoup object

        # Find the TXT download link element
        element = soup.select_one('div.col-md-6:nth-child(1) > a:nth-child(1)')
        relative_url = element.get("href")
        absolute_url = urljoin(url, relative_url)
        print("Found txt file: " + absolute_url)
        return absolute_url

    except Exception as e:
        print(f"Error extracting TXT link from {url}: {e}")
        return None  # Return None on error to indicate failure

def process_csv_and_update_links(file_path: str) -> pd.DataFrame:
    """
    Reads a CSV file, processes the 'location_link' column, replaces URLs with random numbers,
    and renames the column to 'txt_link'.  Handles potential errors during file processing.

    Args:
        file_path: The path to the CSV file.

    Returns:
        The modified pandas DataFrame.  Returns an empty DataFrame on error.
    """
    try:
        # Read the CSV file into a pandas DataFrame
        df = pd.read_csv(file_path)
    except FileNotFoundError:
        print(f"Error: File not found at {file_path}")
        return pd.DataFrame()  # Return an empty DataFrame
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        return pd.DataFrame()

    # Check if the 'location_link' column exists
    if 'location_link' not in df.columns:
        print("Error: 'location_link' column not found in the CSV file.")
        return df  # Return the original DataFrame without changes

    # Process each row in the DataFrame
    for index, row in tqdm(df.iterrows(), total=len(df), desc="Processing transcript links"):
        url = row['location_link']
        try:
            # Call the function to extract data (and handle potential errors)
            txt_link = extract_txt_link(url)
            if txt_link: # only replace if extraction was successful
               df.at[index, 'location_link'] = txt_link
            else:
                print(f"Failed to extract transcript from {url}.  Keeping original link.")

        except Exception as e:
            print(f"Error processing URL {url}: {e}")
            print(f"Keeping original link for row {index}.")  # Keep the original URL

    # Rename the column
    df = df.rename(columns={'location_link': 'txt_link'})
    return df

if __name__ == "__main__":
    # Specify the path to your CSV file
    csv_file_path = 'scraping-parliaments-internally/uk/transcript_links_temp.csv'  # Replace with your actual file path

    # Process the CSV file and get the modified DataFrame
    modified_df = process_csv_and_update_links(csv_file_path)

    # Check if the DataFrame is empty (indicating an error)
    if not modified_df.empty:
        # Print the first few rows of the modified DataFrame
        print(modified_df.head())

        # Optionally, save the modified DataFrame to a new CSV file
        modified_df.to_csv('scraping-parliaments-internally/uk/transcript_links.csv', index=False)
        print("Modified data saved to modified_file.csv")
    else:
        print("Error occurred during processing. No output generated.")
