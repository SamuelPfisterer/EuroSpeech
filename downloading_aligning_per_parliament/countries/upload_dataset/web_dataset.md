# Hugging Face Audio Dataset Upload Plan (WebDataset Format)

This document outlines the plan for processing local audio alignment data and uploading it as a Hugging Face dataset in the WebDataset format.

## 1. Goal

Create a Hugging Face dataset in WebDataset format. The dataset will contain short audio segments (3-20s) extracted from longer recordings, along with associated metadata (transcripts, timings, quality metrics, etc.). The dataset should be organized by country and split into 'train', 'test', 'validation', with 'train' potentially further subsetted for large datasets. Each subset/split will consist of multiple TAR archives (shards).

## 2. Chosen Approach: Local WebDataset Shard Creation & Hub Upload

We will adapt the manifest-guided approach from the Parquet-based plan (`dataset_upload.md`). The core difference is that instead of `Dataset.push_to_hub()`, we will:
1.  Locally generate WebDataset TAR archives (shards), where each shard contains multiple audio files and their corresponding metadata files.
2.  Upload these TAR shards directly to a Hugging Face dataset repository.
3.  Utilize central CSV manifests (`[country_name]_manifest.csv` and `[country_name]_splits.csv`) for managing audio segments, their metadata, split assignments, and upload progress.

**Rationale for WebDataset:**
*   **Streaming Efficiency:** WebDataset is designed for sequential I/O and efficient streaming of large datasets, which is beneficial for training large models.
*   **Multimodal Support:** Well-suited for datasets combining audio, images, text, etc.
*   **Community Standard:** A recognized format for large-scale datasets.

**Rationale for CSV Manifest Batching (retained from previous plan):**
*   **Scalability:** Manages multi-terabyte datasets.
*   **Decoupling:** Separates metadata processing from audio processing and TAR creation/upload.
*   **Memory Management:** Processes data in manageable batches.
*   **State Tracking & Resumability:** `_manifest.csv` and `_splits.csv` track progress.

## 3. Local Data Structure (Source)

-   Root: `countries/`
-   Per Country: `countries/[country_name]/`
    -   Alignment Data: `Alignment/alignment_output/[video_id]_[transcript_id]_aligned.json` (as defined in `dataset_upload.md`)

## 4. WebDataset Shard Structure (Target)

Each WebDataset file is a TAR archive. Within each TAR shard:
*   For every audio segment, there will be at least two files:
    *   `[unique_segment_key].flac`: The audio data (or `.opus`, `.mp3`, etc.). FLAC is recommended for lossless compression if storage permits.
    *   `[unique_segment_key].json`: Metadata for the audio segment.
*   The `[unique_segment_key]` will be derived from the `key` column in the `[country_name]_manifest.csv` (e.g., `[country]_[video_id]_[start_ms]_[end_ms]`).
*   The JSON metadata file (`.json`) will contain fields like:
    ```json
    {
      "key": "[unique_segment_key]",
      "country": "germany",
      "language": "de",
      "video_id": "...",
      "transcript_id": "...",
      "start_seconds": 123.45,
      "end_seconds": 128.90,
      "duration_seconds": 5.45,
      "asr_transcript": "...",
      "human_transcript": "...",
      "cer": 0.05,
      "wer": 0.10,
      "original_transcript_start_idx": 100,
      "original_transcript_end_idx": 150,
      // Potentially audio-specific info if not implicitly handled by loader
      // "sampling_rate": 16000
    }
    ```
*   Shards will be named systematically, e.g., `[country_name]-[split_name]-[subset_id_if_train]-[shard_index].tar` (e.g., `germany-train-1-00000.tar`, `germany-test-00000.tar`).
*   Recommended shard size is ~100MB to 1GB.

## 5. Processing Workflow

**Phase 1: Manifest and Split Generation (`generate_manifest.py`)**

*   **Script:** `generate_manifest.py` (largely reusable from the plan in `dataset_upload.md`).
*   **Functionality:**
    *   Scans `countries/[country_name]/Alignment/alignment_output/*_aligned.json` files.
    *   Creates/Loads `[country_name]_splits.csv` to assign entire source audio files to 'train', 'test', or 'validation' splits and manage train set subsetting (assigning `subset_id`).
    *   Populates `[country_name]_manifest.csv` with detailed metadata for each segment, its assigned `split` (from `_splits.csv`), and an initial `status='pending_local_tar'`. This status indicates segments are ready for local WebDataset TAR shard creation.
    *   Calculates WER, duration, language, and the unique segment `key`.
    *   Avoids duplicate `key` entries.

**Phase 2: Local WebDataset Shard Creation (`create_local_webdataset_shards.py`)**

This script focuses *only* on creating WebDataset TAR files locally. Hugging Face Hub upload logic will be handled by a separate script or an extension of this one later.

*   **Script:** `create_local_webdataset_shards.py`.
*   **Setup:**
    *   Installs libraries: `pydub`, `pandas`, `tarfile`.
    *   Parses arguments:
        *   `--country`
        *   `--manifest-dir` (input, where `_manifest.csv` and `_splits.csv` are)
        *   `--output-dir` (output, where local TAR shards will be saved)
        *   `--max-videos N` (optional, for testing: process segments from at most N video_ids)
        *   `--max-shard-size-gb`
        *   `--max-cer`
        *   `--audio-format` (e.g., flac, opus)
*   **Load Data:**
    *   Loads `[country_name]_manifest.csv` and `[country_name]_splits.csv`.
*   **Identify Target Segments:**
    *   Filter `_manifest.csv` for segments with `status='pending_local_tar'`.
    *   If `--max-videos N` is provided:
        *   Identify unique `video_id`s from the 'pending_local_tar' segments.
        *   Select the first `N` (or fewer, if not enough) unique `video_id`s.
        *   Further filter the 'pending_local_tar' segments to include only those belonging to the selected `video_id`s.
*   **Iterate through Splits and Subsets (for the target segments):**
    *   Process 'test' split.
    *   Process 'validation' split.
    *   Process 'train' split iteratively by `subset_id` (e.g., 'train-1', 'train-2', ...), using only the target segments.
*   **For each split/subset:**
    *   **Batching for Shards:**
        *   Group the current split/subset's pending segments into batches. Each batch will form one TAR shard, aiming for `args.max_shard_size_gb`.
        *   Maintain a shard index (e.g., 00000, 00001, ...) for naming.
    *   **For each batch (i.e., for each local shard to be created):**
        *   **Determine Shard Path:**
            *   Shard name: `[country_name]-[split_name]-[subset_id_if_train]-[shard_index].tar`
            *   Local path: `[args.output_dir]/[country_name]/[split_name_with_subset]/[shard_name].tar` (e.g., `local_wds_output/germany/train-1/germany-train-1-00000.tar`). Ensure parent directories are created.
        *   **Create TAR Archive:** Initialize a new temporary `.tar` file.
        *   A list, `segments_in_this_shard`, will store metadata of segments successfully added to this shard.
        *   **Process Segments for Shard:**
            *   For each segment in the current batch:
                *   If `CER > args.max_cer`, mark its status in the main manifest (in memory) as `error_local_tar_cer` and record the error, then skip.
                *   Attempt to:
                    *   **Extract Audio:** Use `pydub` to load source audio, extract segment, convert to `args.audio_format`.
                    *   **Create Metadata JSON:** Prepare the JSON content.
                    *   **Add to TAR:** Add the audio file (e.g., `[segment_key].[audio_format]`) and metadata file (`[segment_key].json`) to the temporary TAR.
                    *   If successful, add segment's identifier and original manifest row index to `segments_in_this_shard`.
                *   If any step fails, mark status as `error_local_tar_processing` in manifest (in memory) with error details, and skip adding to TAR.
        *   **Finalize and Save Shard:**
            *   Close the temporary TAR archive.
            *   Move/rename the temporary TAR to its final local path. This helps ensure partially written shards aren't mistaken for complete ones if a crash occurs during the move.
        *   **Update Statuses in CSV:**
            *   For all segments successfully added to this shard (those in `segments_in_this_shard`), update their status in the main manifest (in memory) to `completed_local_tar`.
            *   Periodically (e.g., after each shard is written) or at the end of the script, save the updated `[country_name]_manifest.csv` to disk to persist status changes.
*   **Resumability:**
    *   The primary mechanism for resumability is the `status` column in `[country_name]_manifest.csv`.
    *   When the script restarts, it reads the manifest and processes segments still marked `pending_local_tar`.
    *   Segments that were part of a shard that failed to write (or whose statuses weren't updated before a crash) will remain `pending_local_tar` and be re-processed.
    *   Statuses: `pending_local_tar`, `completed_local_tar`, `error_local_tar_cer`, `error_local_tar_processing`.

## 6. Hugging Face Hub Interaction Details

**This section will be relevant for a future script/step that handles uploading the locally created TAR shards.** For now, `create_local_webdataset_shards.py` does not interact with the Hugging Face Hub.

*   **Repository Creation:** (Manual step for later)
*   **Authentication:** (Needed for upload script)
*   **File Upload:** (Logic for upload script, using `huggingface_hub.upload_file`)

## 7. Key Considerations and TODOs

1.  **Audio Format & Compression:** Decide on the audio format within TARs (e.g., `.flac`, `.opus`). This affects quality and size. This is now an argument (`--audio-format`).
2.  **Audio Sampling Rate:** Ensure consistency. Store it in metadata if it can vary, or standardize during segment extraction. `TARGET_AUDIO_SAMPLING_RATE` should be a parameter for audio extraction.
3.  **Error Handling:** Robust `try...except` for file I/O, audio processing, TAR creation. Errors should update segment status in the manifest to `error_local_tar_...` with a message.
4.  **Resource Management:** Monitor memory and disk usage during shard creation, especially when handling many segments for a large shard.
5.  **`hf_hub_url` vs `snapshot_download`:** (Relevant for consumption, not current script)
6.  **Dynamic Shard List for Consumers:** (Relevant for consumption, not current script)
7.  **Dependencies:** `tarfile` (Python standard), `pydub` (and its dependency `ffmpeg`), `pandas`. Ensure `jiwer` is listed for `generate_manifest.py` if WER is calculated there. Add to `requirements.txt`.
8.  **Manifest Integrity:** Ensure that writing updated statuses back to the manifest CSV is done robustly (e.g., write to a temporary file then replace, or use pandas' `to_csv`).
9.  **Output Directory Structure:** The script should create the necessary subdirectories within the `--output-dir` (e.g., `[output_dir]/[country]/[split]/`).

## 8. Command Structure (Example for Local Creation)

```bash
# 0. Ensure ffmpeg is installed (if pydub needs it and it's not bundled)
# 1. pip install -r requirements.txt
# (Assuming generate_manifest.py has been run and manifests exist with 'pending_local_tar' status)
# 2. python create_local_webdataset_shards.py \
#       --manifest-dir ./manifests \
#       --output-dir ./local_webdataset_output \
#       --country germany \
#       --audio-format flac \
#       --max-shard-size-gb 0.5 \
#       --max-cer 0.3 \
#       --max-videos 10 # Optional: for testing with a small number of videos
```

This plan provides a comprehensive approach to creating and uploading your audio data in the WebDataset format to the Hugging Face Hub.
The immediate focus for `create_local_webdataset_shards.py` is local TAR shard generation with robust resumability and testability.
