# Montenegro Parliament Session Scraper

This script collection scrapes video links and transcripts from the Montenegro Parliament website, processing them into a structured CSV file and providing transcript text extraction functionality.

## Website Structure

The Montenegro Parliament website has a unique structure:
- Main chronology page listing all sessions
- Each session page contains:
  - An embedded YouTube video
  - Interactive transcript sections where each speaker's contribution can be clicked to reveal their full statement

### Access Point
- Main chronology page: `https://www.skupstina.me/en/chronology-of-discussions`
- Individual session pages follow the pattern: `https://www.skupstina.me/en/chronology-of-discussions/{session_id}`

## Data Collection

- Video - transcript relation is **1:1**

### Video Links
- YouTube videos are embedded in each session page
- The script extracts the direct YouTube watch URL from the iframe
- Links are converted from embed format to standard watch format

### Transcripts
The transcript processing is handled in two stages:
1. Initial scraping (`getting_transcript_and_video_links.py`):
   - Stores the session page URL which contains the interactive transcript
   - Each session page URL serves as the transcript source

2. Text processing (`transcript_processors.py`):
   - Processes each session page to extract the full transcript
   - Handles interactive elements by:
     - Clicking each speaker section
     - Extracting speaker title and statement
     - Combining into formatted text
   - Output format:
     ```
     **Speaker Title**
     Speaker Text

     **Next Speaker Title**
     Next Speaker Text
     ```

## ID Structure

Video IDs follow the format: `montenegro_{index}_{date}`
Where:
- `index`: Sequential number based on the order of appearance (1, 2, 3, ...)
- `date`: Date in DDMMYYYY format

Example: `montenegro_1_01012022`