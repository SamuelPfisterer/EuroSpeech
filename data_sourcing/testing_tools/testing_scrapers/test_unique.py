import pandas as pd
import sys
from pathlib import Path

def find_duplicates(input_csv: str, output_csv: str, column: str) -> None:
    """
    Find and save duplicate rows based on a specified column in a CSV file.
    
    Args:
        input_csv: Path to the input CSV file
        output_csv: Path to save the duplicate rows CSV
        column: Column name to check for duplicates
    """
    try:
        # Load the CSV file
        df = pd.read_csv(input_csv)
        
        # Check if the specified column exists
        if column not in df.columns:
            print(f"Error: Column '{column}' not found in the CSV file.")
            return
            
        # Identify duplicate values in the specified column
        duplicate_mask = df.duplicated(subset=[column], keep=False)
        
        # Filter the DataFrame to show only the duplicate rows
        duplicate_rows = df[duplicate_mask]
        
        if duplicate_rows.empty:
            print(f"No duplicates found in column '{column}'")
            return
            
        # Print the duplicate rows
        print(f"Rows with duplicate '{column}' values:")
        print(duplicate_rows)
        
        # Save the duplicate rows to a new CSV file
        duplicate_rows.to_csv(output_csv, index=False)
        print(f"Duplicate rows saved to '{output_csv}'")
        
    except FileNotFoundError:
        print(f"Error: The file '{input_csv}' was not found.")
    except Exception as e:
        print(f"An error occurred: {str(e)}")

def main():
    # Hardcoded paths and column name
    input_csv = Path('../scraping-parliaments-internally/lithuania/lithuania_urls.csv')
    output_csv = Path('../scraping-parliaments-internally/lithuania/lithuania_duplicates.csv')
    column_to_check = 'merged_id'
    
    # Run the duplicate check
    find_duplicates(input_csv, output_csv, column_to_check)

if __name__ == "__main__":
    main()