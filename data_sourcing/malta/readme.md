# Malta Parliament Session Scraper

This script scrapes audio recordings and transcripts of plenary sessions from the Malta Parliament website and combines them into a structured CSV file.

## Website Structure

The Malta Parliament website organizes its content hierarchically:
- Electoral Terms (11th-14th Legislature)
  - Plenary Sessions
    - Audio recordings (MP3 format)
    - Transcripts (DOC/DOCX format)

### Access Points
- Video/Audio Archive: `https://parlament.mt/en/menues/reference-material/archives/media-archive/?legislature={video_id}`
  - The `video_id` parameter uses specific IDs stored in `LEGISLATIVE_TERMS_TO_VIDEO_ID` dictionary:
    - 11th Legislature: "193290"
    - 12th Legislature: "186993"
    - 13th Legislature: "471276"
    - 14th Legislature: "506899"
- Transcripts: `https://parlament.mt/mt/{term}th-leg/plenary-session/?type=committeedocuments`
  - The `{term}` in the URL should be replaced with the electoral term number (11-14)
  - Example: `https://parlament.mt/mt/13th-leg/plenary-session/?type=committeedocuments`

## Data Collection

 - Video - transcript relation is **1:1**

### Audio Recordings
- Accessed through the English version of the website
- Located under the "PLENARY SESSION" panel
- Each session contains:
  - Session number
  - Date and time
  - MP3 download link

### Transcripts
- Available in both DOC and DOCX formats
- Contains session information and date
- Accessed through a separate section of the website

## ID Structure

Both video and transcript records use a consistent ID format for matching:
`{term}_{session_num}_{date}`

Where:
- `term`: Legislative term (11-14)
- `session_num`: Three-digit session number (e.g., "001")
- `date`: Date in DDMMYYYY format

Example: `13_001_01012022` (13th term, session 1, January 1st, 2022)

## Output CSV Structure

The script generates three CSV files:

1. `video_urls.csv`:
   - `video_id`: Unique session identifier
   - `mp3_link`: URL to the audio recording

2. `transcript_urls.csv`:
   - `transcript_id`: Unique session identifier
   - `docx_link`: URL to DOCX transcript (if available)
   - `doc_link`: URL to DOC transcript (if available)

3. `malta_urls.csv` (merged final output):
   - `video_id`: Unique session identifier
   - `mp3_link`: URL to the audio recording
   - `docx_link`: URL to DOCX transcript (if available)
   - `doc_link`: URL to DOC transcript (if available)

The final merged CSV only includes sessions that have both audio recordings and transcripts available.

## Legislative Terms Coverage

The script covers four legislative terms:
- 11th Legislature: Sessions 1-536
- 12th Legislature: Sessions 1-508
- 13th Legislature: Sessions 1-550
- 14th Legislature: Sessions 1-324

## Dependencies

- Python 3.x
- Playwright
- tqdm (for progress bars)
- CSV module (standard library)

## Note

The script currently requires manual intervention to open the first expandable panel in the video archive section due to some interaction limitations with the website's JavaScript implementation.
