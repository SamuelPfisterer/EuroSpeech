# Swedish Parliament Session Scraper

This project scrapes parliamentary sessions from the Swedish Riksdag website, including session metadata, video URLs, and transcripts.

## Components

1. **Session Links** (`getting_session_links.py`)
   - Scrapes basic session information (title, date, duration, URL)
   - Saves to `sessions.csv`

2. **Video URLs** (`getting_video_url.py`)
   - Extracts direct video URLs from session pages
   - Updates `sessions.csv` with video_url column

3. **Transcripts** (`getting_transcripts.py`)
   - Extracts speech transcripts and speaker information
   - Saves in multiple formats:
     1. `*_speeches.json`: Main transcript data with structure:
        ```json
        {
          "speaker": "Speaker Name",
          "speech_number": "Anf. X Speaker Name (Party)",
          "content": "Full speech content",
          "video_position": "position in video",
          "timestamp": "HH:MM format",
          "position_seconds": seconds into video
        }
        ```
     2. `*_speakers.json`: Speaker timing data:
        ```json
        {
          "speaker": "Speaker Name",
          "timestamp": "HH:MM",
          "position_seconds": seconds,
          "video_position": "position",
          "href": "link to position"
        }
        ```
     3. `*.txt`: Human-readable format with structure:
        ```
        [SPEECH]
        Speaker: Speaker Name
        Time: HH:MM
        Position: video_position
        Reference: Anf. X Speaker Name (Party)

        Content:
        Full speech content...

        ================================================================================
        ```

## Usage

1. First, get all session links:
```bash
python getting_session_links.py
```

2. Extract video URLs:
```bash
python getting_video_url.py
```

3. Get transcripts:
```bash
python getting_transcripts.py
```

## Working with Transcripts

### Converting JSON to TXT manually
If you have existing JSON transcripts and want to convert them to TXT format:

```python
from pathlib import Path
import json

def convert_json_to_txt(json_path, output_dir='transcripts'):
    """Convert a speeches JSON file to structured TXT format"""
    # Read JSON
    with open(json_path, 'r', encoding='utf-8') as f:
        speeches = json.load(f)
    
    # Create output filename
    base_name = Path(json_path).stem.replace('_speeches', '')
    txt_path = Path(output_dir) / f"{base_name}.txt"
    
    # Write TXT
    with open(txt_path, 'w', encoding='utf-8') as f:
        for speech in speeches:
            # Write header with metadata
            f.write(f"[SPEECH]\n")
            f.write(f"Speaker: {speech['speaker']}\n")
            f.write(f"Time: {speech['timestamp']}\n")
            f.write(f"Position: {speech['video_position']}\n")
            f.write(f"Reference: {speech['speech_number']}\n")
            f.write("\nContent:\n")
            f.write(speech['content'])
            f.write("\n\n" + "="*80 + "\n\n")

# Example usage:
convert_json_to_txt('transcripts/utgiftsomrade-8-migration_hc01sfu4_speeches.json')
```

### Parsing TXT back to structured data
If you need to extract structured data from the TXT format:

```python
def parse_txt_transcript(txt_path):
    """Parse a transcript TXT file back into structured data"""
    speeches = []
    current_speech = None
    
    with open(txt_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    for line in lines:
        line = line.strip()
        if line == '[SPEECH]':
            if current_speech:
                speeches.append(current_speech)
            current_speech = {'content': ''}
        elif line.startswith('Speaker: '):
            current_speech['speaker'] = line[8:]
        elif line.startswith('Time: '):
            current_speech['timestamp'] = line[6:]
        elif line.startswith('Position: '):
            current_speech['video_position'] = line[10:]
        elif line.startswith('Reference: '):
            current_speech['speech_number'] = line[11:]
        elif line == 'Content:':
            continue
        elif line and not line.startswith('='):
            current_speech['content'] += line + '\n'
    
    if current_speech:
        speeches.append(current_speech)
    
    return speeches

# Example usage:
speeches = parse_txt_transcript('transcripts/utgiftsomrade-8-migration_hc01sfu4.txt')
```

This allows you to:
1. Convert existing JSON transcripts to TXT format
2. Parse TXT transcripts back into structured data if needed
3. Work with whichever format is most convenient for your use case