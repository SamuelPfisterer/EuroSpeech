# Batch Storage System Documentation

## Overview

The Batch Storage System is a solution for efficiently storing large numbers of transcripts in a structured way. Instead of creating one file per transcript (which can lead to tens of thousands of small files), this system consolidates transcripts into batch JSON files organized by row ranges and transcript types.

## Key Features

- **Reduced File Count**: Consolidates thousands of individual transcript files into a few batch files
- **Directory Structure Preservation**: Maintains the existing directory structure by storing batch files in appropriate subfolders
- **Meaningful Naming**: Uses row ranges in batch file names for easy identification
- **Content Type Handling**: Properly handles both string and bytes content using base64 encoding
- **Configurable Updates**: Controls how often the JSON file is updated with the `update_frequency` parameter
- **Memory Efficiency**: Only keeps transcripts for the current job in memory
- **Thread Safety**: Uses locks to handle concurrent access within a process

## Implementation Details

### Files Added/Modified

1. **New Files**:
   - `batch_storage.py`: Core implementation of the BatchStorageManager class

2. **Modified Files**:
   - `download_utils.py`: Updated to use BatchStorageManager for transcript storage
   - `main.py`: Added command-line options for batch storage and update frequency
   - `job.sh`: Updated to include batch storage options

### Batch File Structure

Each batch file has this structure:

```json
{
  "metadata": {
    "start_idx": 0,
    "end_idx": 11837,
    "updated_at": "2023-11-26T15:45:00Z",
    "transcript_count": 11837
  },
  "transcripts": {
    "transcript_id_1": {
      "content": {
        "type": "string",
        "data": "The transcript content..."
      },
      "added_at": "2023-11-26T14:35:00Z",
      "url": "https://www.althingi.is/transcript/123",
      "metadata": {
        "original_url": "https://www.althingi.is/transcript/123",
        "file_extension": "html",
        "processed_at": "2023-11-26T14:35:00Z"
      }
    },
    "transcript_id_2": {
      // Another transcript...
    }
  }
}
```

## API Documentation

### BatchStorageManager Class

The `BatchStorageManager` class is the core component of the batch storage system. It manages the storage of transcripts in batch JSON files.

#### Class Methods

##### `get_instance(subfolder_path, start_idx, end_idx, update_frequency=10)`

Get or create a storage instance for the given subfolder.

**Parameters**:
- `subfolder_path` (str): Path to the subfolder for this transcript type
- `start_idx` (int): Starting row index for this process
- `end_idx` (int): Ending row index for this process
- `update_frequency` (int, optional): How often to write to disk (every N transcripts). Default is 10.

**Returns**:
- `BatchStorageManager`: Instance for the specified subfolder

**Example**:
```python
manager = BatchStorageManager.get_instance(
    subfolder_path="/path/to/transcripts/html_transcripts",
    start_idx=0,
    end_idx=1000,
    update_frequency=50
)
```

#### Instance Methods

##### `add_transcript(transcript_id, content, url=None, metadata=None)`

Add a transcript to the batch storage.

**Parameters**:
- `transcript_id` (str): Unique identifier for the transcript
- `content` (str or bytes): The transcript content (HTML, text, or binary data)
- `url` (str, optional): Original URL of the transcript
- `metadata` (dict, optional): Additional metadata about the transcript

**Returns**:
- `bool`: True if successful, False otherwise

**Example**:
```python
success = manager.add_transcript(
    transcript_id="transcript_12345",
    content="<html>Transcript content...</html>",
    url="https://example.com/transcript/12345",
    metadata={
        "speaker": "John Doe",
        "date": "2023-11-26",
        "language": "en"
    }
)
```

##### `get_transcript(transcript_id)`

Retrieve a transcript by its ID.

**Parameters**:
- `transcript_id` (str): Unique identifier for the transcript

**Returns**:
- The transcript content (string or bytes) or None if not found

**Example**:
```python
content = manager.get_transcript("transcript_12345")
if content:
    print(f"Found transcript: {content[:100]}...")
else:
    print("Transcript not found")
```

##### `get_transcript_data(transcript_id)`

Retrieve all data for a transcript by its ID.

**Parameters**:
- `transcript_id` (str): Unique identifier for the transcript

**Returns**:
- Dictionary with all transcript data or None if not found

**Example**:
```python
data = manager.get_transcript_data("transcript_12345")
if data:
    print(f"URL: {data.get('url')}")
    print(f"Added at: {data.get('added_at')}")
    print(f"Content: {data.get('content')[:100]}...")
else:
    print("Transcript not found")
```

##### `cleanup()`

Save any pending changes and clean up resources.

**Example**:
```python
manager.cleanup()
```

## Integration with Download Pipeline

The batch storage system is integrated with the existing download pipeline through the `download_and_process_with_custom_processor` function in `download_utils.py`. This function now accepts additional parameters for batch storage:

```python
def download_and_process_with_custom_processor(
    url: str, 
    output_filename: str,
    processor: TranscriptProcessor,
    file_extension: str,
    batch_storage=False,
    update_frequency=10,
    start_idx=0,
    end_idx=0
) -> bool:
    # ...
```

## Command-Line Options

The batch storage system can be enabled and configured through command-line options in `main.py`:

```
--batch_storage        Enable batch storage for transcripts
--update_frequency N   How often to update batch files (every N transcripts)
```

## Job Script Configuration

The batch storage system can also be enabled and configured in the job script (`job.sh`):

```bash
# Set batch storage options
USE_BATCH_STORAGE=true
UPDATE_FREQUENCY=50
```

## Usage Examples

### Basic Usage

```python
from batch_storage import BatchStorageManager

# Get a manager instance
manager = BatchStorageManager.get_instance(
    subfolder_path="/path/to/transcripts",
    start_idx=0,
    end_idx=1000,
    update_frequency=50
)

# Add a transcript
manager.add_transcript(
    transcript_id="transcript_123",
    content="This is the transcript content",
    url="https://example.com/transcript/123",
    metadata={"language": "en"}
)

# Retrieve a transcript
content = manager.get_transcript("transcript_123")

# Clean up
manager.cleanup()
```

### Enabling Batch Storage in the Pipeline

To enable batch storage in the download pipeline, use the `--batch_storage` flag:

```bash
python download_scripts/main.py \
    --start_idx 0 \
    --end_idx 1000 \
    --csv_file "iceland_links.csv" \
    --batch_storage \
    --update_frequency 50
```

## Technical Details

### Content Type Handling

The batch storage system handles different content types (string and bytes) by encoding them appropriately for JSON storage:

1. **String Content**: Stored directly in the JSON file
2. **Bytes Content**: Encoded as base64 and stored as a string in the JSON file

When retrieving content, the system automatically decodes it back to its original type.

### Thread Safety

The batch storage system uses locks to ensure thread safety when multiple threads access the same batch file:

```python
with self.lock:
    # Thread-safe operations
    # ...
```

### Memory Management

The batch storage system keeps transcripts in memory for the current job, but only loads the batch file once at initialization. This balances memory usage with performance.

### File Updates

The batch storage system writes to disk based on the `update_frequency` parameter:

```python
# Save to file based on update frequency
if self.count % self.update_frequency == 0:
    self._save()
```

This allows you to control how often the JSON file is updated, balancing between performance and data safety.

## Best Practices

1. **Choose an Appropriate Update Frequency**: 
   - Lower values (e.g., 10) provide better data safety but more frequent I/O
   - Higher values (e.g., 100) provide better performance but more data at risk if a crash occurs

2. **Batch Size Considerations**:
   - The batch size (determined by `start_idx` and `end_idx`) affects the size of the JSON file
   - Very large batches may lead to large JSON files that are slower to read/write
   - Very small batches may lead to too many files

3. **Always Call Cleanup**:
   - Always call `cleanup()` at the end to ensure all data is saved

4. **Error Handling**:
   - The batch storage system includes error handling, but you should still handle exceptions when using it

## Limitations and Future Improvements

1. **No Built-in Search**: Currently, there's no built-in way to search across all batch files
2. **No Compression**: The JSON files are not compressed, which could be added for larger datasets
3. **No Automatic Cleanup**: Old or temporary files are not automatically cleaned up
4. **No Indexing**: There's no index file to quickly locate transcripts across batch files 