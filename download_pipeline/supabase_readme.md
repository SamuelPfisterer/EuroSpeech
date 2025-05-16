# Supabase Database Documentation

## Overview
This document describes the Supabase database setup for the Croatian Parliament video/transcript download system. The database tracks download progress, errors, and statistics for parliamentary sessions across different parliaments.

## Database Schema

### Tables

#### 1. download_status
Tracks individual download sessions and their progress.

```sql
create table download_status (
    parliament_id text not null,
    session_id text not null,
    
    -- Status fields
    video_status text check (video_status in ('pending', 'downloading', 'completed', 'failed')),
    transcript_status text check (transcript_status in ('pending', 'downloading', 'completed', 'failed')),
    
    -- Timestamps
    video_download_started timestamp with time zone,
    video_download_completed timestamp with time zone,
    transcript_download_started timestamp with time zone,
    transcript_download_completed timestamp with time zone,
    
    -- Performance metrics
    video_size_bytes bigint,
    video_duration_seconds integer,
    download_speed_mbps real,
    
    -- Error handling
    retry_count integer default 0,
    last_error text,
    last_error_timestamp timestamp with time zone,
    error_history jsonb default '[]'::jsonb,
    
    -- Job tracking
    slurm_job_id text,
    batch_id text,
    
    -- Constraints
    primary key (parliament_id, session_id),
    created_at timestamp with time zone default now()
);
```

#### 2. parliament_progress
Stores aggregated statistics and progress for each parliament.

```sql
create table parliament_progress (
    parliament_id text primary key,
    
    -- Session counts
    total_sessions integer,
    completed_videos integer default 0,
    completed_transcripts integer default 0,
    
    -- Duration tracking
    total_duration_hours real,
    downloaded_duration_hours real default 0,
    
    -- Performance metrics
    failed_downloads integer default 0,
    active_downloads integer default 0,
    avg_download_speed_mbps real,
    
    -- Recent activity
    last_successful_download timestamp with time zone,
    last_error_count integer default 0,
    success_rate real,
    
    -- Estimation
    estimated_completion_time timestamp with time zone,
    
    -- Metadata
    last_updated timestamp with time zone default now(),
    created_at timestamp with time zone default now()
);
```

## Automatic Updates

### Error History
The system automatically maintains an error history using a trigger. When you update `last_error`, the system automatically:
- Adds the error to the `error_history` JSONB array
- Includes timestamp and status information
- Preserves previous errors

### Parliament Progress
The system automatically updates parliament-level statistics when:
- New downloads are added
- Download status changes
- Errors occur

## Usage Guide

### 1. Connecting to Supabase
```python
from supabase import create_client

url = "YOUR_SUPABASE_URL"
key = "YOUR_SUPABASE_KEY"
supabase = create_client(url, key)
```

### 2. Common Operations

#### Creating a New Download Entry
```python
def create_download_entry(parliament_id: str, session_id: str):
    supabase.table('download_status').insert({
        'parliament_id': parliament_id,
        'session_id': session_id,
        'video_status': 'pending',
        'transcript_status': 'pending'
    }).execute()
```

#### Updating Download Status
```python
def update_download_status(session_id: str, status_update: dict):
    supabase.table('download_status').update(status_update)\
        .eq('session_id', session_id).execute()
```

#### Recording an Error
```python
def record_error(session_id: str, error_message: str):
    supabase.table('download_status').update({
        'last_error': error_message,
        'last_error_timestamp': datetime.now().isoformat(),
        'retry_count': supabase.raw('retry_count + 1')
    }).eq('session_id', session_id).execute()
```

#### Querying Progress
```python
def get_parliament_progress(parliament_id: str):
    return supabase.table('parliament_progress')\
        .select('*')\
        .eq('parliament_id', parliament_id)\
        .single()\
        .execute()
```

### 3. Status Codes

#### Video/Transcript Status
- `pending`: Not yet started
- `downloading`: Currently in progress
- `completed`: Successfully finished
- `failed`: Failed to download/process

### 4. Best Practices

1. **Error Handling**
   - Always include descriptive error messages
   - Set appropriate status when errors occur
   - Don't forget to update retry_count

2. **Performance**
   - Update download_speed_mbps when possible
   - Include video_duration_seconds for completed downloads
   - Set video_size_bytes for storage tracking

3. **Batch Operations**
   - Use batch inserts for multiple records
   - Keep track of batch_id for related downloads
   - Update status in bulk when possible

4. **Monitoring**
   - Check parliament_progress for overall status
   - Monitor last_error_count for recent issues
   - Review error_history for recurring problems

## Maintenance

### Indexes
The following indexes are maintained for performance:
```sql
create index download_status_parliament_id_idx on download_status(parliament_id);
create index download_status_status_idx on download_status(video_status, transcript_status);
```

### Security
Row Level Security (RLS) is enabled with policies for:
- Read access for authenticated users
- Write access for authenticated users
- No public access

## Troubleshooting

### Common Issues

1. **Missing Updates**
   - Check if triggers are enabled
   - Verify transaction completed successfully
   - Ensure proper status codes are used

2. **Performance Issues**
   - Use provided indexes
   - Batch related operations
   - Monitor query performance

3. **Error History Issues**
   - Ensure last_error_timestamp is set
   - Check JSONB format if manually updating
   - Verify trigger is active

## Support

For issues with:
- Database access: Check Supabase project settings
- Missing data: Review transaction logs
- Performance: Monitor query plans
- Security: Verify RLS policies

## Version History

- v1.0.0 (2024-01-05)
  - Initial schema setup
  - Automatic error history
  - Parliament progress tracking
  - Estimation logic for completion time 