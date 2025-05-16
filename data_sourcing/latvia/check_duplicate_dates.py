import pandas as pd
from collections import Counter

# Read the CSV file with headers
df = pd.read_csv('transcript_links.csv')

# Convert the Date column to datetime
df['Date'] = pd.to_datetime(df['Date'])

# Find duplicate dates
date_counts = Counter(df['Date'])
duplicates = {date: count for date, count in date_counts.items() if count > 1}

if duplicates:
    # Count how many dates have each number of occurrences
    occurrence_counts = Counter(duplicates.values())
    
    print("\n=== SUMMARY OF DUPLICATE DATES ===")
    print(f"Total number of unique dates with duplicates: {len(duplicates)}")
    total_duplicate_entries = sum(count * num_occurrences for num_occurrences, count in occurrence_counts.items())
    print(f"Total number of entries involved in duplicates: {total_duplicate_entries}")
    
    print("\nBreakdown of duplicates:")
    for num_occurrences in sorted(occurrence_counts.keys()):
        dates_with_count = len([date for date, count in duplicates.items() if count == num_occurrences])
        print(f"Dates appearing {num_occurrences} times: {dates_with_count}")
    
    print("\nWould you like to see the detailed listing? (y/n)")
else:
    print("No duplicate dates found in the transcript links.") 