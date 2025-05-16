# Portugal Parliamentary Data Collection

## Project Overview
This project collects parliamentary session data from the Portuguese Parliament, including video recordings, transcripts, and detailed intervention information.

## Project Structure
```
Portugal/
├── session_links/
│   └── all_session_recordings.csv    # Contains 1,995 session links with metadata
├── per_session_scraping/
│   ├── scrape_session.py            # Main script for detailed session info
│   └── get_transcript_file.py       # Utility for downloading transcripts
└── get_session_links.py             # Script for collecting session links
```

## Current State

### 1. Session Links Collection (Completed)
- Successfully collected 1,995 session recordings in `all_session_recordings.csv`
- Data includes:
  - Cycle and legislation information
  - Session numbers and titles
  - Session dates
  - Links to video recordings

### 2. Per-Session Processing
The project includes two main processing scripts:

#### a. Session Scraping (`scrape_session.py`)
- **Functionality:**
  - Extracts detailed intervention data from each session
  - Collects speaker information, timestamps, and party affiliations
  - Identifies transcript links
  - Creates structured data for each intervention
- **Output:**
  - `session_details.csv`: Basic session information
  - `interventions.csv`: Detailed intervention data
- **Data Collected per Intervention:**
  - Intervention number and timing (start/end)
  - Speaker name and party affiliation
  - Duration and intervention type
  - Individual intervention links

#### b. Transcript Download (`get_transcript_file.py`)
- **Functionality:**
  - Downloads transcript files in TXT format
  - Handles URL parsing and parameter extraction
  - Manages POST requests to parliament export endpoint

### 3. Data Organization
The scraped data is organized into:
- Session-level information
- Detailed intervention data
- Downloadable transcripts

## CURRENT STATE AND IMMEDIATE NEXT STEPS

### Video Downloads ✅
- The session links in `all_session_recordings.csv` can be used directly as video links
- Videos can be downloaded using yt-dlp
- No additional processing needed for video URL extraction

### Transcript Processing 🔄
We need to rewrite the per-session transcript processing scripts. Two possible approaches:

1. **API Approach (Recommended)**
   - More reliable and stable
   - Uses the parliament's export endpoint
   - Less prone to breaking due to HTML structure changes
   - Current implementation in `get_transcript_file.py`

2. **BeautifulSoup Approach (Alternative)**
   - Manual HTML parsing
   - More flexible but potentially fragile
   - Useful as fallback if API approach fails
   - Current implementation in `scrape_session.py`

### Next Implementation Steps
1. Create unified script that:
   - Processes each session
   - Extracts transcript text using preferred method
   - Passes transcript data to downloading function
2. Implement proper error handling and logging
3. Add data validation for extracted transcripts
4. Create mapping between transcript segments and video timestamps

## Next Steps
1. **Data Collection**
   - Run the session scraping script on all 1,995 sessions
   - Download and organize transcripts
   - Verify data completeness

2. **Data Processing**
   - Implement quality checks for scraped data
   - Match transcripts with video segments
   - Create mapping between interventions and transcript sections

3. **Data Validation**
   - Verify timestamp accuracy
   - Check for missing transcripts or interventions
   - Validate speaker and party information

## Technical Notes
- The scraping scripts handle pagination and error cases
- Intermediate results are saved every 10 sessions
- Transcript downloads use POST requests with specific parameters
- All data is saved in CSV format for easy processing 