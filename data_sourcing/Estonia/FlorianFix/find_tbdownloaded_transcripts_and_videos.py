import pandas as pd

def filter_and_write_data(input_csv, estonia_links_csv, output_csv):
    """
    Filters data from an input CSV based on the absence of certain values in
    the estonia_links CSV and writes the filtered data to a new CSV.

    Args:
        input_csv (str): Path to the input CSV file (e.g., joined_transcript_youtube_data.csv).
        estonia_links_csv (str): Path to the estonia_links CSV file.
        output_csv (str): Path to the output CSV file.
    """
    try:
        # Read the input CSV
        df_input = pd.read_csv(input_csv)

        # Read the estonia_links CSV
        df_estonia = pd.read_csv(estonia_links_csv)

        # Get the transcript_link and youtube_link from estonia_links.csv
        estonia_transcript_links = set(df_estonia['transcript_link'])
        estonia_youtube_links = set(df_estonia['youtube_link'].dropna())  # Drop NaN to avoid errors

        # Filter the input DataFrame
        df_filtered = df_input[
            (~df_input['transcript_link'].isin(estonia_transcript_links)) &
            (~df_input['youtube_link'].isin(estonia_youtube_links))
        ]

        # Write the filtered DataFrame to a new CSV file
        df_filtered.to_csv(output_csv, index=False)

        print(f"Filtered data written to {output_csv}")

    except FileNotFoundError:
        print(f"Error: One or both of the CSV files ({input_csv}, {estonia_links_csv}) were not found.")
    except KeyError as e:
        print(f"Error: Column '{e}' not found in one of the CSV files.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    input_csv_path = "scraping-parliaments-internally/Estonia/FlorianFix/estonia_urls_complete_inner_join.csv"  # Replace with your actual input CSV path
    estonia_links_csv_path = "scraping-parliaments-internally/Estonia/FlorianFix/estonia_links.csv"        # Replace with your actual estonia_links CSV path
    output_csv_path = "scraping-parliaments-internally/Estonia/FlorianFix/estonia_urls_complete_inner_join_filtered.csv.csv"             # Replace with your desired output CSV path

    filter_and_write_data(input_csv_path, estonia_links_csv_path, output_csv_path)
