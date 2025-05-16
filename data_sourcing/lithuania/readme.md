# Lithuanian Parliament Session Scraper

This directory contains scripts for scraping parliamentary session data from the Lithuanian Parliament (Seimas), including both audio recordings and transcripts. The data is collected from two separate sources and then merged based on session dates.

## 1. Website Structure and Data Organization

### Content Hierarchy

The Lithuanian Parliament website organizes its content in two distinct ways:

#### Transcripts
- Organized by 4-year terms (convocation periods)
- Each term contains multiple sittings (either regular "eilinė" or irregular "neeilinė")
- Each sitting contains multiple sessions organized by date
- Multiple sessions can occur on the same date

#### Audio Recordings
- Organized chronologically by date
- Less structured than transcripts
- Contains only date information
- Requires specific search query "seimo" and audio file filter

### Access Points

#### Transcripts
- Main URL: `https://www.lrs.lt/sip/portal.show?p_r=35727&p_k=1&p_a=sale_ses_pos&p_kade_id=10&p_ses_id=140`
- Transcripts are available as Word documents (.docx and .doc formats)

#### Audio Recordings
- Main URL: `https://www.lrs.lt/sip/portal.show?p_r=35826&p_k=1&p5=3&q=seimo&page={page_number}`
- The website contains 179 pages of audio recordings
- Each page is directly accessible via URL with the page number parameter

## 2. Data Sources

### Media Content
- Audio recordings are stored as MP3 files on the parliament website
- Each recording is associated with a specific date
- The media archive contains recordings from 11.03.1992 to 27.03.2025
- Requires specific search query "seimo" and audio file filter to avoid overflow

### Transcripts
- Transcripts are available as Word documents (.docx and .doc formats)
- Organized hierarchically by term, sitting type, and sitting number
- Covers sessions from 10.03.1990 to 27.03.2025
- Each transcript is associated with a specific date

## 3. Output Format

### Data Structure

#### Audio Recordings (video_links.csv)
- `video_id`: Unique identifier in format `lithuania_{index}_{date}`
- `mp3_link`: URL to the audio recording
- `title`: Session title (if available)

#### Transcripts (transcript_urls.csv)
- `transcript_id`: Unique identifier in format `lithuania_{convocationDate}_{sittingType}_{sittingNo}_{i}_{date}`
- `docx_link`: URL to the DOCX transcript
- `doc_link`: URL to the DOC transcript
- `title`: Session title

#### Merged Data (lithuania_urls.csv)
- Combined data from both sources, matched by date
- Contains both audio and transcript links for each session

### ID Generation

#### Audio ID Format
- Format: `lithuania_{index}_{date}`
- Example: `lithuania_0_23032015`
- Where:
  - `index`: Sequential number based on the order of appearance
  - `date`: Date in DDMMYYYY format

#### Transcript ID Format
- Format: `lithuania_{convocationDate}_{sittingType}_{sittingNo}_{date}`
- Example: `lithuania_2020_eiline_2_22052021`
- Where:
  - `convocationDate`: The year when the term started
  - `sittingType`: Either "eilinė" (regular) or "neeilinė" (irregular)
  - `sittingNo`: The sitting number within the term
  - `date`: Date in DDMMYYYY format

### Output Files
1. `video_links.csv`: Contains audio recording links
2. `transcript_urls.csv`: Contains transcript links
3. `lithuania_urls.csv`: Merged data with both audio and transcript links
4. `failed_sessions.csv`: Log of sessions that failed to process

## 4. Data Processing Pipeline

### Collection Process
1. **Audio Collection** (`getting_video_links.py`):
   - Iterates through 179 pages of audio recordings
   - Extracts MP3 links and session dates
   - Generates unique video IDs

2. **Transcript Collection** (`getting_transcript_links.py` or `getting_transcript_links_parallel.py`):
   - Processes each term, sitting, and session
   - Extracts transcript links and metadata
   - Generates unique transcript IDs
   - Parallel version improves performance

3. **Data Merging** (`merge_csv.py`):
   - Performs an inner join on dates
   - Matches audio recordings with transcripts
   - Creates a comprehensive dataset

### Error Handling
- Failed sessions are logged to `failed_sessions.csv`
- The system continues processing even if individual sessions fail
- Detailed error messages are provided for debugging

### Data Quality
- Validation of date formats
- Consistency checks between audio and transcript data
- Logging of unmatched entries

## Known Issues

- 692 transcripts have no matching audio recordings
- 104 audio recordings have no matching transcripts
- Some sessions may be missing due to website structure changes
- The audio archive requires specific search parameters to avoid overflow

## Usage

1. Run `getting_video_links.py` to collect audio recordings
2. Run `getting_transcript_links.py` or `getting_transcript_links_parallel.py` to collect transcripts
3. Run `merge_csv.py` to merge the data

## Notes

- The parallel version of the transcript scraper significantly improves performance
- The audio archive contains 179 pages that must be processed sequentially
- The transcript structure is more complex and hierarchical than the audio structure
