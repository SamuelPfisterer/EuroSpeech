# Croatia Data Processing

## Observations and Analysis

We found that there are duplicates in our extracted M3U8 links:
- Total rows in croatian_parliament_media_links_ready_to_download.csv: 6707 (with 7 duplicates)
- Total rows in extracted_m3u8_links.csv: 5822 (with 2072 duplicates)

## Performed Actions

1. Extracted unique video_ids from the m3u8_urls
   - Pattern used: `HLSArchive/([0-9]+-[0-9]+)/HLS`
   - Example: from `https://itv2.sabor.hr/HLSArchive/20241122091525-8880/HLS/index.m3u8` we extracted `20241122091525-8880`
   - Found 3750 unique m3u8_urls and 3750 unique video_ids, confirming our extraction method properly captures unique identifiers

2. Created two enhanced CSV files:
   - `extracted_m3u8_links_with_video_ids.csv`: Added video_id column to extracted_m3u8_links.csv
   - `croatian_parliament_media_links_final.csv`: Added video_id column to croatian_parliament_media_links_ready_to_download.csv

3. Successfully matched 5804 out of 6707 rows (86.5%) between the original datasets
   - This is sufficient for our purposes as it covers all our completed video downloads

## Future Steps

For renaming audio files, we need to:
1. Check if there's a file with name video_id.opus in the downloaded_audio/m3u8_streams directory
2. If not, and if a transcript_id.opus file exists, rename transcript_id.opus to video_id.opus
3. This ensures consistent naming between our file system and CSV data
