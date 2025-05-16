# Hugging Face Audio Dataset Upload Plan

This document outlines the plan for processing local audio alignment data and uploading it as a Hugging Face dataset.

## Goal

Create a Hugging Face dataset containing short audio segments (3-20s) extracted from longer recordings, along with associated metadata (transcripts, timings, quality metrics, etc.). The dataset should be organized by country and split into 'train', 'test', 'validation', with 'train' potentially further subsetted for large datasets.

## Chosen Approach: Direct Arrow/Parquet Creation with CSV Manifests

We will bypass the intermediate WebDataset format and directly create Hugging Face `Dataset` objects (backed by Apache Arrow) for batches of data, guided by central CSV manifests. These batches will be pushed incrementally to the Hugging Face Hub using `push_to_hub`, where they will be stored as Parquet files.

**Rationale for Arrow/Parquet:**

1.  **HF Native:** This aligns directly with the `datasets` library's internal format and the format `push_to_hub` expects (Parquet).
2.  **Efficiency:** Avoids creating potentially thousands or millions of intermediate audio/JSON segment files locally. Parquet provides efficient storage and compression on the Hub.
3.  **Simplified Upload:** `push_to_hub` handles conversion to Parquet and optimized sharding automatically.
4.  **Metadata Integration:** Arrow/Parquet is well-suited for storing and querying rich metadata alongside the audio.

**Rationale for CSV Manifest Batching:**

1.  **Scalability:** Essential for handling multi-terabyte datasets that cannot fit into memory.
2.  **Decoupling:** Separates lightweight metadata scanning from heavy audio processing and uploading.
3.  **Memory Management:** Only audio for the current small batch needs to be loaded.
4.  **State Tracking & Resumability:**
    *   The main `[country_name]_manifest.csv` tracks upload progress ('pending', 'uploaded', 'error') per segment.
    *   A new `[country_name]_splits.csv` file tracks the assignment of entire audio files to 'train', 'test', or 'validation' splits and, for 'train' files, the `subset_id` they belong to after being processed. This aids resumability for large train sets.
    *   The unique `key` per segment in the main manifest is critical.

## Local Data Structure

-   Root: `countries/`
-   Per Country: `countries/[country_name]/` (e.g., `countries/germany/`)
    -   Alignment Data: `Alignment/alignment_output/[video_id]_[transcript_id]_aligned.json`

**Alignment JSON Format (`*_aligned.json`):**

```json
{
  "audio_file": "/path/to/long/audio/[video_id].opus",
  "segments": [
    {
      "start": float, // seconds
      "end": float,   // seconds
      "asr_text": "...",
      "human_text": "...",
      "cer": float,
      "start_idx": int, // index in original full transcript
      "end_idx": int    // index in original full transcript
    },
    // ... more segments
  ]
}
```

## Target Hugging Face Dataset Schema

The final dataset pushed to the Hub will have the following features (columns):

```python
from datasets import Features, Value, Audio

# Need to determine the sampling rate from the source audio files
# Assuming 16000 for now, but MUST BE VERIFIED.
AUDIO_SAMPLING_RATE = 16000

features = Features({
    # Audio data, will be handled by the datasets library
    'audio': Audio(sampling_rate=AUDIO_SAMPLING_RATE),
    # Unique identifier for the segment
    'key': Value("string"), # Format: [country]_[video_id]_[start_ms]_[end_ms]
    # Metadata
    'country': Value("string"), # e.g., "germany"
    'language': Value("string"), # e.g., "de" (derived from country)
    'video_id': Value("string"), # ID of the original long audio file
    'transcript_id': Value("string"), # From alignment filename
    'start_seconds': Value("float32"), # Start time within original audio
    'end_seconds': Value("float32"), # End time within original audio
    'duration_seconds': Value("float32"), # Duration of the segment
    'asr_transcript': Value("string"), # Transcript from ASR
    'human_transcript': Value("string"), # Human-verified transcript
    'cer': Value("float32"), # Character Error Rate (from source)
    'wer': Value("float32"), # Word Error Rate (to be calculated)
    'original_transcript_start_idx': Value("int32"), # Start char index in original human transcript
    'original_transcript_end_idx': Value("int32"), # End char index in original human transcript
})
```

## Central Manifest CSV Schema (`[country_name]_manifest.csv`)

This file acts as the master list and progress tracker for individual segments.

Columns:
*   `key`: STRING (Unique ID: `[country]_[video_id]_[start_ms]_[end_ms]`, Primary Key)
*   `country`: STRING
*   `language`: STRING (ISO 639-1 code, e.g., "de")
*   `video_id`: STRING
*   `transcript_id`: STRING
*   `source_audio_path`: STRING (Absolute or relative path to the original large audio file)
*   `start_seconds`: FLOAT
*   `end_seconds`: FLOAT
*   `duration_seconds`: FLOAT
*   `asr_transcript`: STRING
*   `human_transcript`: STRING
*   `cer`: FLOAT
*   `wer`: FLOAT (Calculated)
*   `original_transcript_start_idx`: INTEGER
*   `original_transcript_end_idx`: INTEGER
*   `status`: STRING ('pending', 'processing', 'uploaded', 'error')
*   `error_message`: STRING (Optional: store error details if status is 'error')
*   `batch_id`: INTEGER (Optional, legacy or for other uses)
*   `split`: STRING ('train', 'test', 'validation' - assigned based on `_splits.csv`)

## Split Assignment CSV Schema (`[country_name]_splits.csv`)

This file tracks the assignment of entire source audio files to dataset splits and manages train set subsetting. It is generated by `generate_manifest.py` and updated by `batch_upload.py`.

Columns:
*   `source_audio_path`: STRING (Path to the original large audio file, Primary Key for this file)
*   `video_id`: STRING (Derived from `source_audio_path`)
*   `duration_hours`: FLOAT (Total duration of usable segments from this audio file, in hours)
*   `size_mb`: FLOAT (File size of the source audio file, in megabytes)
*   `split`: STRING ('train', 'test', 'validation' - initial assignment)
*   `subset_id`: INTEGER (Nullable. For 'train' files, this stores the ID of the train subset, e.g., 1 for `train-1`, once processed.)

## Processing Workflow

**Phase 1: Manifest and Split Generation (`generate_manifest.py`)**

1.  **Script:** `generate_manifest.py`.
2.  **Scan:** Iterates through `countries/[country_name]/Alignment/alignment_output/*_aligned.json` files.
3.  **Create/Load `[country_name]_splits.csv`:**
    *   If `_splits.csv` doesn't exist for the country:
        *   Scans all alignment JSONs to find unique `source_audio_path`s.
        *   Calculates total duration (sum of segment durations) and file size (`size_mb`) for each unique `source_audio_path`.
        *   Assigns each `source_audio_path` to 'train', 'test', or 'validation' based on desired duration percentages (e.g., 1% test, 1% validation, rest to train), ensuring entire files belong to one split. This is randomized but seeded for reproducibility.
        *   Saves this information to `[country_name]_splits.csv`.
    *   If `_splits.csv` exists, it's loaded to retain existing split assignments.
4.  **Process Segments for `[country_name]_manifest.csv`:**
    *   For each segment within each JSON file:
        *   Extracts metadata (`start`, `end`, transcripts, `cer`, indices).
        *   Gets `country`, `video_id`, `transcript_id`, `source_audio_path`.
        *   Calculates `duration_seconds`, `wer`.
        *   Determines `language`.
        *   Constructs the unique segment `key`.
        *   Retrieves the `split` assignment for the segment's `source_audio_path` from the loaded/created `_splits.csv`.
        *   Appends a row to `[country_name]_manifest.csv` with all metadata, `split`, and `status='pending'`.
        *   Avoids duplicate `key` entries if the script is run multiple times.

**Phase 2: Batch Upload (`batch_upload.py`)**

1.  **Script:** `batch_upload.py`.
2.  **Setup:**
    *   Installs libraries (`datasets`, `huggingface_hub`, `pydub`, `pandas`, `psutil`).
    *   Login to Hugging Face Hub. Define `repo_id`.
    *   Parses arguments: `--country`, `--manifest-dir`, `--repo-id`, `--max-files` (for train subsets), `--hf-token`, `--max-split-size-gb`, `--ram-percentage-limit`, `--max-cer`.
3.  **Load Data:**
    *   Loads the main `[country_name]_manifest.csv`.
    *   Loads (or initializes columns in) `[country_name]_splits.csv`.
4.  **Process 'Test' Split:**
    *   Identifies all `source_audio_path`s assigned to 'test' in `_splits.csv`.
    *   Gathers all 'pending' segments from `_manifest.csv` corresponding to these test audio files.
    *   Filters segments where `CER > args.max_cer`. Skipped segments are marked as 'error' in `_manifest.csv`.
    *   Processes these segments (loads audio, extracts specified portions).
    *   Pushes the resulting Hugging Face `Dataset` to `repo_id` with `config_name=[country_name]` and `split='test'`.
    *   Updates segment statuses in `_manifest.csv` ('uploaded' or 'error').
5.  **Process 'Validation' Split:**
    *   Same logic as 'Test' split, but for `split='validation'`.
6.  **Process 'Train' Split (Subsetting):**
    *   This is an iterative process to handle potentially very large train sets.
    *   **Loop for Subsets:** Continues as long as there are 'train' files in `_splits.csv` without an assigned `subset_id`.
        *   **Determine Next Subset ID:** Finds the max `subset_id` used so far for the country's train files and increments it (e.g., `train-1`, `train-2`, ...).
        *   **Batch Assembly:**
            *   Identifies 'train' `source_audio_path`s from `_splits.csv` that have `subset_id` as NA.
            *   Calculates memory/size limits for the current batch based on `args.ram_percentage_limit` and `args.max_split_size_gb`.
            *   Iteratively adds these pending train audio files (typically smallest first by `size_mb`) to the current batch if their cumulative estimated size fits the calculated limit.
            *   A pre-flight memory check is done when adding a file to the batch to catch immediate `MemoryError`s. Files causing this are skipped for the *current* batch attempt.
        *   **Segment Processing for Subset:**
            *   Gathers all 'pending' segments from `_manifest.csv` that belong to the audio files selected for the current train subset.
            *   Filters segments where `CER > args.max_cer`.
            *   Processes these segments.
        *   **Push Subset:**
            *   Pushes the resulting Hugging Face `Dataset` to `repo_id` with `config_name=[country_name]` and `split='train-[subset_id]'`.
        *   **Update Statuses:**
            *   Updates segment statuses in `_manifest.csv` ('uploaded' or 'error').
            *   Updates `_splits.csv`: for all `source_audio_path`s included in the *attempted* batch, their `subset_id` is set to the current `subset_id`. This marks them as processed for subsetting.
        *   The loop continues to create the next train subset.
7.  **Resumability:**
    *   Segment-level resumability is handled by the `status` column in `_manifest.csv`.
    *   Train set resumability is handled by the `subset_id` in `_splits.csv`. If the script is stopped, it can identify which train files still need to be processed into subsets.
    *   'Test' and 'Validation' splits are typically processed in full; if interrupted, pending segments will be picked up on the next run.

## TODOs / Open Questions

1.  **Audio Sampling Rate:** **Must** verify/determine the sampling rate of source files. Update `TARGET_AUDIO_SAMPLING_RATE` in `batch_upload.py`.
2.  **Language Mapping:** Finalize country to language codes in `utils.py`.
3.  **Dependencies:** List exact versions in `requirements.txt`.
4.  **Resource Estimation:** While RAM-based batching helps, large individual files might still be an issue if they exceed available RAM or configured limits. The script attempts to handle this by skipping such files for a given batch.

## Required Libraries (Example `requirements.txt`)

```
datasets>=2.10.0
huggingface_hub>=0.10.0
pydub>=0.25.0
jiwer>=2.3.0
pandas>=1.3.0 # Recommended for CSV handling
# ffmpeg needs to be installed separately if not using pydub's bundled ff* executables
```

## Upload Command Structure

```bash
# 0. Ensure ffmpeg is installed and in PATH (if needed by pydub)
# 1. Install Python dependencies: pip install -r requirements.txt
# 2. Create/Update the manifest: python generate_manifest.py --output-csv upload_manifest.csv --countries-dir ./countries
# 3. Log in to Hugging Face: huggingface-cli login
# 4. Run the upload script: python batch_upload.py --manifest-csv upload_manifest.csv --repo-id "your_username/your_dataset_name"
```

## Future: WebDataset Conversion

If needed later, the uploaded Hugging Face dataset (stored as Parquet on the Hub) can be converted to the WebDataset format. This would involve:
1.  Streaming or loading the Hugging Face dataset (e.g., using `load_dataset(..., streaming=True)`).
2.  Iterating through the samples.
3.  For each sample, writing its audio component (e.g., as `.flac` or `.opus`) and its metadata component (as `.json`) into a TAR archive.
4.  Grouping samples into TAR archives based on size (e.g., ~1GB per TAR).
5.  This conversion process is best performed on a cloud platform (like Azure, AWS, GCP) with scalable compute and storage, especially given the dataset size.

## Implementation Plan

**1. Core Modules/Scripts:**

*   `generate_manifest.py`:
    *   Argument parsing (input `countries-dir`, output `manifest-csv`).
    *   Function to scan directories for `*_aligned.json` files.
    *   Function to parse a single JSON file.
    *   Function to process a segment's metadata (calculate WER, determine lang, build key).
    *   Function to safely append/update rows in the CSV manifest (using `pandas` recommended, check for existing key before adding).
    *   Main logic to orchestrate scanning and writing.
*   `batch_upload.py`:
    *   Argument parsing (input `manifest-csv`, `repo-id`, optional HF token).
    *   Function to read/update CSV status safely (atomic updates if possible, or careful locking if running parallel workers).
    *   Function to find the next `source_audio_path` with 'pending' segments.
    *   Function to load audio (using `pydub` or `soundfile`), determine sample rate, handle errors.
    *   Function to extract audio segment, handle errors.
    *   Main loop logic following the "Phase 2: Batch Upload (Source File Focused)" workflow.
    *   `push_to_hub` call with error handling and retries.
    *   Logic to update CSV status based on push success/failure.
*   `utils.py` (Optional): Shared utility functions, e.g.:
    *   Language code mapping (country -> code).
    *   WER calculation wrapper.
    *   Audio sampling rate detection.
    *   Consistent key generation logic.
    *   CSV reading/writing/status update helpers.

**2. Key Functionality to Implement:**

*   **Argument Parsing:** Use `argparse` in both scripts.
*   **Directory Scanning:** Use `pathlib` or `os.walk`.
*   **JSON Parsing:** Use `json` library.
*   **CSV Handling:** Use `pandas` for efficient reading, querying (finding pending paths/rows), and writing/updating.
*   **Audio Loading/Processing:** Use `pydub` (requires ffmpeg) or potentially `soundfile` + `librosa` (for resampling if needed). Ensure consistent sample rate handling.
*   **WER Calculation:** Use `jiwer`. Handle potential empty strings.
*   **HF Interaction:** Use `datasets` (`Dataset.from_list`, `.filter`) and `huggingface_hub` (`push_to_hub`). Handle authentication (token or login).
*   **Error Handling:** Robust `try...except` blocks for file I/O, audio processing, API calls. Log errors clearly.
*   **Status Tracking:** Reliable updates to the CSV 'status' and 'error_message' columns.

**3. Development Steps:**

1.  Set up project structure, virtual environment, install base dependencies (`pandas`, `jiwer`, `datasets`, `huggingface_hub`, `pydub`).
2.  Implement `generate_manifest.py`. Test thoroughly on a subset of data. Verify CSV structure and content.
3.  Implement core audio loading and segment extraction functions (perhaps in `utils.py` or `batch_upload.py`). Test independently.
4.  Implement the main loop logic in `batch_upload.py`, focusing on finding the next source file and identifying its pending segments.
5.  Integrate audio processing into the loop.
6.  Implement the `push_to_hub` call and related logic (grouping by country, constructing commit messages).
7.  Implement the CSV status update logic carefully, especially considering potential errors during processing or push.
8.  Add comprehensive logging.
9.  Test `batch_upload.py` end-to-end on a small test dataset on Hugging Face Hub.
10. Refine error handling, add retries for `push_to_hub`.
11. Consider performance and potential for parallelization (if needed).

# Library Documentation:
## push_to_hub
push_to_hub
<
source
>
( repo_id: strconfig_name: str = 'default'set_default: typing.Optional[bool] = Nonesplit: typing.Optional[str] = Nonedata_dir: typing.Optional[str] = Nonecommit_message: typing.Optional[str] = Nonecommit_description: typing.Optional[str] = Noneprivate: typing.Optional[bool] = Nonetoken: typing.Optional[str] = Nonerevision: typing.Optional[str] = Nonecreate_pr: typing.Optional[bool] = Falsemax_shard_size: typing.Union[str, int, NoneType] = Nonenum_shards: typing.Optional[int] = Noneembed_external_files: bool = True )

Parameters

repo_id (str) — The ID of the repository to push to in the following format: <user>/<dataset_name> or <org>/<dataset_name>. Also accepts <dataset_name>, which will default to the namespace of the logged-in user.
config_name (str, defaults to "default") — The configuration name (or subset) of a dataset. Defaults to "default".
set_default (bool, optional) — Whether to set this configuration as the default one. Otherwise, the default configuration is the one named "default".
split (str, optional) — The name of the split that will be given to that dataset. Defaults to self.split.
data_dir (str, optional) — Directory name that will contain the uploaded data files. Defaults to the config_name if different from "default", else "data".
Added in 2.17.0

commit_message (str, optional) — Message to commit while pushing. Will default to "Upload dataset".
commit_description (str, optional) — Description of the commit that will be created. Additionally, description of the PR if a PR is created (create_pr is True).
Added in 2.16.0

private (bool, optional) — Whether to make the repo private. If None (default), the repo will be public unless the organization's default is private. This value is ignored if the repo already exists.
token (str, optional) — An optional authentication token for the Hugging Face Hub. If no token is passed, will default to the token saved locally when logging in with huggingface-cli login. Will raise an error if no token is passed and the user is not logged-in.
revision (str, optional) — Branch to push the uploaded files to. Defaults to the "main" branch.
Added in 2.15.0

create_pr (bool, optional, defaults to False) — Whether to create a PR with the uploaded files or directly commit.
Added in 2.15.0

max_shard_size (int or str, optional, defaults to "500MB") — The maximum size of the dataset shards to be uploaded to the hub. If expressed as a string, needs to be digits followed by a unit (like "5MB").
num_shards (int, optional) — Number of shards to write. By default, the number of shards depends on max_shard_size.
Added in 2.8.0

embed_external_files (bool, defaults to True) — Whether to embed file bytes in the shards. In particular, this will do the following before the push for the fields of type:
Audio and Image: remove local path information and embed file content in the Parquet files.
Pushes the dataset to the hub as a Parquet dataset. The dataset is pushed using HTTP requests and does not need to have neither git or git-lfs installed.

The resulting Parquet files are self-contained by default. If your dataset contains Image, Audio or Video data, the Parquet files will store the bytes of your images or audio files. You can disable this by setting embed_external_files to False.

Example:

Copied
dataset.push_to_hub("<organization>/<dataset_id>")
dataset_dict.push_to_hub("<organization>/<dataset_id>", private=True)
dataset.push_to_hub("<organization>/<dataset_id>", max_shard_size="1GB")
dataset.push_to_hub("<organization>/<dataset_id>", num_shards=1024)
If your dataset has multiple splits (e.g. train/validation/test):

Copied
train_dataset.push_to_hub("<organization>/<dataset_id>", split="train")
val_dataset.push_to_hub("<organization>/<dataset_id>", split="validation")
# later
dataset = load_dataset("<organization>/<dataset_id>")
train_dataset = dataset["train"]
val_dataset = dataset["validation"]
If you want to add a new configuration (or subset) to a dataset (e.g. if the dataset has multiple tasks/versions/languages):

Copied
english_dataset.push_to_hub("<organization>/<dataset_id>", "en")
french_dataset.push_to_hub("<organization>/<dataset_id>", "fr")
# later
english_dataset = load_dataset("<organization>/<dataset_id>", "en")
french_dataset = load_dataset("<organization>/<dataset_id>", "fr")
