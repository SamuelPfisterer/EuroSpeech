# CSV Format Documentation for main.py

This documentation specifically describes how to use the `main.py` script with CSV input files. The script processes parliamentary meeting content from a structured CSV file and downloads the corresponding media files.

## Purpose
The `main.py` script takes a CSV file containing links to various parliamentary content (videos, transcripts, subtitles) and downloads them into an organized directory structure.

## Usage

```bash
python main.py --csv_file <csv_file_name> --start_idx <start_index> --end_idx <end_index>
```

Arguments:
- `--csv_file`: Name of your input CSV file (default: 'danish_parliament_meetings.csv')
- `--start_idx`: Starting row index in the CSV file
- `--end_idx`: Ending row index in the CSV file

## CSV Format Requirements

### Required Columns
At least one of these ID columns must be present:
- `video_id`: Unique identifier for video content
- `transcript_id`: Unique identifier for transcript content

### Optional URL Columns
Each URL must point to a file with the correct extension:

#### Video/Audio Sources
- `mp4_video_link`: Direct link ending in `.mp4`
- `youtube_link`: YouTube video URL
- `m3u8_link`: Stream URL ending in `.m3u8`
- `generic_video_link`: Any video URL supported by yt-dlp
  - To check if your URL is supported:
    1. Install yt-dlp: `pip install yt-dlp`
    2. Test your URL: `yt-dlp --simulate URL`

#### Transcript Sources
- `pdf_link`: Direct link ending in `.pdf`
- `html_link`: Link to HTML transcript page

#### Subtitle Sources
- `srt_link`: Direct link ending in `.srt`

### Example CSV Format
```csv
video_id,mp4_video_link,pdf_link,srt_link
12345,https://example.com/video/12345.mp4,https://example.com/transcript/12345.pdf,https://example.com/subs/12345.srt
```

## Output Directory Structure

```
BASE_DIR/
├── downloaded_audio/              # All audio content
│   ├── mp4_converted/            # MP4 videos converted to audio
│   ├── youtube_converted/        # YouTube videos converted to audio
│   ├── m3u8_streams/            # Streaming content converted to audio
│   └── generic_video/           # Other video formats converted to audio
├── downloaded_transcript/         # All transcript content
│   ├── pdf_transcripts/         # PDF format transcripts
│   └── html_transcripts/        # HTML format transcripts
└── downloaded_subtitle/           # All subtitle content
    └── srt_subtitles/          # SRT format subtitles
```

Each downloaded file will be named according to its ID (from either `video_id` or `transcript_id`).

## Example Usage

```bash
# Process rows 0-100 from default CSV file
python main.py --start_idx 0 --end_idx 100

# Process specific CSV file
python main.py --csv_file my_parliament_data.csv --start_idx 0 --end_idx 50
```

## Adding New Source Types

To add support for a new source type, you'll need to modify two files:

### 1. In main.py

Add the new source to the configuration dictionaries:

```python
COLUMN_TO_MODALITY = {
    # ... existing mappings ...
    'new_source_link': {
        'modality': 'audio',  # or 'transcript' or 'subtitle'
        'subfolder': 'new_source_converted'
    }
}

DOWNLOAD_FUNCTIONS = {
    # ... existing mappings ...
    'new_source_link': download_and_process_new_source
}
```

### 2. In download_utils.py

Add a new download function:

```python
def download_and_process_new_source(url: str, output_path: str) -> bool:
    """Download and process content from new source.
    
    Args:
        url: Source URL to download from
        output_path: Where to save the processed file
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # 1. Download the content
        # 2. Process if needed (e.g., convert to audio)
        # 3. Save to output_path
        return True
    except Exception as e:
        logging.error(f"Failed to process {url}: {str(e)}")
        return False
```

### Checklist for Adding New Sources

1. **Determine Content Type**
   - Is it audio/video content?
   - Is it transcript content?
   - Is it subtitle content?

2. **Choose Modality and Subfolder**
   - Add to appropriate modality ('audio', 'transcript', or 'subtitle')
   - Create meaningful subfolder name

3. **Implement Download Function**
   - Handle download logic
   - Process content if needed (e.g., convert formats)
   - Implement proper error handling
   - Add logging

4. **Test Implementation**
   - Test with sample URLs
   - Verify output format
   - Check error handling
   - Validate file structure

5. **Update Documentation**
   - Add new column to CSV format documentation
   - Document URL requirements
   - Add examples

### Common Patterns

For different types of sources, you might need to:

1. **For Video Sources**
   - Convert to audio (usually MP3)
   - Use yt-dlp or similar tools
   - Handle streaming protocols

2. **For Transcript Sources**
   - Parse HTML/PDF
   - Extract text content
   - Handle character encoding

3. **For Subtitle Sources**
   - Convert between subtitle formats
   - Handle timing synchronization
   - Process character encoding