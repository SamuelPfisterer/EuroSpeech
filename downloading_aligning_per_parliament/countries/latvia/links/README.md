# Links Documentation

## Data Structure

The links data contains the following identifiers:

- **video_id**: Unique identifier for each video file
- **transcript_id**: Unique identifier for each transcript
- **session_id**: Composite identifier formed by combining video_id and transcript_id (format: `video_id:transcript_id`)

## Relationships

There is a many-to-many (m:n) relationship between video_id and transcript_id:

- A single video_id may have multiple associated transcript_ids
- A single transcript_id may be associated with multiple video_ids

## Alignment Pipeline

The alignment process follows these steps:

1. **Video Processing**:
   - For each unique video_id:
     - Locate the corresponding video file
     - Perform audio segmentation on the video file

2. **Transcript Alignment**:
   - For each transcript_id associated with the current video_id:
     - Perform alignment between the audio segments and the transcript
     - Calculate the Character Error Rate (CER) for each alignment

3. **Best Match Selection**:
   - Compare the CER rates from all transcript alignments for the current video_id
   - Select the transcript_id with the lowest CER as the best match

This process ensures that we find the most accurate alignment between video audio and transcripts, even in cases where multiple transcripts exist for a single video or where transcripts are shared across multiple videos.
