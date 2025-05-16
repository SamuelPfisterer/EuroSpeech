# Italian Parliament Data Processing and Video Extraction

This repository contains tools to process Italian Parliament's session data and extract video streams.

## 1. Data Processing and Matching

### Dataset Overview
- Total video records: 2,727
- Total transcript records: 2,781
- Final matched records: 2,699
- Date range: 2006-04-28 to 2024-12-05
- Covering legislations: 15-19

#### Available Document Formats
Each session has multiple document formats available:
- HTML link (web interface)
- PDF link (downloadable document)
- AKN link (XML format for parliamentary documents)

The AKN (Akoma Ntoso) links are constructed from the HTML links using the following pattern:
- HTML: `https://www.senato.it/japp/bgt/showdoc/frame.jsp?tipodoc=Resaula&leg=19&id=1438126`
- AKN: `https://www.senato.it/leg/19/BGT/Testi/Resaula/01438126.akn`

**AKN Link Availability by Legislature:**
- Legislature 19 (current): 100% available
- Legislature 18: ~80% available
- Legislatures 15-17: Not available in AKN format

The AKN (Akoma Ntoso) format appears to have been introduced during Legislature 18 and is fully implemented in Legislature 19. For older sessions (Legislatures 15-17), please use the HTML or PDF formats instead.

### Matching Process

Our matching strategy handles several complexities:

1. **Sitting Number Extraction**
   - Extracted from video titles using regex patterns
   - Handles formats like:
     - "Seduta di Assemblea n. 716"
     - "761ª Seduta pubblica"

2. **Duplicate Handling**
   We identified and handled three types of duplicates:
   - Multiple videos for one session
   - Multiple transcripts for one session
   - Multiple records in both datasets
   
   **Important**: We removed ALL instances of sessions with duplicates to ensure data quality. The final dataset only contains sessions with exactly one video and one transcript.

3. **Final Dataset Format**
   The cleaned dataset (`italian_senate_meetings_ready_to_download_no_duplicates.csv`) contains:
   ```csv
   video_id,generic_video_link,html_link,pdf_link,date,legislation,sitting_number
   19_250,https://webtv.senato.it/...,https://senato.it/...,https://senato.it/...,2024-12-05,19,250
   ```

### Distribution by Legislature
```
Legislature 15: 485 records
Legislature 16: 1,454 records
Legislature 17: 1,433 records
Legislature 18: 466 records
Legislature 19: 250 records
```


## 2. Video URL Extraction

After matching sessions, we extract the actual video stream URLs. Our approach has evolved significantly based on encountered challenges.

### 2.1 Initial Approach (`testing_video.py`)
Our first implementation used Playwright to:
1. Open the video page in a browser
2. Monitor network requests
3. Capture the first video stream URL found
4. Automatically close once the URL is found

### 2.2 Evolution of Async Processing (`async_video_scraper.py`)

#### Development Timeline and Findings

1. **First Attempt - 10 Parallel Tabs**
   - Initial implementation with 10 concurrent tabs
   - No deliberate delays between requests
   - Result: Quick rate limiting by server
   - Failed after processing only a few videos

2. **Reduced to 5 Tabs**
   - Decreased concurrent tabs to 5
   - Added basic delays
   - Result: Still hit rate limits, but processed more videos
   - Failed after ~50 videos

3. **Further Reduction to 3 Tabs**
   - Decreased to 3 concurrent tabs
   - Added random delays (2-4 seconds)
   - Result: Improved but still problematic
   - Successfully processed ~80 videos before rate limiting
   - Encountered:
     - Timeout errors (30000ms exceeded)
     - Failures to find m3u8 URLs
     - Complete request failures

4. **Technical Issues Identified**
   - `networkidle` state waiting caused unnecessary timeouts
   - Even when m3u8 URL was found, script waited full 30 seconds
   - Rate limiting appeared more aggressive with multiple tabs
   - Server seemed to track request frequency across tabs

5. **Final Single-Tab Solution**
   - Completely abandoned parallel processing
   - Implemented:
     - Single tab processing
     - Random delays of 3-6 seconds between requests
     - Additional 1-2 second cooldown after each request
     - Removed `networkidle` state waiting
     - Early exit once m3u8 URL is found
     - Exponential backoff retry logic (3 attempts, 4-10 seconds between retries)

#### Current Implementation Details

1. **Request Timing**
   ```python
   # Pre-request delay
   delay = random.uniform(3, 6)
   await asyncio.sleep(delay)
   
   # Post-request cooldown
   await asyncio.sleep(random.uniform(1, 2))
   ```

2. **Retry Logic**
   ```python
   @retry(
       stop=stop_after_attempt(3),
       wait=wait_exponential(multiplier=1, min=4, max=10),
       reraise=True
   )
   ```

3. **Progress Protection**
   - Saves results every 5 successful extractions
   - Detailed logging:
     ```
     2025-01-02 17:28:36,005 - INFO - Processing video 19_156 (attempt 1)
     2025-01-02 17:28:38,988 - INFO - [2.98s] Found streaming URL for video 19_156
     ```

#### Performance Metrics
- Average time per video: ~10-15 seconds
  - 3-6 seconds initial delay
  - 2-4 seconds processing
  - 1-2 seconds cooldown
  - Additional time for retries if needed
- Expected total runtime for 2,699 videos: 8-11 hours
- Success rate tracking in logs

#### Output Format
csv
video_id,generic_video_link,html_link,pdf_link,date,legislation,sitting_number,streaming_url
19_250,https://webtv.senato.it/...,https://senato.it/...,https://senato.it/...,2024-12-05,19,250,https://senato-vod.senato.it/.../playlist.m3u8

#### Best Practices
1. **Execution Strategy**
   - Run during off-peak hours
   - Monitor first 100 videos closely
   - Watch for timeout errors indicating rate limiting

2. **Error Recovery**
   - Script can be stopped and restarted
   - Already processed URLs are saved
   - Failed URLs logged for retry
   - If rate limits occur:
     - Increase base delay (3-6 seconds → 4-7 seconds)
     - Increase cooldown (1-2 seconds → 2-3 seconds)

3. **Monitoring**
   - Check logs for:
     - Timeout errors
     - Failed URL extractions
     - Success rate percentage
   - Monitor `streaming_urls.csv` for saved progress

This documentation reflects our iterative development process and the specific challenges encountered with the Italian Senate's web infrastructure. The final single-tab approach, while slower, provides the most reliable method for bulk URL extraction without triggering rate limits.