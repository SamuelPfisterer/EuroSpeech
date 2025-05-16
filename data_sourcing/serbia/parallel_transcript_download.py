from transcript_processors import process_transcript_text_link
import multiprocessing
import time
import csv
from tqdm import tqdm
import logging  # Import the logging module
import json
import os
import signal
import sys
import random
# Configure logging (do this at the beginning of your script)
logging.basicConfig(filename='error.log', level=logging.ERROR,
                    format='%(asctime)s - %(levelname)s - %(processName)s - %(message)s')

def signal_handler(sig, frame):
    print('Ctrl+C pressed. Terminating processes...')
    global pool  # Make sure pool is accessible if defined in main
    if 'pool' in globals() and pool is not None:
        pool.terminate()
        pool.join()
    sys.exit(0)

def process_url_wrapper(item):
    """
    Wrapper function to call process_transcript_text_link with the URL
    and save the result to a .txt file, returning a dictionary status.
    """
    url, output_filename = item
    result_dict = {'url': url, 'output_filename': output_filename, 'process': multiprocessing.current_process().name}
    try:
        # Wait a random time before starting a new process Then get transcript content
        time.sleep(random.uniform(2, 5))
        # Important! Do not call assign url=url when calling process_transcript_text_link.
        # It will cause the function to receive None for its url parameter.
        transcript_content = process_transcript_text_link(url)

        #write .txt file
        with open(output_filename, 'w', encoding='utf-8') as f:
            f.write(transcript_content)
        print(f"Saved transcript for {url} to {output_filename} in process {multiprocessing.current_process().name}")
        
        # Create return dict
        result_dict['status'] = 'success'
        return result_dict
    except Exception as e:
        # Log the error to the error.log file
        logging.error(f"Error processing URL: {url}. Exception: {e}")
        
        # Create return dict
        result_dict['status'] = 'error'
        result_dict['error_message'] = str(e)
        return result_dict


def main():
    signal.signal(signal.SIGINT, signal_handler) # Used to handle Ctrl+C. Otherwise it wont react to it
    # Read URLs and transcript IDs from CSV file
    csv_path = "scraping-parliaments-internally/serbia/serbia_transcript_links.csv"
    error_csv_path = "scraping-parliaments-internally/serbia/empty_erronous_transcripts.csv"
    output_dir = "scraping-parliaments-internally/serbia/transcripts"
    os.makedirs(output_dir, exist_ok=True)
    # Used for logging results
    results_file = "scraping-parliaments-internally/serbia/transcript_processing_results.json"

    # First read the error transcript IDs Only needed for second pass
    error_transcript_ids = set()
    with open(error_csv_path, 'r', encoding='utf-8') as error_csv:
        error_reader = csv.DictReader(error_csv)
        for row in error_reader:
            error_transcript_ids.add(row['transcript_id'])

    url_outfile_pairs = []
    seen_transcript_ids = set()
    
    # Go through csv and add url and transcript id to list if we haven't seen this transcript_id before
    # and it's in the error transcript list
    with open(csv_path, 'r', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            transcript_id = row['transcript_id']
            url = row['processed_transcript_text_link']
            
            # Only add if we haven't seen this transcript_id before and it's in error list.
            # The boolean after the "and" is only needed for the second pass.
            if transcript_id not in seen_transcript_ids and transcript_id in error_transcript_ids:
                url_outfile_pairs.append((url, f"{output_dir}/{transcript_id}.txt"))
                seen_transcript_ids.add(transcript_id)
    
    num_processes = multiprocessing.cpu_count()
    print(f"Using {num_processes} processes")
    start_time = time.time()

    # The actual multiprocessing execution happens here
    with multiprocessing.Pool(processes=1) as pool:
        # Pass the list of tuples to the pool.imap function
        results = list(tqdm(pool.imap(process_url_wrapper, url_outfile_pairs), total=len(url_outfile_pairs), desc="Processing transcripts"))

    end_time = time.time()

    print("\n--- Processing Complete ---")
    print(f"Total time taken: {end_time - start_time:.2f} seconds")
    print(f"Processed {len(results)} URLs")

    # Count and report errors
    error_count = sum(1 for result in results if result['status'] == 'error')
    print(f"Number of errors: {error_count}")
    
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=4)
    print(f"Results saved to {results_file}")

if __name__ == "__main__":
    main()