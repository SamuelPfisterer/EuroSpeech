from main import main
import pandas as pd
import argparse

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--start_idx", type=int, required=True)
    parser.add_argument("--end_idx", type=int, required=True)
    args = parser.parse_args()
    
    # Use failed_downloads.csv instead of original
    main(args.start_idx, args.end_idx, csv_file='failed_downloads.csv')