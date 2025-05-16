# Supabase Integration Documentation

## Overview
This document explains how and when we interact with our Supabase database throughout the download process.

## Database Initialization
Before starting any downloads, we initialize the parliament entry:
```bash
python download_scripts/initialize_parliament.py --parliament_id croatia --csv_file <path_to_csv>
```
This creates an entry in the `parliament_progress` table with:
- Total number of sessions from CSV
- Initial counters set to 0

## Download Process Updates

### 1. Session Creation
**When**: At the start of processing each row in the CSV
**Where**: `main.py` - main processing loop
**What**: Creates entry in `download_status` table
```python
create_download_entry(session_id)  # Sets initial pending status
```

### 2. Download Status Updates
**When**: During the download process in `with_retry` function
**Where**: `download_utils.py`
**What**: Updates happen at three points:

a) **Download Start**:
- Sets status to 'downloading'
- Records start timestamp
- Updates for either video or transcript based on modality

b) **Download Success**:
- Sets status to 'completed'
- Records completion timestamp
- For videos: adds duration and size metrics

c) **Download Failure**:
- Sets status to 'failed'
- Records error message and timestamp
- Updates retry count

### 3. Automatic Updates
The following updates happen automatically via database triggers:
- Error history maintenance
- Parliament progress statistics
- Success rate calculations
- Estimated completion time updates

## Key Files and Their Supabase Interactions

### 1. supabase_config.py
- Contains database credentials
- Provides utility functions for database operations
- Handles connection management

### 2. download_utils.py
- `with_retry` function manages status updates
- Collects and sends metrics for video downloads
- Handles error recording

### 3. main.py
- Creates initial download entries
- Uses Supabase functions through download_utils

## Update Flow Example

For a video download:
1. Create entry: `pending` status
2. Start download: `downloading` status
3. If successful:
   - Set `completed` status
   - Record metrics (duration, size)
4. If failed:
   - Set `failed` status
   - Record error
   - Retry if attempts remain

## Error Handling

Errors are tracked in multiple ways:
1. `last_error`: Most recent error message
2. `error_history`: JSON array of all errors
3. `retry_count`: Number of attempts made
4. `last_error_timestamp`: When the error occurred

## Monitoring Progress

You can monitor progress through:
1. `parliament_progress` table for overall statistics
2. `download_status` table for individual session status
3. Error history for debugging issues

## Best Practices

1. **Error Messages**
   - Be descriptive
   - Include relevant details
   - Help identify the source

2. **Status Updates**
   - Update promptly
   - Include all relevant metrics
   - Maintain accurate timestamps

3. **Monitoring**
   - Check parliament_progress regularly
   - Monitor error rates
   - Track completion estimates 