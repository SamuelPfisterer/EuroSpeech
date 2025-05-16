# Bulgaria Parliament Session Scraper

This scraper collects plenary session data from the Bulgarian Parliament website, including session transcripts and related video recordings. It extracts both transcript text and links to video recordings for parliamentary sessions dating from 2010 to 2025.

## 1. Website Structure and Data Organization

### Content Hierarchy
The Bulgarian Parliament website organizes its content hierarchically by:
- Years (2010-2025)
- Months within each year
- Individual sessions within each month, identified by date (DD/MM/YYYY)

Each session page contains:
- A title and date of the session
- An embedded transcript in HTML format
- Multiple embedded MP4 videos of the session (typically different parts of the session)

### Access Points
- Base URL: https://parliament.bg/bg/plenaryst
- Session URL pattern: https://parliament.bg/bg/plenaryst/ns/{term}/ID/{session_id}
- The website uses a dynamic interface where years and months must be clicked to reveal session links

## 2. Data Sources

### Media Content
- Videos are embedded as MP4 files directly on the session pages
- Each session may have multiple video segments accessible via buttons on the page
- Videos are played through a custom HTML5 video player
- MP4 links are extracted by clicking through each available video button and capturing the source URL
- Video - transcript relation is **n:1**

### Transcripts
- Transcripts are embedded as HTML content on the session pages
- Format: HTML with structured text content
- Accessed directly from the session page through the same URL
- Processed to extract plain text while preserving paragraph structure

## 3. Technical Implementation

### Protection Measures
- Implemented delays between requests (3-5 seconds) to avoid overloading the server
- Browser automation via Playwright to handle JavaScript-rendered content
- Error logging for failed requests and data extraction issues
- Parallel processing capability to distribute workload across multiple processes

## 4. Output Format

### Data Structure
The scraper generates CSV files with the following columns:
- `video_id`: Unique identifier for each video segment
- `mp4_link`: Direct URL to the MP4 video file
- `title`: Title of the parliamentary session
- `transcript_id`: Unique identifier for the transcript
- `process_transcript_link`: URL to the session page containing the transcript

### ID Generation
- Video ID format: `bulgaria_{video_number}_{date}`
  - `video_number`: Sequential number starting from 0 for each video in a session
  - `date`: Date in DDMMYYYY format (without separators)
- Transcript ID format: `bulgaria_{date}`
  - `date`: Date in DDMMYYYY format (without separators)

### Output Files
- `bulgaria_urls.csv`: Main output file containing all video and transcript links
- `bulgaria_urls_parallel.csv`: Output from the parallel processing version
- `scraping.log` and `scraping_parallel.log`: Log files for tracking the scraping process

## 5. Data Processing Pipeline

### Collection Process
1. **Session Discovery**: Navigate through years and months to discover session links
2. **Video Collection**: For each session, extract all available video segments by:
   - Navigating to the session page
   - Clicking through video segment buttons
   - Extracting MP4 source URLs
3. **Transcript Processing**: For each session:
   - Extract the session title and date
   - Record the URL for later transcript text extraction
4. **Text Extraction**: Using the `transcript_processors.py` module to extract plain text from the HTML content

### Error Handling
- Exception handling for network errors and page navigation issues
- Logging of errors with session URLs for debugging
- Retry mechanisms in the parallel implementation

### Data Quality
- Date format validation using regex pattern matching
- Error logging for missing or incomplete data
- Verification that video links are valid MP4 URLs

## Known Issues

- Some older sessions may have different page structures
- Network timeouts can occur during extended scraping sessions
- Extended runtime for comprehensive scraping (mitigated by parallel implementation)

## Notes

The Bulgarian Parliament website contains sessions dating back to 2010, with varying quality and completeness of transcripts and videos. The parallel implementation significantly reduces total scraping time by distributing work across multiple processes, each handling different years.