import os
import csv
from tqdm import tqdm
from botasaurus.browser import browser, Driver
import time
import transcript_processors
from multiprocessing import Pool, cpu_count

def check_num_speakers(expected_speakers: int, transcript: str) -> tuple:
    """
    Check if the number of speakers in the transcript matches the expected amount.
    Speakers are identified by markdown bold syntax (**speaker_name**).

    Args:
        expected_speakers (int): The expected number of speakers
        transcript (str): The transcript text to analyze

    Returns:
        tuple: (bool, int) - (whether counts match, actual speaker count)
    """
    # Count occurrences of the markdown bold syntax
    speaker_count = transcript.count('**')
    # Each speaker has two ** markers (start and end)
    actual_speakers = speaker_count // 2
    return actual_speakers == expected_speakers, actual_speakers

@browser(reuse_driver=False, headless=False)
def process_last_page(driver: Driver, url: str) -> int:
    """
    Process the last page of the transcript to get the total number of speakers.

    Args:
        driver (Driver): The botasaurus browser driver
        url (str): The URL of the transcript

    Returns:
        int: Total number of speakers
    """
    # Get total number of pages
    driver.get(url)
    time.sleep(10)
    soup = transcript_processors.soupify(driver)
    total_pages = transcript_processors.get_total_pages(soup)

    # Go to last page
    last_page_url = f"{url}?page={total_pages}"
    driver.get(last_page_url)
    time.sleep(10)

    # Extract content from last page
    soup = transcript_processors.soupify(driver)
    transcript_rows = soup.find_all('div', class_='media-body js-eq-button-append speech-vertical-align-top')

    return len(transcript_rows) + 10 * (total_pages - 1)

def check_transcript_quality(filepath: str) -> tuple:
    """
    Check the quality of a transcript file by verifying the number of speakers.

    Args:
        filepath (str): Path to the transcript file

    Returns:
        tuple: (transcript_id, expected_speakers, actual_speakers) if error found,
               ("", 0, 0) if file is valid
    """
    # Get transcript_id from filename
    transcript_id = os.path.basename(filepath).replace('.txt', '')

    # Read CSV to find the corresponding transcript link
    with open('scraping-parliaments-internally/serbia/serbia_transcript_links.csv', 'r', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            if row['transcript_id'] == transcript_id:
                url = row['processed_transcript_text_link']
                break
        else:
            return transcript_id, 0, 0  # Return ID if not found in CSV

    try:
        # Get speaker count from last page
        expected_speakers = process_last_page(url)

        # Check if the file has the same number of speakers
        with open(filepath, 'r', encoding='utf-8') as f:
            file_content = f.read()
            correct, actual_speakers = check_num_speakers(expected_speakers=expected_speakers, transcript=file_content)
            if not correct:
                print(f"Mismatch in {filepath}: Expected {expected_speakers} speakers, found {actual_speakers}")
                return transcript_id, expected_speakers, actual_speakers

        return "", 0, 0
    except Exception as e:
        print(f"Error processing {transcript_id}: {e}")
        return transcript_id, 0, 0

def find_erroneous_files(directory: str, filetype: str) -> list:
    """
    Find all erroneous files of a given type in a directory, checking only files
    listed in empty_erronous_transcripts.csv.

    Args:
        directory (str): Path to the directory containing the files
        filetype (str): File extension to check (e.g., 'txt')

    Returns:
        list: List of tuples (transcript_id, expected_speakers, actual_speakers) with errors
    """
    if not os.path.exists(directory):
        print(f"Directory {directory} does not exist.")
        return []

    # Read transcript IDs from CSV
    try:
        with open('scraping-parliaments-internally/serbia/empty_erronous_transcripts.csv', 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            transcript_ids = [row['transcript_id'] for row in reader]
    except FileNotFoundError:
        print("empty_erronous_transcripts.csv not found.")
        return []

    # Get only files that match the transcript IDs
    files = [os.path.join(directory, f"{tid}.{filetype}") for tid in transcript_ids
             if os.path.exists(os.path.join(directory, f"{tid}.{filetype}"))]

    if not files:
        print(f"No matching .{filetype} files found in {directory}.")
        return []

    # Use multiprocessing to check files in parallel
    print(f"Starting multiprocessing with {2} cores...")
    with Pool(1) as pool:
        results = list(tqdm(pool.imap(check_transcript_quality, files), total=len(files)))

    # Filter out empty strings (valid files) and collect erroneous files
    erroneous_files = [result for result in results if result[0]]  # Check first element of tuple
    print(f"Found {len(erroneous_files)} erroneous files.")

    return erroneous_files

def save_erroneous_files_to_csv(erroneous_files: list, output_file: str) -> None:
    """
    Save the list of erroneous files to a CSV file.

    Args:
        erroneous_files (list): List of tuples (transcript_id, expected_speakers, actual_speakers) with errors
        output_file (str): Path to the output CSV file
    """
    if erroneous_files:
        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['transcript_id', 'expected_speakers', 'actual_speakers'])  # Write header
            for file_id, expected, actual in erroneous_files:
                writer.writerow([file_id, expected, actual])
                print(f"Transcript {file_id}: Expected {expected} speakers, found {actual} speakers")
        print(f"Saved list of erroneous files to {output_file}")

# Example usage
if __name__ == "__main__":
    directory_path = "scraping-parliaments-internally/serbia/transcripts"  # Replace with your directory path
    erroneous_files = find_erroneous_files(directory_path, "txt")
    #check_transcript_quality(os.path.join(directory_path, "serbia_2012_123_24122012.txt"))
    print(f"Found {len(erroneous_files)} erroneous .txt files.")
    save_erroneous_files_to_csv(erroneous_files, "scraping-parliaments-internally/serbia/empty_erronous_transcripts.csv")
