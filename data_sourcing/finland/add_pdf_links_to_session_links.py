import csv
import re
from typing import Optional, Tuple
from pathlib import Path

def extract_session_numbers(session_url: str) -> Optional[Tuple[str, str]]:
    """
    Extract session number and year from a session URL.
    
    Args:
        session_url: URL of the format https://verkkolahetys.eduskunta.fi/fi/taysistunnot/taysistunto-127-2020
        
    Returns:
        Tuple of (session_number, year) or None if pattern doesn't match
    """
    try:
        # Extract the last part of the URL (e.g., "taysistunto-127-2020")
        parts = session_url.strip('/').split('/')[-1]
        # Extract numbers using regex
        match = re.search(r'taysistunto-(\d+)-(\d+)', parts)
        if match:
            session_num, year = match.groups()
            return session_num, year
    except Exception as e:
        print(f"Error extracting numbers from {session_url}: {e}")
    return None

def construct_pdf_link(session_num: str, year: str) -> str:
    """
    Construct the PDF link from session number and year.
    
    Args:
        session_num: Session number (e.g., "127")
        year: Year (e.g., "2020")
        
    Returns:
        Full PDF URL
    """
    return f"https://www.eduskunta.fi/FI/vaski/Poytakirja/Documents/PTK_{session_num}+{year}.pdf"

def process_csv(input_path: str, output_path: str):
    """
    Process the input CSV and create a new one with PDF links.
    
    Args:
        input_path: Path to input CSV file
        output_path: Path to output CSV file
    """
    # Read input CSV
    rows = []
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames
            rows = list(reader)
        print(f"Read {len(rows)} rows from {input_path}")
    except Exception as e:
        print(f"Error reading input CSV: {e}")
        return

    if not rows:
        print("No rows found in input file")
        return

    # Add new column for PDF links
    new_fieldnames = list(fieldnames) + ['pdf_link']
    processed = 0
    skipped = 0

    # Process each row
    for row in rows:
        session_url = row.get('link', '')
        if not session_url:
            row['pdf_link'] = ''
            skipped += 1
            continue

        numbers = extract_session_numbers(session_url)
        if numbers:
            session_num, year = numbers
            row['pdf_link'] = construct_pdf_link(session_num, year)
            processed += 1
        else:
            row['pdf_link'] = ''
            skipped += 1

    # Write output CSV
    try:
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=new_fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        print(f"\nProcessed {processed} rows successfully")
        print(f"Skipped {skipped} rows")
        print(f"Output written to {output_path}")
    except Exception as e:
        print(f"Error writing output CSV: {e}")

if __name__ == "__main__":
    input_csv = "session_links.csv"
    output_csv = "session_links_with_pdf.csv"
    
    # Check if input file exists
    if not Path(input_csv).exists():
        print(f"Error: Input file {input_csv} not found")
    else:
        process_csv(input_csv, output_csv)
