# Slovenia Parliament Session Scraper

This scraper collects parliamentary session videos and transcripts from the Slovenian Parliament (Državni zbor) website. It handles both video recordings and transcripts, processing them separately and then merging the data.

## 1. Website Structure and Data Organization

### Content Hierarchy
- Videos are organized by calendar dates
- Transcripts are organized by:
  - Mandate (Term)
  - Session type (Regular/Special)
  - Session dates (multiple dates possible per session)

### Access Points
- Video portal: https://www.dz-rs.si/wps/portal/Home/
- Transcript portal: https://www.dz-rs.si/wps/portal/Home/seje/sejeDZ/poDatumu/
- Video coverage: Years 2015 and 2020-2025
- Each session may contain zero, one, or multiple video links

## 2. Data Sources

### Media Content
- Videos are hosted on an archive website
- Format: m3u8 streaming links (temporary)
- Access requires special handling due to anti-scraping measures
- Videos are accessed through a calendar-based interface

### Transcripts
- Format: Embedded content on separate website
- Organization: 
  - Hierarchical structure (mandate → session type → dates)
  - Multiple transcript dates possible per session
  - Accessed via "zapis seje" (session record) links
- Pagination system for session lists (not URL-accessible)

## 3. Technical Implementation

### Protection Measures
- Uses Camoufox for bypassing anti-scraping measures on archive website
- Handles temporary m3u8 link generation during download
- Implements delays and proper session handling
- Special handling for archive website access (standard automation tools like Playwright encounter errors)

## 4. Output Format

### Data Structure
The scraper generates multiple CSV files:
- `video_links.csv`: Contains extracted video links
- `transcript_links.csv`: Contains transcript links
- Final merged dataset combining both sources

### ID Format Specifications

#### Transcript IDs
- Format: `slovenia_convocationDate_sessionNo_sessionType_transcriptNo_date`
- Example: `slovenia_2022_29_redna_0_24032025`
- Components:
  - convocationDate: Term/mandate start year
  - sessionNo: Sequential number of the session
  - sessionType: Type of session (redna/izredna)
  - transcriptNo: Transcript index (usually 0)
  - date: Date in DDMMYYYY format

#### Video IDs
- Format: `slovenia_sessionNo_sessionType_videoNo_date`
- Example: `slovenia_93_Izredna_0_30012025`
- Components:
  - sessionNo: Sequential number of the session
  - sessionType: Type of session (redna/izredna)
  - videoNo: Index for multiple videos within same session
  - date: Date in DDMMYYYY format

### Data Processing
- Video processing:
  - Navigates through calendar
  - Extracts archive links
  - Processes links to get temporary m3u8 URLs during download
- Transcript processing:
  - Iterates through mandates and pages
  - Extracts transcript links for each session date

## 5. Data Processing Pipeline

### Collection Process
1. Video Collection (`getting_video_links.py`/`getting_video_links_parallel.py`):
   - Navigates calendar until end date (01.05.1990)
   - Extracts archive links for each session
   - Processes links for downloading

2. Transcript Collection (`getting_transcript_links.py`):
   - Processes each mandate
   - Handles pagination
   - Extracts transcript links

3. Data Merging (`merge_csv.py`):
   - Video - transcript relation is **n:m**
   - Combines video and transcript data
   - Handles data cleaning and matching

### Data Quality
- Current statistics:
  - 47 videos discarded
  - 463 transcripts discarded
- Logging system in place (`scraping.log`)

## Known Issues

- Archive website has anti-scraping measures
- Standard automation tools (Playwright, Botasaurus) face connection issues
- Temporary nature of m3u8 links requires special handling
- Pagination system for transcripts not directly URL-accessible

## Notes

- The scraper handles complex session structures where one session may span multiple dates
- Special attention is required for handling temporary media URLs
- Robust error handling and logging system in place