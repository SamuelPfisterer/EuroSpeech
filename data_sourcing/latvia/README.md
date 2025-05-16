# Latvia Parliament Data Processing

This project involves processing data from the Latvian Parliament (Saeima), focusing on matching parliamentary session videos with their corresponding transcripts.

## Data Overview

- `transcript_links.csv`: Contains links to session transcripts
- `video_links.csv`: Contains links to session videos
- Total videos: 2,007
- Videos with matching transcript dates: 1,749 (87.14% coverage)

## Matching Strategy

Our analysis revealed two distinct periods requiring different matching approaches:

### Pre-2020 Data
- 900 total videos before 2020
- 759 videos can be matched using date-based alignment
- We focus on dates with exactly one transcript to ensure reliable matching
- Distribution of matches:
  * 123 dates: 1 transcript, 1 video
  * 101 dates: 1 transcript, 2 videos
  * 60 dates: 1 transcript, 3 videos
  * etc.

### Post-2020 Data
- 1,107 videos from 2020 onwards
- Hypothesis: These can be matched by consulting the transcript webpages
- Example transcript page: https://www.saeima.lv/lv/transcripts/view/2581
- Assumption to verify: Post-2020 transcripts contain direct references to their corresponding videos
- **Important**: Need to verify this assumption by:
  1. Testing a sample of transcript pages
  2. Checking if video URLs are consistently present
  3. Verifying the format and reliability of video references
  4. Understanding any exceptions or special cases

### Two-Phase Matching Approach

1. **Phase 1: Pre-2020 Date-Based Matching**
   - Match 759 videos from dates with single transcripts
   - This provides a reliable baseline of matches
   - Simple date-based alignment is sufficient due to 1:N relationship

2. **Phase 2: Post-2020 Webpage-Based Matching**
   - Match 1,107 videos from 2020 onwards
   - Requires scraping transcript pages to find video references
   - More accurate due to explicit video-transcript relationships
   - **Prerequisite**: Verify assumption about video references on transcript pages

This approach will potentially match 1,866 videos (92.97% of all videos), providing a comprehensive dataset for further analysis.

## Why This Approach?

1. **Data Quality**:
   - Pre-2020: Simpler structure with mostly 1:N (one transcript to N videos) relationships
   - Post-2020: More complex relationships but better documentation on webpages (to be verified)

2. **Reliability**:
   - Phase 1 uses only unambiguous matches (single transcript dates)
   - Phase 2 depends on verification of transcript-video references

3. **Coverage**:
   - Maximizes the number of reliable matches
   - Leaves only 7% of videos potentially unmatched
   - Avoids risky assumptions in ambiguous cases

## Scripts

Current:
- `match_videos_transcripts.py`: Analyzes the relationship between transcripts and videos
- `check_duplicate_dates.py`: Analyzes duplicate dates in transcripts
- `match_post_2020.py`: Scrapes post-2020 transcript pages to extract video links and match them with transcripts
- `combine_matches.py`: Combines both matching approaches into a single comprehensive dataset

To-Do:
1. Run `match_post_2020.py` to verify our assumption about video links on transcript pages
2. Create `match_pre_2020.py` for Phase 1 matching
3. Analyze results from both phases and combine into a final dataset

Note: The implementation of these scripts is tracked in the Composer thread "Latvia-matching-links" from January 7th.

## Usage

### Phase 2: Post-2020 Matching
```
python match_post_2020.py
```
This script:
1. Reads transcript links from `transcript_links.csv`
2. Filters for transcripts from 2020 onwards
3. Scrapes each transcript page to extract video links
4. Tracks and displays a continuously updating hit rate (percentage of transcripts with video links)
5. Saves two output files:
   - `post_2020_matches.csv`: Contains all successful transcript-video matches
   - `transcripts_without_videos.csv`: Records transcripts where no video links were found

The script provides detailed statistics including:
- Number of video-transcript matches found
- Number of unique videos and transcripts
- Final hit rate (percentage of transcripts with videos)
- List of transcripts without video links and the reason (e.g., "No video links found" or "Failed to scrape page")

### Combining All Matches
```
python combine_matches.py
```
This script:
1. Loads data from all sources:
   - `post_2020_matches.csv`: Webpage-based matches from Phase 2
   - `transcript_links.csv`: All transcript links
   - `video_links.csv`: All video links
2. Combines both matching approaches:
   - For post-2020 videos: Uses webpage-based matches when available
   - For pre-2020 videos with single transcript dates: Uses reliable date-based matching
   - For all other videos: Includes all possible transcript matches from the same date
3. Saves the results in two formats:
   - `all_video_transcript_matches.csv`: One row per video with transcript matches as JSON
   - `all_video_transcript_matches.json`: Detailed JSON structure with all matching information

The script categorizes matches by type:
- `webpage`: Matches found through webpage scraping (most reliable)
- `date_single`: Date-based matches where there's only one transcript for that date (reliable)
- `date_multiple`: Date-based matches where there are multiple transcripts for that date (less reliable)
- `date_post_2020`: Date-based fallback matches for post-2020 videos without webpage matches

The output includes comprehensive statistics on match coverage and distribution.
