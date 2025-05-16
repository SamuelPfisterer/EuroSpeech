# Local Download Testing Guide

This guide explains how to test the download pipeline locally without Supabase integration.

## Prerequisites

1. Python 3.6 or higher
2. Required Python packages:
   - pandas
   - tqdm
   - requests
   - playwright
   - yt-dlp (for YouTube downloads)
   - ffmpeg (for audio processing)

## Directory Structure

The download pipeline expects the following directory structure: 

```
root/
├── links/                    # Place your CSV files here
├── downloaded_audio/         # Output directory for audio files
├── downloaded_transcript/    # Output directory for transcripts
├── downloaded_subtitle/      # Output directory for subtitles
└── logs/                    # Directory for log files

## Using the Local Testing Script

The `local_download_testing.py` script is provided to help you test the download pipeline without Supabase integration. This script allows you to:

1. Test downloads using local CSV files
2. Choose between testing the first N rows or random N rows
3. Validate your directory structure
4. Automatically create missing directories

### How to Use

1. First, ensure Supabase is disabled by setting `SUPABASE_ENABLED = False` in `supabase_config.py`

2. Place your CSV file(s) in the `links` directory. The CSV should contain columns with keywords like 'link', 'url', 'video', 'transcript', or 'subtitle'

3. Run the script:
   ```bash
   python local_download_testing.py
   ```

4. The script will:
   - Check your directory structure and offer to create missing directories
   - Show you available CSV files to choose from
   - Let you select whether to test the first N rows or random N rows
   - Allow you to specify how many rows to test
   - Execute the download pipeline for the selected rows

### Testing Options

- **Test First N Rows**: Tests the first N consecutive rows in your CSV file
- **Test Random N Rows**: Tests N randomly selected rows from your CSV file

This is particularly useful for:
- Validating your CSV file format
- Testing download functionality for specific sources
- Debugging download issues
- Testing the pipeline without affecting your production database 