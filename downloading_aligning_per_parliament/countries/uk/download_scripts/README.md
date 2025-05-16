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
- `mp3_link`: Direct link ending in `.mp3` (uses curl_cffi to bypass Cloudflare and other protections)
- `generic_video_link`: Any video/audio URL supported by yt-dlp, including:
  - Direct video files (MP4, etc.)
  - Direct audio files (MP3, etc.)
  - Video streaming sites
  - Web players
- `generic_m3u8_link`: Webpage containing embedded m3u8 stream
- `processed_video_link`: Link requiring custom extraction to get downloadable URL
  - Requires implementing a video link extractor (see Video Link Extraction section)
  - To check if your URL is supported:
    1. Install yt-dlp: `pip install yt-dlp`
    2. Test your URL: `yt-dlp --simulate URL`

#### Transcript Sources
- `pdf_link`: Direct link ending in `.pdf`
- `html_link`: Link to HTML transcript page
- `dynamic_html_link`: Link to dynamically loaded HTML page (uses Playwright)
- `doc_link`: Direct link to Word document (.doc or .docx)
- `txt_link`: Direct link to text file or endpoint that returns text content
- `processed_transcript_html_link`: Link to transcript page that needs custom HTML processing
- `processed_transcript_text_link`: Link to transcript page that needs custom text processing

#### Subtitle Sources
- `srt_link`: Direct link ending in `.srt`

### Example CSV Format
```csv
video_id,mp4_video_link,doc_link,txt_link,processed_transcript_html_link
12345,https://example.com/video/12345.mp4,https://example.com/transcript/12345.docx,https://example.com/transcript/12345.txt,https://example.com/transcript/12345
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
│   ├── html_transcripts/        # HTML format transcripts
│   ├── dynamic_html_transcripts/ # Dynamically loaded HTML transcripts
│   ├── processed_html_transcripts/  # Custom processed HTML transcripts
│   └── processed_text_transcripts/  # Custom processed text transcripts
└── downloaded_subtitle/           # All subtitle content
    └── srt_subtitles/          # SRT format subtitles
```

## Custom Transcript Processing

For parliaments that require custom processing of transcripts (e.g., extracting content from complex web pages), you can use the processed transcript columns. To enable this:

1. Create a `transcript_processors.py` file in your parliament's directory
2. Implement one or both processor functions:
   - `process_transcript_html(url: str) -> str`: Returns processed HTML content
   - `process_transcript_text(url: str) -> str`: Returns processed text content
3. Use the corresponding columns in your CSV:
   - `processed_transcript_html_link`: For HTML output
   - `processed_transcript_text_link`: For text output

Example processor implementation:
```python
def process_transcript_html(url: str) -> str:
    """Process a transcript URL and return HTML content."""
    try:
        # Your HTML processing logic here
        return processed_html_content
    except Exception as e:
        raise ValueError(f"Failed to process HTML transcript: {str(e)}")

def process_transcript_text(url: str) -> str:
    """Process a transcript URL and return text content."""
    try:
        # Your text processing logic here
        return processed_text_content
    except Exception as e:
        raise ValueError(f"Failed to process text transcript: {str(e)}")

## Video Link Extraction

For parliaments that require custom processing to obtain downloadable video links (e.g., extracting m3u8 URLs from video pages):

1. Create a `video_link_extractors.py` file in your parliament's directory
2. Implement the extractor function:
   ```python
   def process_video_link(url: str) -> tuple[str, str]:
       """Extract downloadable link from video page.
       
       Args:
           url: The video page URL to process
           
       Returns:
           tuple[str, str]: (downloadable_url, link_type) where
           link_type is one of: 'mp4_video_link', 'm3u8_link', etc.
           
       Example:
           url = "https://parliament.example.com/video/12345"
           # Extract m3u8 URL from page
           m3u8_url = extract_m3u8_from_page(url)
           return m3u8_url, 'm3u8_link'
       """
       try:
           # Your extraction logic here
           # e.g., fetch page, parse HTML, find video URL
           return downloadable_url, link_type
       except Exception as e:
           raise ValueError(f"Failed to extract video link: {str(e)}")
   ```
3. Use the `processed_video_link` column in your CSV

The extractor must return a tuple containing:
- `downloadable_url`: The actual URL that can be downloaded
- `link_type`: One of the supported types matching existing download functions:
  - 'mp4_video_link'
  - 'm3u8_link'
  - 'youtube_link'
  - 'generic_video_link'
  - 'generic_m3u8_link'

This allows you to:
1. Handle complex video pages that don't expose direct download links
2. Extract embedded video URLs
3. Transform video page URLs into downloadable formats
4. Reuse existing download functionality for the extracted links

Example CSV usage:
```csv
video_id,processed_video_link
12345,https://parliament.example.com/video/12345
```

The system will:
1. Call your extractor to get the actual video URL
2. Use the appropriate download function based on the returned link type
3. Process and save the video as usual

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

### Dependencies

For dynamic HTML content, you'll need to install Playwright:

```bash
pip install playwright
playwright install chromium
```

This is required for downloading transcripts from pages that load content dynamically using JavaScript.