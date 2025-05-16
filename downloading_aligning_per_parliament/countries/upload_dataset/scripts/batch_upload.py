"""Processes the upload_manifest.csv, extracts audio segments,
and uploads them to Hugging Face Hub in batches based on source audio files,
taking into account train/test/validation splits and RAM limits for train subsets.

Phase 2 of the upload process.
"""

import argparse
import pandas as pd
import time
import logging
from pathlib import Path
from tqdm import tqdm
from pydub import AudioSegment
from pydub.exceptions import CouldntDecodeError
from datasets import Dataset, Features, Value, Audio
from huggingface_hub import HfApi, HfFolder
from dotenv import load_dotenv
import os
import psutil # For checking RAM

load_dotenv("/itet-stor/spfisterer/net_scratch/Alignment/testing/own_pipeline/.env")

# Assuming utils.py is in the same directory
import utils

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Constants ---
# Define the target sampling rate for the HF dataset.
TARGET_AUDIO_SAMPLING_RATE = 16000
# Define the HF Dataset features - MUST match dataset_upload.md
DATASET_FEATURES = Features({
    'audio': Audio(sampling_rate=TARGET_AUDIO_SAMPLING_RATE),
    'key': Value("string"),
    'country': Value("string"),
    'language': Value("string"),
    'video_id': Value("string"),
    'transcript_id': Value("string"),
    'start_seconds': Value("float32"),
    'end_seconds': Value("float32"),
    'duration_seconds': Value("float32"),
    'asr_transcript': Value("string"),
    'human_transcript': Value("string"),
    'cer': Value("float32"),
    'wer': Value("float32"),
    'original_transcript_start_idx': Value("int32"),
    'original_transcript_end_idx': Value("int32"),
})
PUSH_RETRIES = 3
PUSH_RETRY_DELAY = 5 # seconds
DEFAULT_RAM_PERCENTAGE_LIMIT = 70 # Default RAM percentage to use for train subset batching
DEFAULT_MAX_CER = 0.30 # Default maximum CER for segments to be included

# --- CSV Handling Functions ---

def load_manifest(manifest_dir, target_country):
    """Load the specific manifest CSV for the target country."""
    if not target_country:
        logging.error("Target country must be specified for loading manifest.")
        return None
    csv_path = Path(manifest_dir) / f"{target_country.lower()}_manifest.csv"

    if not csv_path.exists():
        logging.error(f"Manifest file not found for country {target_country}: {csv_path}")
        return None
    try:
        df = pd.read_csv(csv_path, keep_default_na=False)
        required_cols = ['status', 'source_audio_path', 'key', 'country', 'split'] # Added 'split'
        if not all(col in df.columns for col in required_cols):
            logging.error(f"Manifest {csv_path} missing one or more required columns: {required_cols}.")
            return None

        if not df.empty and not (df['country'].str.lower() == target_country.lower()).all():
             logging.warning(f"Manifest {csv_path} contains rows with mismatched country names.")

        logging.info(f"Loaded manifest for country '{target_country}' from {csv_path} ({len(df)} rows).")
        return df
    except Exception as e:
        logging.error(f"Error loading manifest {csv_path}: {e}")
        return None

def load_or_initialize_splits_csv(manifest_dir, country_name):
    """Loads the [country_name]_splits.csv file. Initializes 'subset_id' if not present."""
    splits_csv_path = Path(manifest_dir) / f"{country_name.lower()}_splits.csv"
    if not splits_csv_path.exists():
        logging.error(f"Splits CSV file not found: {splits_csv_path}. Please generate it first using generate_manifest.py.")
        return None
    try:
        splits_df = pd.read_csv(splits_csv_path)
        if 'subset_id' not in splits_df.columns:
            splits_df['subset_id'] = pd.NA # Use pandas NA for nullable integers
        # Ensure subset_id is treated as a nullable integer
        splits_df['subset_id'] = splits_df['subset_id'].astype(pd.Int64Dtype())
        if 'size_mb' not in splits_df.columns: # Ensure size_mb exists, might be missing if old splits file
            logging.warning(f"'size_mb' column missing in {splits_csv_path}. Train subset batching might be less accurate.")
            splits_df['size_mb'] = 0.0 # Add a default if missing

        logging.info(f"Loaded splits data from {splits_csv_path} ({len(splits_df)} files).")
        return splits_df
    except Exception as e:
        logging.error(f"Error loading or initializing splits CSV {splits_csv_path}: {e}")
        return None

def save_splits_csv(splits_df, manifest_dir, country_name):
    """Saves the _splits.csv DataFrame."""
    splits_csv_path = Path(manifest_dir) / f"{country_name.lower()}_splits.csv"
    try:
        splits_df.to_csv(splits_csv_path, index=False)
        logging.debug(f"Saved updated splits data to {splits_csv_path}")
        return True
    except Exception as e:
        logging.error(f"Error saving splits CSV {splits_csv_path}: {e}")
        return False

# update_manifest_file (from original, uses utils.update_manifest_statuses)
def update_manifest_file(csv_path, status_updates):
    """Update the status of specific rows in the specified country CSV file."""
    if not status_updates:
        return True # No updates needed
    return utils.update_manifest_statuses(csv_path, status_updates)


# --- Audio Processing ---

def process_audio_files_for_batch(
    audio_file_paths, # List of source_audio_path for this batch
    segments_df,      # DataFrame of all segments for these audio_file_paths
    loaded_audio_cache, # Cache for loaded AudioSegment objects for this batch
    max_cer # Maximum allowed CER
    ):
    """
    Processes a list of audio files and extracts their specified segments.
    Filters segments based on max_cer.
    Manages loading audio files, utilizing the provided cache.
    Returns a list of records for HF dataset, processed_keys (set), failed_keys_dict (key: error_message).
    Re-raises MemoryError if encountered during audio loading.
    """
    batch_records = []
    batch_processed_keys = set()
    batch_failed_keys_dict = {}

    for source_path_str in tqdm(audio_file_paths, desc="Processing batch files", leave=False, unit="file"):
        if source_path_str not in loaded_audio_cache: # Check if already loaded for this batch
            source_path_obj = Path(source_path_str)
            if not source_path_obj.is_file():
                logging.error(f"Audio file not found: {source_path_str}")
                for key in segments_df[segments_df['source_audio_path'] == source_path_str]['key']:
                    batch_failed_keys_dict[key] = "Source audio file not found"
                continue
            try:
                logging.debug(f"Attempting to load audio source for batch: {source_path_str}")
                # Debug: Check pydub's ffmpeg/avconv path
                if not hasattr(process_audio_files_for_batch, '_converter_logged'):
                    logging.debug(f"Pydub default converter: {AudioSegment.converter}")
                    process_audio_files_for_batch._converter_logged = True # Log only once

                # Debug: Check file size before attempting to load
                try:
                    file_size = source_path_obj.stat().st_size
                    logging.debug(f"File size for {source_path_str}: {file_size} bytes")
                    if file_size == 0:
                        logging.error(f"File {source_path_str} is 0 bytes. Cannot decode.")
                        for key in segments_df[segments_df['source_audio_path'] == source_path_str]['key']:
                            batch_failed_keys_dict[key] = "Audio file is 0 bytes"
                        continue
                except Exception as e_stat:
                    logging.warning(f"Could not get file stats for {source_path_str}: {e_stat}")

                full_audio = AudioSegment.from_file(source_path_obj)
                actual_sample_rate = full_audio.frame_rate
                if actual_sample_rate != TARGET_AUDIO_SAMPLING_RATE:
                    logging.warning(f"Resampling {source_path_str} from {actual_sample_rate}Hz to {TARGET_AUDIO_SAMPLING_RATE}Hz.")
                    full_audio = full_audio.set_frame_rate(TARGET_AUDIO_SAMPLING_RATE)
                    actual_sample_rate = TARGET_AUDIO_SAMPLING_RATE
                loaded_audio_cache[source_path_str] = (full_audio, actual_sample_rate)
            except MemoryError:
                logging.error(f"MemoryError loading audio file: {source_path_str}. This file will be skipped.")
                for key in segments_df[segments_df['source_audio_path'] == source_path_str]['key']:
                    batch_failed_keys_dict[key] = "MemoryError during audio load"
                if source_path_str in loaded_audio_cache: del loaded_audio_cache[source_path_str]
                raise # Re-raise to be handled by the batching logic
            except CouldntDecodeError as cde:
                logging.error(f"Could not decode audio file: {source_path_str}. Pydub error: {cde}")
                logging.error("This often means the file is corrupted, not a valid Opus file, or there's an issue with FFmpeg/Libav setup (not found, or lacks Opus support).")
                for key in segments_df[segments_df['source_audio_path'] == source_path_str]['key']:
                     batch_failed_keys_dict[key] = f"Could not decode audio file: {cde}"
                continue
            except Exception as e:
                logging.error(f"Error loading audio {source_path_str}: {e}")
                for key in segments_df[segments_df['source_audio_path'] == source_path_str]['key']:
                    batch_failed_keys_dict[key] = f"Error loading audio: {e}"
                continue
        
        if source_path_str not in loaded_audio_cache: # Should be loaded unless error
            continue

        full_audio, actual_sample_rate = loaded_audio_cache[source_path_str]
        current_file_segments_df = segments_df[segments_df['source_audio_path'] == source_path_str]

        for _, row in current_file_segments_df.iterrows():
            key = row['key']
            start_s, end_s = float(row['start_seconds']), float(row['end_seconds'])
            start_ms, end_ms = int(start_s * 1000), int(end_s * 1000)

            # CER Filtering
            current_cer = row.get('cer') # Use .get() for safety, though manifest should have it
            if pd.notna(current_cer) and float(current_cer) > max_cer:
                logging.debug(f"Segment {key} skipped, CER {current_cer:.2f} > {max_cer:.2f}")
                batch_failed_keys_dict[key] = f"CER too high: {current_cer:.2f} > {max_cer:.2f}"
                continue # Skip this segment

            try:
                segment_audio = full_audio[start_ms:end_ms]
                audio_bytes = segment_audio.export(format="opus").read()

                wer_val = row['wer']; cer_val = row['cer']
                record = {
                    'audio': {'bytes': audio_bytes, 'path': None, 'sampling_rate': actual_sample_rate},
                    'key': str(key), 'country': str(row['country']), 'language': str(row['language']),
                    'video_id': str(row['video_id']), 'transcript_id': str(row['transcript_id']),
                    'start_seconds': start_s, 'end_seconds': end_s,
                    'duration_seconds': float(row['duration_seconds']),
                    'asr_transcript': str(row['asr_transcript']), 'human_transcript': str(row['human_transcript']),
                    'cer': float(cer_val) if pd.notna(cer_val) else None,
                    'wer': float(wer_val) if pd.notna(wer_val) else None,
                    'original_transcript_start_idx': int(row['original_transcript_start_idx']),
                    'original_transcript_end_idx': int(row['original_transcript_end_idx']),
                }
                batch_records.append(record)
                batch_processed_keys.add(key)
            except Exception as e:
                logging.error(f"Error processing segment {key} from {source_path_str}: {e}")
                batch_failed_keys_dict[key] = f"Error extracting/processing segment: {e}"
    
    return batch_records, batch_processed_keys, batch_failed_keys_dict


# --- Hugging Face Hub Interaction ---
def push_to_hub_with_retries(dataset, repo_id, config_name, split, commit_message, token):
    """Push dataset to Hub with retry mechanism."""
    for attempt in range(PUSH_RETRIES):
        try:
            logging.info(f"Attempt {attempt + 1}/{PUSH_RETRIES} pushing {len(dataset)} records to {repo_id} (config={config_name}, split={split}) ...")
            dataset.push_to_hub(
                repo_id=repo_id, config_name=config_name, split=split,
                commit_message=commit_message, token=token
            )
            logging.info(f"Push successful for config={config_name}, split={split}.")
            return True
        except Exception as e:
            logging.error(f"Error on push attempt {attempt + 1} for {config_name}/{split}: {e}")
            if attempt < PUSH_RETRIES - 1:
                logging.info(f"Retrying push in {PUSH_RETRY_DELAY} seconds...")
                time.sleep(PUSH_RETRY_DELAY)
            else:
                logging.error(f"Push failed after {PUSH_RETRIES} attempts for {config_name}/{split}.")
                return False
    return False

def process_and_push_batch(
    segment_batch_df, # DataFrame of segments to process and push for this batch
    source_audio_paths_in_batch, # List of unique source_audio_path in this batch
    repo_id,
    country_config_name,
    hf_split_name, # e.g., "test", "validation", "train-1"
    hf_token,
    manifest_path, # Path to the main country_manifest.csv
    loaded_audio_cache, # Pass cache here
    max_cer # Pass max_cer for filtering
    ):
    """Processes a batch of segments and pushes them to the Hugging Face Hub."""
    if segment_batch_df.empty:
        logging.info(f"No segments to process for {country_config_name} -> {hf_split_name}.")
        return True, set()

    logging.info(f"Processing {len(segment_batch_df)} segments from {len(source_audio_paths_in_batch)} audio files for {country_config_name} -> {hf_split_name}...")

    records, processed_keys, failed_keys_dict = [], set(), {}
    try:
        records, processed_keys, failed_keys_dict = process_audio_files_for_batch(
            source_audio_paths_in_batch, segment_batch_df, loaded_audio_cache, max_cer
        )
    except MemoryError: # This batch attempt failed due to a file that couldn't be loaded.
        logging.error(f"MemoryError during batch audio processing for {hf_split_name}. "
                      "The file causing this will be skipped for this batch attempt. "
                      "Any prior successfully loaded files in this batch won't be processed now.")
        # The failed_keys_dict from process_audio_files_for_batch for the problematic file is preserved.
        # All other files in source_audio_paths_in_batch that were not yet processed are effectively skipped for this push.
        # The calling function (process_train_subsets) needs to handle this by not adding the problematic file next time.
        # For now, we proceed to update manifest for the keys that failed due to MemoryError.
        # No push will happen for this batch.
        if failed_keys_dict: # Should contain the memory error entry
             update_manifest_file(manifest_path, {k: ('error', v) for k,v in failed_keys_dict.items()})
        return True, set() # Return True as manifest updated, but no keys pushed.

    push_successful_keys = set()
    push_failed_update_dict = {}

    if records:
        try:
            batch_dataset = Dataset.from_list(records, features=DATASET_FEATURES)
            keys_in_push_attempt = batch_dataset['key']
            
            if keys_in_push_attempt:
                first_key, last_key = keys_in_push_attempt[0], keys_in_push_attempt[-1]
                commit_msg = f"Add {hf_split_name} for {country_config_name} (keys {first_key}..{last_key})"
                
                if push_to_hub_with_retries(batch_dataset, repo_id, country_config_name, hf_split_name, commit_msg, hf_token):
                    push_successful_keys.update(keys_in_push_attempt)
                else:
                    for k in keys_in_push_attempt: push_failed_update_dict[k] = "Failed during Hugging Face Hub upload"
            else:
                 logging.warning(f"Dataset for {hf_split_name} created but key list empty. Skipping push.")
        except Exception as e:
            logging.error(f"Error creating or pushing dataset for {hf_split_name}: {e}")
            for k_proc in processed_keys: push_failed_update_dict[k_proc] = f"Error creating/pushing dataset: {e}"
    else:
        logging.info(f"No records successfully extracted for {hf_split_name}. Nothing to push.")

    status_updates = {}
    for key, reason in failed_keys_dict.items(): status_updates[key] = ('error', reason)
    for key, reason in push_failed_update_dict.items():
        if key not in status_updates: status_updates[key] = ('error', reason)
    for key in push_successful_keys:
        if key not in status_updates: status_updates[key] = ('uploaded', None)
    
    if status_updates:
        if not update_manifest_file(manifest_path, status_updates): # Uses utils.update_manifest_statuses
            logging.error(f"CRITICAL: Failed to update manifest file {manifest_path} for {hf_split_name}. Halting.")
            return False, push_successful_keys
    
    return True, push_successful_keys

# --- Main Logic ---

def process_fixed_split(
    main_manifest_df,
    splits_df,
    country_config_name,
    split_to_process, # 'test' or 'validation'
    args,
    hf_token
    ):
    """Processes and uploads a fixed split ('test' or 'validation')."""
    logging.info(f"\n--- Processing '{split_to_process}' split for country: {country_config_name} ---")
    manifest_path = Path(args.manifest_dir) / f"{country_config_name}_manifest.csv"

    split_audio_paths = splits_df[splits_df['split'] == split_to_process]['source_audio_path'].tolist()
    if not split_audio_paths:
        logging.info(f"No audio files assigned to '{split_to_process}' split for {country_config_name}.")
        return True # Success, nothing to do.

    pending_segments_df = main_manifest_df[
        (main_manifest_df['source_audio_path'].isin(split_audio_paths)) &
        (main_manifest_df['status'].astype(str) == 'pending')
    ].copy()

    if pending_segments_df.empty:
        all_segments_df = main_manifest_df[main_manifest_df['source_audio_path'].isin(split_audio_paths)]
        if not all_segments_df.empty and (all_segments_df['status'] == 'uploaded').all():
            logging.info(f"All segments for '{split_to_process}' split already 'uploaded'. Skipping.")
        else:
            logging.info(f"No PENDING segments for '{split_to_process}' split for {country_config_name}.")
        return True

    loaded_audio_cache_fixed_split = {} 
    success, _ = process_and_push_batch(
        pending_segments_df,
        list(pending_segments_df['source_audio_path'].unique()),
        args.repo_id, country_config_name, split_to_process, hf_token,
        manifest_path, loaded_audio_cache_fixed_split, args.max_cer
    )
    del loaded_audio_cache_fixed_split
    logging.info(f"--- Finished '{split_to_process}' split for country: {country_config_name} ---")
    return success


def process_train_subsets(
    main_manifest_df, # Passed as initial state, reloaded inside if needed
    splits_df, # This df will be modified with subset_id and saved
    country_config_name,
    args,
    hf_token
    ):
    logging.info(f"\n--- Processing 'train' subsets for country: {country_config_name} ---")
    manifest_path = Path(args.manifest_dir) / f"{country_config_name}_manifest.csv"

    available_ram_mb = psutil.virtual_memory().available / (1024 * 1024)
    ram_limit_mb = (available_ram_mb * (args.ram_percentage_limit / 100.0))
    logging.info(f"Available RAM: {available_ram_mb:.2f} MB. Using {args.ram_percentage_limit}%: {ram_limit_mb:.2f} MB limit.")

    effective_batch_limit_mb = ram_limit_mb
    if args.max_split_size_gb:
        max_split_limit_mb = args.max_split_size_gb * 1024
        effective_batch_limit_mb = min(ram_limit_mb, max_split_limit_mb)
        logging.info(f"Max split size arg: {args.max_split_size_gb} GB ({max_split_limit_mb:.2f} MB). Effective batch limit: {effective_batch_limit_mb:.2f} MB.")
    
    audio_files_processed_this_run = 0 # For --max-files
    
    while True:
        # Reload main_manifest_df at the start of each subset attempt to get latest statuses
        current_main_manifest_df = load_manifest(args.manifest_dir, country_config_name)
        if current_main_manifest_df is None:
            logging.error("Failed to reload main manifest during train processing. Exiting train subsetting.")
            return False # Indicate failure


        pending_train_files_info_df = splits_df[
            (splits_df['split'] == 'train') &
            (splits_df['subset_id'].isna())
        ].copy()

        if pending_train_files_info_df.empty:
            logging.info(f"No more 'train' files needing subset assignment for {country_config_name}.")
            break
        
        max_existing_subset_id = splits_df[splits_df['split'] == 'train']['subset_id'].max()
        next_subset_id = 1 if pd.isna(max_existing_subset_id) else int(max_existing_subset_id) + 1
        hf_train_split_name = f"train-{next_subset_id}"
        logging.info(f"\nAttempting to build subset: {hf_train_split_name}")

        current_batch_audio_paths = []
        current_batch_size_mb = 0
        loaded_audio_cache_this_subset = {} # For current subset construction and processing
        
        # Sort by size_mb (smaller first) to try and pack more files
        pending_train_files_info_df = pending_train_files_info_df.sort_values(by='size_mb', ascending=True)
        files_skipped_this_subset_attempt_due_to_mem = set()

        for _, row in pending_train_files_info_df.iterrows():
            file_path = row['source_audio_path']
            file_size_mb = row['size_mb'] if pd.notna(row['size_mb']) else 0.0

            if current_batch_size_mb + file_size_mb <= effective_batch_limit_mb:
                try:
                    logging.debug(f"Pre-flight check for {Path(file_path).name} ({file_size_mb:.2f}MB)")
                    # Try to load into the subset's cache
                    # This mirrors the loading logic in process_audio_files_for_batch
                    temp_audio = AudioSegment.from_file(Path(file_path))
                    actual_rate = temp_audio.frame_rate
                    if actual_rate != TARGET_AUDIO_SAMPLING_RATE:
                        temp_audio = temp_audio.set_frame_rate(TARGET_AUDIO_SAMPLING_RATE)
                    loaded_audio_cache_this_subset[file_path] = (temp_audio, TARGET_AUDIO_SAMPLING_RATE)
                    # No del temp_audio, it's now in cache for this subset if successful

                    current_batch_audio_paths.append(file_path)
                    current_batch_size_mb += file_size_mb
                    logging.debug(f"Added {Path(file_path).name} to {hf_train_split_name}. Batch size: {current_batch_size_mb:.2f}MB / {effective_batch_limit_mb:.2f}MB")
                except MemoryError:
                    logging.warning(f"MemoryError pre-loading {Path(file_path).name} for {hf_train_split_name}. Skipping for THIS subset.")
                    if file_path in loaded_audio_cache_this_subset: del loaded_audio_cache_this_subset[file_path] # cleanup partial
                    files_skipped_this_subset_attempt_due_to_mem.add(file_path)
                    continue 
                except Exception as e:
                    logging.error(f"Error pre-loading {Path(file_path).name}: {e}. Marking its segments as error in manifest.")
                    error_keys = current_main_manifest_df[current_main_manifest_df['source_audio_path'] == file_path]['key'].tolist()
                    status_updates = {k: ('error', f"Pre-load failed: {e}") for k in error_keys}
                    if status_updates: update_manifest_file(manifest_path, status_updates)
                    
                    splits_df.loc[splits_df['source_audio_path'] == file_path, 'subset_id'] = -99 # Mark as errored pre-load
                    save_splits_csv(splits_df, args.manifest_dir, country_config_name) # Save immediately
                    if file_path in loaded_audio_cache_this_subset: del loaded_audio_cache_this_subset[file_path]
                    continue
            else:
                logging.debug(f"{Path(file_path).name} ({file_size_mb:.2f}MB) won't fit current batch. Batch full or file too large.")
                break 

        if not current_batch_audio_paths:
            if not pending_train_files_info_df.empty and not files_skipped_this_subset_attempt_due_to_mem:
                 # This case implies files are available but none fit (e.g., smallest is > limit)
                 # or all remaining files had non-memory pre-load errors and were marked -99.
                smallest_pending_file = pending_train_files_info_df.iloc[0]
                logging.warning(f"No audio files could be added to subset {hf_train_split_name}. "
                                f"Smallest remaining file {Path(smallest_pending_file['source_audio_path']).name} "
                                f"({smallest_pending_file['size_mb']:.2f}MB) "
                                f"may be too large for limit {effective_batch_limit_mb:.2f}MB, or all had errors.")
                # If the only remaining files are those that consistently cause MemoryError, this might loop.
                # However, files causing MemoryError are skipped for the *current* batch attempt,
                # allowing smaller files to potentially form a batch. If only large MemoryError files remain,
                # this `if not current_batch_audio_paths:` block will be hit.
                # Consider marking such a file as unprocessable if it's the *only* one left and consistently fails.
                if len(pending_train_files_info_df) == 1 and smallest_pending_file['source_audio_path'] in files_skipped_this_subset_attempt_due_to_mem :
                     logging.error(f"The single remaining file {Path(smallest_pending_file['source_audio_path']).name} "
                                   f"repeatedly causes MemoryError. Marking as permanently skipped for subsetting.")
                     splits_df.loc[splits_df['source_audio_path'] == smallest_pending_file['source_audio_path'], 'subset_id'] = -100 # Perm skip for mem err
                     save_splits_csv(splits_df, args.manifest_dir, country_config_name)
                     continue # Re-evaluate next iter

            logging.info(f"No audio files selected for current train subset {hf_train_split_name}. Ending train processing for {country_config_name}.")
            break

        segments_for_subset_df = current_main_manifest_df[
            (current_main_manifest_df['source_audio_path'].isin(current_batch_audio_paths)) &
            (current_main_manifest_df['status'].astype(str) == 'pending')
        ].copy()

        if segments_for_subset_df.empty:
            logging.info(f"No PENDING segments for the selected audio files in {hf_train_split_name}. Marking files as processed for subsetting.")
            for f_path in current_batch_audio_paths:
                splits_df.loc[splits_df['source_audio_path'] == f_path, 'subset_id'] = next_subset_id
            save_splits_csv(splits_df, args.manifest_dir, country_config_name)
            audio_files_processed_this_run += len(current_batch_audio_paths)
            del loaded_audio_cache_this_subset # clear cache
            continue 

        push_op_success, pushed_segment_keys = process_and_push_batch(
            segments_for_subset_df, current_batch_audio_paths,
            args.repo_id, country_config_name, hf_train_split_name, hf_token,
            manifest_path, loaded_audio_cache_this_subset, args.max_cer
        )
        
        del loaded_audio_cache_this_subset # Crucial to release memory for next subset

        if not push_op_success: # Critical manifest update failure from push_op
             logging.error(f"Train subset {hf_train_split_name} failed critically. Halting.")
             return False

        # If push_op_success (manifest was updated, even if some segments failed push or extraction)
        # update subset_id for files that were part of this ATTEMPTED batch
        for f_path in current_batch_audio_paths: # All files intended for this batch
            splits_df.loc[splits_df['source_audio_path'] == f_path, 'subset_id'] = next_subset_id
        if not save_splits_csv(splits_df, args.manifest_dir, country_config_name):
            logging.error(f"CRITICAL: Failed to save splits_df after {hf_train_split_name}. Halting.")
            return False
        logging.info(f"Marked {len(current_batch_audio_paths)} audio files with subset_id {next_subset_id}.")

        audio_files_processed_this_run += len(current_batch_audio_paths)
        if args.max_files and audio_files_processed_this_run >= args.max_files:
            logging.info(f"Processed {audio_files_processed_this_run} train audio files, reaching max-files limit of {args.max_files}.")
            break
    
    logging.info(f"--- Finished 'train' subset processing for country: {country_config_name} ---")
    return True


def main():
    parser = argparse.ArgumentParser(description="Upload dataset batches for a specific country based on its manifest and splits.")
    parser.add_argument("--manifest-dir", default="/itet-stor/spfisterer/net_scratch/Downloading/countries/upload_dataset/manifests", help="Directory containing the per-country manifest CSV files.")
    parser.add_argument("--country", required=True, help="Process only segments/files for this country (e.g., 'germany').")
    parser.add_argument("--repo-id", default="SamuelPfisterer1/EuroSpeech", help="Hugging Face Hub repository ID.")
    parser.add_argument("--max-files", type=int, default=None, help="For 'train' subsets, stop after processing this many source audio files in this run.")
    parser.add_argument("--hf-token", default=os.getenv("HF_AUTH_TOKEN"), help="Hugging Face API token.")
    parser.add_argument("--max-split-size-gb", type=float, default=None, help="Maximum size (GB) for a 'train-[subset_id]' split. Overrides RAM %% if smaller.")
    parser.add_argument("--ram-percentage-limit", type=int, default=DEFAULT_RAM_PERCENTAGE_LIMIT, choices=range(10, 91), help="Percentage of available RAM to target for batch size (10-90).")
    parser.add_argument("--max-cer", type=float, default=DEFAULT_MAX_CER, help="Maximum CER for a segment to be included in the upload (default: 0.30).")
    args = parser.parse_args()

    hf_token = args.hf_token or HfFolder.get_token()
    if not hf_token:
        logging.error("Hugging Face token not found. Login using `huggingface-cli login` or provide --hf-token.")
        return

    country_name_lower = args.country.lower()
    logging.info(f"Starting batch upload process for country: {args.country}")
    logging.info(f"Using manifest directory: {args.manifest_dir}")
    logging.info(f"Target repo: {args.repo_id}")
    if args.max_files: logging.info(f"Train subset processing will stop after {args.max_files} audio files.")
    if args.max_split_size_gb: logging.info(f"Max train subset size: {args.max_split_size_gb} GB.")
    logging.info(f"RAM percentage limit for train subsets: {args.ram_percentage_limit}%.")
    logging.info(f"Maximum CER for uploaded segments: {args.max_cer:.2f}.")


    main_manifest_df = load_manifest(args.manifest_dir, args.country)
    if main_manifest_df is None or main_manifest_df.empty:
        logging.info(f"Main manifest for '{args.country}' is empty or could not be loaded. Exiting.")
        return

    splits_df = load_or_initialize_splits_csv(args.manifest_dir, args.country)
    if splits_df is None:
        logging.info(f"Splits CSV for '{args.country}' could not be loaded. Exiting.")
        return

    # Process 'test' split
    if not process_fixed_split(main_manifest_df, splits_df, country_name_lower, 'test', args, hf_token):
        logging.error("Critical error during 'test' split processing. Exiting.")
        return
    main_manifest_df = load_manifest(args.manifest_dir, args.country) # Reload after potential updates
    if main_manifest_df is None: logging.error("Failed to reload manifest after test split. Exiting."); return

    # Process 'validation' split
    if not process_fixed_split(main_manifest_df, splits_df, country_name_lower, 'validation', args, hf_token):
        logging.error("Critical error during 'validation' split processing. Exiting.")
        return
    main_manifest_df = load_manifest(args.manifest_dir, args.country) # Reload
    if main_manifest_df is None: logging.error("Failed to reload manifest after validation split. Exiting."); return

    # Process 'train' subsets
    if not process_train_subsets(main_manifest_df, splits_df, country_name_lower, args, hf_token):
        logging.error("Critical error during 'train' subset processing. Exiting.")
        return

    logging.info(f"\nBatch upload process finished for country '{args.country}'.")

if __name__ == "__main__":
    main() 