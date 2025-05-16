import pandas as pd

def inner_join_csvs_on_date(csv_path1, csv_path2, date_column1='date', date_column2='date_from_title'):
    """
    Performs an inner join of two CSV files based on the date, with enhanced error handling and reporting.

    Args:
        csv_path1 (str): Path to the first CSV file (transcript links with dates).
        csv_path2 (str): Path to the second CSV file (YouTube playlist data).
        date_column1 (str): Name of the date column in the first CSV.
        date_column2 (str): Name of the date column in the second CSV.

    Returns:
        pandas.DataFrame: The inner-joined DataFrame, or None if an error occurs.
    """
    try:
        # Read the CSV files
        df1 = pd.read_csv(csv_path1)
        df2 = pd.read_csv(csv_path2)

        # Initialize counters
        invalid_dates_df1 = []
        invalid_dates_df2 = []
        
        # Convert date columns with error handling
        def safe_date_conversion(df, col, invalid_dates):
            valid_dates = []
            for date_str in df[col]:
                try:
                    valid_dates.append(pd.to_datetime(date_str).date())
                except ValueError:
                    invalid_dates.append(date_str)
                    valid_dates.append(None)
            return valid_dates

        df1['parsed_date'] = safe_date_conversion(df1, date_column1, invalid_dates_df1)
        df2['parsed_date'] = safe_date_conversion(df2, date_column2, invalid_dates_df2)

        # Filter out rows with invalid dates
        valid_df1 = df1[df1['parsed_date'].notna()]
        valid_df2 = df2[df2['parsed_date'].notna()]

        # Perform inner join
        merged_df = pd.merge(valid_df1, valid_df2, left_on='parsed_date', right_on='parsed_date', how='inner')

        # Calculate statistics
        total_df1 = len(df1)
        total_df2 = len(df2)
        matched_count = len(merged_df)
        unmatched_df1 = total_df1 - matched_count - len(invalid_dates_df1)
        unmatched_df2 = total_df2 - matched_count - len(invalid_dates_df2)

        # Print statistics
        print("\nMatching Statistics:")
        print(f"Total transcript entries: {total_df1}")
        print(f"Total YouTube videos: {total_df2}")
        print(f"Successfully matched: {matched_count}")
        print(f"Unmatched transcript entries: {unmatched_df1}")
        print(f"Unmatched YouTube videos: {unmatched_df2}")
        print(f"Invalid dates in transcript entries: {len(invalid_dates_df1)}")
        print(f"Invalid dates in YouTube videos: {len(invalid_dates_df2)}")

        # Print examples of invalid dates if any
        if invalid_dates_df1:
            print("\nExamples of invalid dates in transcript entries:")
            print(invalid_dates_df1[:3])
        if invalid_dates_df2:
            print("\nExamples of invalid dates in YouTube videos:")
            print(invalid_dates_df2[:3])

        return merged_df

    except FileNotFoundError:
        print("Error: One or both of the specified CSV files were not found.")
        return None
    except KeyError as e:
        print(f"Error: Column '{e}' not found in one of the CSV files.")
        return None
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None

if __name__ == "__main__":
    transcript_csv_path = "scraping-parliaments-internally/Estonia/FlorianFix/transcript_links_with_dates.csv"
    youtube_csv_path = "scraping-parliaments-internally/Estonia/FlorianFix/youtube_playlist.csv"

    # Perform the inner join
    joined_df = inner_join_csvs_on_date(transcript_csv_path, youtube_csv_path)

    if joined_df is not None:
        # Save the joined DataFrame to a new CSV file
        output_csv_path = "scraping-parliaments-internally/Estonia/FlorianFix/estonia_urls_complete_inner_join.csv"
        joined_df.to_csv(output_csv_path, index=False)
        print(f"\nInner joined data has been saved to {output_csv_path}")
        print("\nFirst few rows of the joined data:")
        print(joined_df.head())