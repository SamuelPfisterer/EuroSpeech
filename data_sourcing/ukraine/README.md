# Ukrainian Parliament Session Videos Dataset

This repository contains tools and datasets for collecting and processing videos from the Ukrainian Parliament (Verkhovna Rada) YouTube channel.

## Project Overview

This project aims to create a comprehensive dataset of Ukrainian Parliament session videos by:
1. Collecting video metadata from the official YouTube channel
2. Processing and cleaning the data
3. Extracting and standardizing session dates
4. Creating filtered datasets for analysis

## Files Description

- `get_youtube_videos.py`: Python script that uses yt-dlp to fetch video metadata from the Ukrainian Parliament's YouTube playlist
- `filter_videos.ipynb`: Jupyter notebook for processing and filtering the video dataset
- `ukraine_parliament_session_videos.csv`: Raw dataset containing all video metadata
- `ukraine_parliament_videos_with_dates.csv`: Cleaned dataset containing only videos with valid dates
- `ukraine_parliament_videos.csv`: Complete dataset with additional metadata (4.9MB)

## CSV File Specifications

### ukraine_parliament_videos.csv (4.9MB)
Complete dataset containing:
- All video metadata from the YouTube playlist
- Additional metadata and information
- Raw, unprocessed data in its original form
- Largest of the three datasets at 4.9MB
- Used as initial data collection

### ukraine_parliament_session_videos.csv (107KB)
Raw dataset created by `get_youtube_videos.py` containing:
- `title`: Video title in Ukrainian (string)
- `video_id`: Unique YouTube video identifier (string)
- `url`: Complete YouTube video URL (string)
- `upload_date`: Original upload date from YouTube (string, may be 'N/A')
- `duration`: Video length in seconds (float)
- Constraints:
  - No filtering applied
  - Contains all videos from the playlist
  - May include private or deleted videos
  - Total rows: 703

### ukraine_parliament_videos_with_dates.csv (110KB)
Processed dataset created by `filter_videos.ipynb` containing:
- `title`: Video title in Ukrainian (string)
- `video_id`: Unique YouTube video identifier (string)
- `url`: Complete YouTube video URL (string)
- `upload_date`: Original upload date from YouTube (string)
- `duration`: Video length in seconds (float)
- `date`: Extracted and standardized session date (datetime)
- Constraints:
  - Only includes videos where a date could be extracted from the title
  - Dates are standardized to YYYY-MM-DD format
  - Sorted by date in descending order
  - No private or invalid videos
  - Total rows: 685
- Note on Dates:
  - Multiple videos can exist for the same date
  - This is because the parliament often has:
    - Morning sessions (Ранкове засідання)
    - Evening sessions (Вечірнє засідання)
    - Multi-part videos (e.g., "ч.1", "ч.2" for parts 1, 2)
  - Distribution of videos per date:
    - Total unique dates: 499
    - Single video dates: 347 (69.5% of dates)
    - Two videos: 133 dates
    - Three videos: 7 dates
    - Four videos: 10 dates
    - Five videos: 1 date
    - Six videos: 1 date

## Data Collection

The data is collected from the official Ukrainian Parliament YouTube playlist using the `yt-dlp` library. For each video, we collect:
- Title
- Video ID
- URL
- Upload date
- Duration

## Data Processing

The data processing pipeline includes:
1. Extracting dates from video titles
2. Filtering out videos without dates
3. Converting dates to a standardized format
4. Sorting videos by date

## Dataset Statistics

- Total videos collected: 703
- Videos with valid dates: 685
- Date range: January 17, 2017 to present
- Video types: Primarily plenary sessions, with some special sessions and government question hours

## Requirements

- Python 3.9+
- pandas
- yt-dlp

## Usage

1. To collect new video data:
```bash
python get_youtube_videos.py
```

2. To process and filter the videos, run the Jupyter notebook:
```bash
jupyter notebook filter_videos.ipynb
``` 