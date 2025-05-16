# Estonia Parliament Transcript and Video Scraping

This repository contains scripts to scrape, merge, and filter Estonian parliament transcripts and YouTube videos. The process involves three main scripts:

1. **`getting_transcripts.py`**: Extracts transcript links from the Estonian parliament website.
2. **`merge_csv.py`**: Merges transcript links with YouTube video data based on the date.
3. **`find_tbdownloaded_transcripts_and_videos.py`**: Filters out already downloaded transcripts and videos.

## Overview of the Process

### 1. Extracting Transcripts (`getting_transcripts.py`)
- **Input**: None (scrapes directly from the Estonian parliament website).
- **Output**: `transcript_links_with_dates.csv` containing transcript links and their corresponding dates.
- **Details**:
  - The script scrapes transcript links from the Estonian parliament website for a given range of years (2014 to 2025).
  - The `transcript_link` column contains relative URLs, which serve as unique identifiers for transcripts.
  - The `date` column is extracted from the transcript link and formatted as `YYYY-MM-DD HH:MM:SS`.

### 2. Merging Transcripts and Videos (`merge_csv.py`)
- **Input**:
  - `transcript_links_with_dates.csv`: Contains transcript links and dates.
  - `youtube_playlist.csv`: Contains YouTube video links and dates (in the `date_from_title` column).
- **Output**: `estonia_urls_complete_inner_join.csv` containing merged data of transcripts and videos.
- **Details**:
  - The script performs an inner join on the `date` column from `transcript_links_with_dates.csv` and the `date_from_title` column from `youtube_playlist.csv`.
  - It handles invalid dates and provides statistics on matched and unmatched entries.

### 3. Filtering Already Downloaded Data (`find_tbdownloaded_transcripts_and_videos.py`)
- **Input**:
  - `estonia_urls_complete_inner_join.csv`: Contains merged transcript and video data.
  - `estonia_links.csv`: Contains rows for which transcripts and videos have already been downloaded.
- **Output**: `estonia_urls_complete_inner_join_filtered.csv` containing filtered data.
- **Details**:
  - The script filters out rows from `estonia_urls_complete_inner_join.csv` where either the `transcript_link` or `youtube_link` is already present in `estonia_links.csv`.
  - The resulting CSV contains over 1000 unique videos and transcripts that have not been downloaded yet.

## File Descriptions

- **`transcript_links_with_dates.csv`**: Contains transcript links and their dates.
- **`youtube_playlist.csv`**: Contains YouTube video links and their dates.
- **`estonia_urls_complete_inner_join.csv`**: Contains merged transcript and video data.
- **`estonia_links.csv`**: Contains already downloaded transcript and video links.
- **`estonia_urls_complete_inner_join_filtered.csv`**: Contains filtered transcript and video data for download.

## Usage

1. Run `getting_transcripts.py` to extract transcript links.
2. Run `merge_csv.py` to merge transcript and video data.
3. Run `find_tbdownloaded_transcripts_and_videos.py` to filter out already downloaded data.

## Notes
- The `transcript_link` and `youtube_link` serve as unique identifiers throughout the process.
- The `date` column is crucial for matching transcripts and videos.
