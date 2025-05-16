import csv
import os

def filter_links(m3u8_file, downloaded_file, output_file):
    """
    Filters rows from m3u8_file based on timestamps in downloaded_file.

    Reads timestamps from downloaded_file. Reads m3u8_file row by row.
    Writes rows to output_file if their 'm3u8_link' column does not
    contain any of the timestamps from downloaded_file.

    Args:
        m3u8_file (str): Path to the input CSV file with m3u8 links.
        downloaded_file (str): Path to the file containing downloaded timestamps (one per line).
        output_file (str): Path to the output filtered CSV file.
    """
    try:
        with open(downloaded_file, 'r', encoding='utf-8') as f_downloaded:
            # Read timestamps, remove quotes and whitespace
            downloaded_timestamps = {line.strip().replace('"', '') for line in f_downloaded if line.strip()}
        print(f"Read {len(downloaded_timestamps)} timestamps from {downloaded_file}")

    except FileNotFoundError:
        print(f"Error: Downloaded timestamps file not found at {downloaded_file}")
        return
    except Exception as e:
        print(f"Error reading {downloaded_file}: {e}")
        return

    try:
        with open(m3u8_file, 'r', encoding='utf-8') as f_in, \
             open(output_file, 'w', newline='', encoding='utf-8') as f_out:

            reader = csv.DictReader(f_in)
            if reader.fieldnames is None:
                print(f"Error: Could not read header from {m3u8_file}")
                return

            writer = csv.DictWriter(f_out, fieldnames=reader.fieldnames)
            writer.writeheader()

            filtered_count = 0
            total_count = 0
            for row in reader:
                total_count += 1
                m3u8_link = row.get('m3u8_link', '')
                # Check if any downloaded timestamp is a substring of the m3u8_link
                if not any(timestamp in m3u8_link for timestamp in downloaded_timestamps):
                    writer.writerow(row)
                    filtered_count += 1

        print(f"Processed {total_count} rows from {m3u8_file}.")
        print(f"Wrote {filtered_count} filtered rows to {output_file}.")

    except FileNotFoundError:
        print(f"Error: Input m3u8 file not found at {m3u8_file}")
    except KeyError as e:
        print(f"Error: Missing expected column in {m3u8_file}: {e}")
    except Exception as e:
        print(f"An error occurred during processing: {e}")

if __name__ == "__main__":
    # Define file paths relative to the script location or use absolute paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    m3u8_links_csv = os.path.join(script_dir, 'iceland_m3u8_links_with_ids.csv')
    downloaded_opus_csv = os.path.join(script_dir, 'downloaded_opus_files.csv')
    filtered_output_csv = os.path.join(script_dir, 'final_iceland_links_to_process.csv')

    filter_links(m3u8_links_csv, downloaded_opus_csv, filtered_output_csv)
