# Norway Parliamentary Speeches Data Collection

## Project Progress

### Previous Approach (Discontinued)
1. **HTML Processing Attempt**
   - Initially tried processing HTML pages directly
   - Encountered consistent issues:
     - Timeout errors with 2016-2017 transcripts
     - Unreliable selector matches
     - Website structure complexities
   - Second attempt with improved HTML scraping:
     - Modern format (post-2015): Successfully extracts using `?all=true` parameter
     - Legacy format (pre-2015): Partially working
       - Different HTML structure using classes like `content-area-react` and `ref-uinnrykk`
       - Some sections successfully scraped, others still problematic
       - Inconsistent HTML structure across different section types
   - Decision made to switch to PDF-based approach for better reliability

### Current Approach
1. **Transcript Link Collection** (`getting_transcript_links.py`)
   - Successfully gathered transcript links from 2010-2024
   - Generated `transcript_links_with_dates.csv` (1,410 entries)
   - Includes meeting dates and corresponding URLs
   - Important note on transcript accessibility:
     - For transcripts after 2015: Full transcript available via `?all=true` URL parameter
     - For transcripts before 2015: Requires manual navigation through session parts

2. **Next Steps**
   - Develop script to download PDF transcripts for each session (Priority)
   - Handle multiple videos per transcript link scenario
   - Implement PDF processing for text extraction
   - Match video segments with corresponding transcript sections

### Project Structure
```
Norway/getting_links/
├── getting_transcript_links.py    # Script for collecting transcript URLs
├── getting_video_links.py        # Script for video link extraction
├── output/
│   └── video_links.csv          # Collected video links
└── Various CSV files:
    └── transcript_links_with_dates.csv
```

### Upcoming Tasks
1. **PDF Processing Pipeline**
   - Create script for bulk PDF downloads
   - Implement PDF text extraction
   - Develop mapping between PDF content and video segments

2. **Video Link Management**
   - Handle cases with multiple videos per transcript
   - Create robust mapping between transcript sections and video segments
   - Implement verification of video-transcript matches

3. **Data Organization**
   - Design storage structure for PDFs
   - Create mapping files for transcript-video relationships
   - Implement validation checks for completeness
