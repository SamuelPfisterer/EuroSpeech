"""Processes the upload_manifest.csv, extracts audio segments,
and uploads them to Hugging Face Hub in batches based on source audio files.

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
load_dotenv("/itet-stor/spfisterer/net_scratch/Alignment/testing/own_pipeline/.env")

# Assuming utils.py is in the same directory
import utils

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Constants --- 
# Define the target sampling rate for the HF dataset.
# MUST BE VERIFIED based on source data analysis or chosen target rate.
# Common rates are 16000 or 48000 for Opus usually.
TARGET_AUDIO_SAMPLING_RATE = 16000
# Define the HF Dataset features - MUST match dataset_upload.md
DATASET_FEATURES = Features({
    'audio': Audio(sampling_rate=TARGET_AUDIO_SAMPLING_RATE),
    'key': Value("string"),
    'country': Value("string"),
    'language': Value("string"),
    'video_id': Value("string"),
    'transcript_id': Value("string"), # Added based on filename parsing
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
        df = pd.read_csv(csv_path, keep_default_na=False) # keep_default_na helpful
        required_cols = ['status', 'source_audio_path', 'key', 'country']
        if not all(col in df.columns for col in required_cols):
            logging.error(f"Manifest {csv_path} missing one or more required columns: {required_cols}.")
            return None

        # Verify the country column matches the target country (consistency check)
        if not df.empty and not (df['country'].str.lower() == target_country.lower()).all():
             logging.warning(f"Manifest {csv_path} contains rows with mismatched country names.")
             # Optionally filter again, though loading the correct file should suffice
             # df = df[df['country'].str.lower() == target_country.lower()].copy()

        logging.info(f"Loaded manifest for country '{target_country}' from {csv_path} ({len(df)} rows).")
        return df
    except Exception as e:
        logging.error(f"Error loading manifest {csv_path}: {e}")
        return None

def find_next_pending_source_file(df):
    """Find a source_audio_path that has pending segments within the DataFrame."""
    # Ensure status column is treated as string if loaded with keep_default_na=False
    pending_rows = df[df['status'].astype(str) == 'pending']
    if pending_rows.empty:
        return None
    # Return the first unique path found among pending rows
    unique_pending_paths = pending_rows['source_audio_path'].unique()
    return unique_pending_paths[0] if len(unique_pending_paths) > 0 else None

def update_manifest_file(csv_path, status_updates):
    """Update the status of specific rows in the specified country CSV file."""
    if not status_updates:
        return True # No updates needed

    # Utilize the utility function for the actual update
    return utils.update_manifest_statuses(csv_path, status_updates)


# --- Audio Processing --- 

def process_source_audio(source_path_str, segments_df):
    """Load audio, extract segments, and return records for Hugging Face dataset."""
    records = []
    processed_keys = set()
    failed_keys = set()
    error_messages = {}

    source_path = Path(source_path_str)
    # Check if path is absolute or resolve relative to script/working dir if needed
    # For simplicity, assume paths in manifest are absolute or resolvable from cwd
    if not source_path.is_file():
        logging.error(f"Audio file not found: {source_path_str}")
        failed_keys.update(segments_df['key'].tolist())
        for key in failed_keys: error_messages[key] = "Source audio file not found"
        return records, processed_keys, failed_keys, error_messages

    try:
        logging.info(f"Loading audio source: {source_path_str}")
        full_audio = AudioSegment.from_file(source_path)
        actual_sample_rate = full_audio.frame_rate
        logging.info(f"Detected sample rate: {actual_sample_rate} Hz for {source_path_str}")

        if actual_sample_rate != TARGET_AUDIO_SAMPLING_RATE:
            logging.warning(f"Resampling {source_path_str} from {actual_sample_rate}Hz to {TARGET_AUDIO_SAMPLING_RATE}Hz.")
            full_audio = full_audio.set_frame_rate(TARGET_AUDIO_SAMPLING_RATE)
            actual_sample_rate = TARGET_AUDIO_SAMPLING_RATE

    except CouldntDecodeError:
        logging.error(f"Could not decode audio file: {source_path_str}")
        failed_keys.update(segments_df['key'].tolist())
        for key in failed_keys: error_messages[key] = "Could not decode audio file"
        return records, processed_keys, failed_keys, error_messages
    except FileNotFoundError:
         logging.error(f"Audio file not found (likely during pydub load): {source_path_str}")
         failed_keys.update(segments_df['key'].tolist())
         for key in failed_keys: error_messages[key] = "Source audio file not found during load"
         return records, processed_keys, failed_keys, error_messages
    except Exception as e:
        logging.error(f"Error loading audio {source_path_str}: {e}")
        failed_keys.update(segments_df['key'].tolist())
        for key in failed_keys: error_messages[key] = f"Error loading audio: {e}"
        return records, processed_keys, failed_keys, error_messages

    logging.info(f"Extracting {len(segments_df)} segments from {source_path_str}...")
    for _, row in tqdm(segments_df.iterrows(), total=len(segments_df), desc="Extracting segments"):
        key = row['key']
        # Ensure start/end are float before calculation
        start_s = float(row['start_seconds'])
        end_s = float(row['end_seconds'])
        start_ms = int(start_s * 1000)
        end_ms = int(end_s * 1000)

        try:
            segment_audio = full_audio[start_ms:end_ms]
            audio_bytes = segment_audio.export(format="opus").read()

            # Convert potential pandas types to native Python types for Dataset
            wer_val = row['wer']
            wer_float = float(wer_val) if pd.notna(wer_val) else None
            cer_val = row['cer']
            cer_float = float(cer_val) if pd.notna(cer_val) else None

            record = {
                'audio': {'bytes': audio_bytes, 'path': None, 'sampling_rate': actual_sample_rate},
                'key': str(key),
                'country': str(row['country']),
                'language': str(row['language']),
                'video_id': str(row['video_id']),
                'transcript_id': str(row['transcript_id']),
                'start_seconds': start_s,
                'end_seconds': end_s,
                'duration_seconds': float(row['duration_seconds']),
                'asr_transcript': str(row['asr_transcript']),
                'human_transcript': str(row['human_transcript']),
                'cer': cer_float,
                'wer': wer_float,
                'original_transcript_start_idx': int(row['original_transcript_start_idx']),
                'original_transcript_end_idx': int(row['original_transcript_end_idx']),
            }
            records.append(record)
            processed_keys.add(key)

        except Exception as e:
            logging.error(f"Error processing segment {key} from {source_path_str}: {e}")
            failed_keys.add(key)
            error_messages[key] = f"Error extracting/processing segment: {e}"

    logging.info(f"Finished processing {source_path_str}. Success: {len(processed_keys)}, Failed: {len(failed_keys)}")
    return records, processed_keys, failed_keys, error_messages

# --- Hugging Face Hub Interaction --- 

def push_to_hub_with_retries(dataset, repo_id, config_name, split, commit_message, token):
    """Push dataset to Hub with retry mechanism."""
    # api = HfApi(token=token) # Not needed directly for dataset.push_to_hub
    for attempt in range(PUSH_RETRIES):
        try:
            logging.info(f"Attempt {attempt + 1}/{PUSH_RETRIES} pushing {len(dataset)} records to {repo_id} (config={config_name}, split={split}) ...")
            dataset.push_to_hub(
                repo_id=repo_id,
                config_name=config_name,
                split=split,
                commit_message=commit_message,
                token=token
                #blocking=True # Wait for completion
            )
            logging.info(f"Push successful for config={config_name}, split={split}.")
            return True # Success
        except Exception as e:
            logging.error(f"Error on push attempt {attempt + 1}: {e}")
            if attempt < PUSH_RETRIES - 1:
                logging.info(f"Retrying push in {PUSH_RETRY_DELAY} seconds...")
                time.sleep(PUSH_RETRY_DELAY)
            else:
                logging.error(f"Push failed after {PUSH_RETRIES} attempts for config={config_name}.")
                return False # Failed after retries
    return False

# --- Main Logic --- 

def main():
    parser = argparse.ArgumentParser(description="Upload dataset batches for a specific country based on its manifest.")
    parser.add_argument("--manifest-dir", default="/itet-stor/spfisterer/net_scratch/Downloading/countries/upload_dataset/manifests", help="Directory containing the per-country manifest CSV files.")
    parser.add_argument("--country", required=True, help="Process only segments/files for this country (must match manifest filename, e.g., 'germany').")
    parser.add_argument("--repo-id", default="SamuelPfisterer1/EuroSpeech", help="Hugging Face Hub repository ID (e.g., your_username/dataset_name).")
    parser.add_argument("--max-files", type=int, default=None, help="Stop after processing this many source audio files in this run.")
    parser.add_argument("--hf-token", default=os.getenv("HF_AUTH_TOKEN"), help="Hugging Face API token (optional, uses login if None).")
    args = parser.parse_args()

    hf_token = args.hf_token or HfFolder.get_token()
    if not hf_token:
        logging.warning("Hugging Face token not found. Login using `huggingface-cli login` or provide --hf-token.")

    country_name_lower = args.country.lower()
    manifest_path = Path(args.manifest_dir) / f"{country_name_lower}_manifest.csv"

    logging.info(f"Starting batch upload process for country: {args.country}")
    logging.info(f"Using manifest: {manifest_path}")
    logging.info(f"Target repo: {args.repo_id}")
    if args.max_files:
        logging.info(f"Will process a maximum of {args.max_files} source audio files this run.")

    manifest_df = load_manifest(args.manifest_dir, args.country)
    if manifest_df is None or manifest_df.empty:
        logging.info(f"Manifest for country '{args.country}' is empty or could not be loaded. Exiting.")
        return

    # --- Calculate Total Pending Files for Progress Bar --- 
    pending_files_df = manifest_df[manifest_df['status'].astype(str) == 'pending']
    total_pending_source_files = 0
    if not pending_files_df.empty:
        total_pending_source_files = pending_files_df['source_audio_path'].nunique()
    logging.info(f"Found {total_pending_source_files} pending source audio files for country '{args.country}'.")
    # -------------------------------------------------------

    processed_source_files_count = 0
    with tqdm(total=total_pending_source_files, desc=f"Processing Source Files ({args.country})") as pbar:
        while True:
            if args.max_files is not None and processed_source_files_count >= args.max_files:
                logging.info(f"Reached max-files limit ({args.max_files}). Stopping upload run for {args.country}.")
                break

            current_source_path = find_next_pending_source_file(manifest_df)

            if current_source_path is None:
                logging.info(f"No more pending segments found for country '{args.country}'.")
                # Ensure progress bar reaches 100% if it finished early but correctly
                if pbar.n < pbar.total:
                    pbar.update(pbar.total - pbar.n)
                break

            pbar.set_postfix_str(f"Current: ...{Path(current_source_path).name}", refresh=True)
            # logging.info(f"\n--- Processing source file #{processed_source_files_count + 1}: {current_source_path} ---")

            # Get pending rows for this source file
            source_segments_df = manifest_df[
                (manifest_df['source_audio_path'] == current_source_path) &
                (manifest_df['status'].astype(str) == 'pending')
            ].copy()

            if source_segments_df.empty:
                 logging.warning(f"Found source path {current_source_path} but no pending rows? Skipping.")
                 # This source file doesn't count towards progress as it has no pending work.
                 # Mark rows for this source file as skipped so we don't select it again.
                 indices_to_mark = manifest_df[manifest_df['source_audio_path'] == current_source_path].index
                 if not indices_to_mark.empty:
                     manifest_df.loc[indices_to_mark, 'status'] = 'skipped_no_pending'
                 continue

            # --- Process Audio and Create Dataset --- 
            records, processed_keys, failed_keys, error_messages = process_source_audio(current_source_path, source_segments_df)

            # --- Push Successfully Processed Records --- 
            push_success_keys = set()
            push_failed_keys_dict = {} # Store keys that failed push with reason

            if records:
                # logging.info(f"Creating dataset for {len(records)} successfully processed segments.")
                try:
                    batch_dataset = Dataset.from_list(records, features=DATASET_FEATURES)
                    keys_in_push_attempt = batch_dataset['key']
                    if not keys_in_push_attempt:
                        logging.warning("Dataset created but key list is empty? Skipping push.")
                    else:
                        first_key = keys_in_push_attempt[0]
                        last_key = keys_in_push_attempt[-1]
                        commit_msg = f"Add segments from {current_source_path} ({args.country}, keys {first_key}..{last_key})"

                        if push_to_hub_with_retries(batch_dataset, args.repo_id, country_name_lower, 'train', commit_msg, hf_token):
                            push_success_keys.update(keys_in_push_attempt)
                        else:
                            logging.error(f"Failed to push batch for {args.country} from {current_source_path}.")
                            for k in keys_in_push_attempt: push_failed_keys_dict[k] = "Failed during Hugging Face Hub upload"

                except Exception as e:
                    logging.error(f"Error creating or pushing dataset for {current_source_path}: {e}")
                    for k in processed_keys: push_failed_keys_dict[k] = f"Error creating/pushing dataset: {e}"

            # --- Update Manifest Status --- 
            status_updates = {}
            for key in failed_keys: status_updates[key] = ('error', error_messages.get(key, "Failed during audio processing/extraction"))
            for key, reason in push_failed_keys_dict.items(): status_updates[key] = ('error', reason)
            for key in push_success_keys:
                if key not in status_updates: status_updates[key] = ('uploaded', None)

            if status_updates:
                 if not update_manifest_file(manifest_path, status_updates):
                      logging.error(f"Failed to update manifest file {manifest_path}. Stopping to prevent data loss.")
                      break # Stop if we can't save status

                 # Reload manifest to reflect updates for the next iteration
                 manifest_df = load_manifest(args.manifest_dir, args.country)
                 if manifest_df is None:
                     logging.error("Failed to reload manifest after update. Stopping.")
                     break
            # else:
                 # logging.info(f"No status changes required for segments from {current_source_path}.")

            processed_source_files_count += 1
            pbar.update(1) # Increment progress bar
            # logging.info(f"Finished processing source file: {current_source_path}")

    logging.info(f"\nBatch upload process finished for country '{args.country}'. Processed {processed_source_files_count} source files.")

if __name__ == "__main__":
    main() 