"""Generates the upload_manifest.csv file by scanning country directories.

Phase 1 of the upload process.
"""

import os
import argparse
import json
import pandas as pd
import numpy as np
from pathlib import Path
from tqdm import tqdm
import logging
import random

# Assuming utils.py is in the same directory
import utils

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Define expected columns for the manifest CSV
MANIFEST_COLUMNS = [
    'key', 'country', 'language', 'video_id', 'transcript_id',
    'source_audio_path', 'start_seconds', 'end_seconds',
    'duration_seconds', 'asr_transcript', 'human_transcript',
    'cer', 'wer', 'original_transcript_start_idx',
    'original_transcript_end_idx', 'status', 'error_message', 'batch_id',
    'split'  # Add split column to manifest
]

# Split distribution constants
TEST_SPLIT_PERCENT = 1
VALIDATION_SPLIT_PERCENT = 1
TRAIN_SPLIT_PERCENT = 98  # Remaining percentage

def find_country_dirs(countries_dir, target_country=None):
    """Find country directories to process."""
    countries_path = Path(countries_dir)
    if not countries_path.is_dir():
        raise FileNotFoundError(f"Countries directory not found: {countries_dir}")

    country_dirs = []
    if target_country:
        target_path = countries_path / target_country
        if target_path.is_dir():
            country_dirs.append(target_path)
        else:
            logging.warning(f"Target country directory not found: {target_path}")
    else:
        country_dirs = [d for d in countries_path.iterdir() if d.is_dir()]

    logging.info(f"Found {len(country_dirs)} country directories to process: {[d.name for d in country_dirs]}")
    return country_dirs

def find_alignment_files_for_country(country_dir):
    """Find all *_aligned.json files for a single country directory."""
    json_files = []
    alignment_output_dir = country_dir / "Alignment" / "alignment_output"
    if alignment_output_dir.is_dir():
        json_files.extend(alignment_output_dir.glob("*_aligned.json"))
    else:
        logging.warning(f"Alignment output directory not found for country: {country_dir.name}")
    return json_files

def process_alignment_file(json_path, existing_keys, existing_audio_paths_for_country):
    """Process a single alignment JSON file and extract segment metadata.

    Args:
        json_path (Path): Path to the alignment JSON file.
        existing_keys (set): Set of segment keys already in the manifest for this country.
        existing_audio_paths_for_country (set): Set of source_audio_paths already
                                               present for this file's country.

    Returns:
        tuple: (list_of_new_records, source_audio_path_processed)
               source_audio_path_processed is the path if new records were added,
               otherwise None.
    """
    records = []
    source_audio_path_processed = None
    country_name = json_path.parent.parent.parent.name # ../../.. -> country dir
    language_code = utils.get_language_code(country_name)
    if not language_code:
        logging.warning(f"No language code found for country '{country_name}' (from {json_path}). Skipping file.")
        return [], None

    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError:
        logging.error(f"Error decoding JSON from {json_path}. Skipping.")
        return [], None
    except Exception as e:
        logging.error(f"Error reading {json_path}: {e}. Skipping.")
        return [], None

    source_audio_path = data.get(utils.AUDIO_FILE_FIELD)
    segments = data.get(utils.SEGMENTS_FIELD, [])

    # --- Derive IDs using new logic --- 
    video_id = utils.parse_video_id_from_audio_path(source_audio_path)
    if not video_id:
         logging.warning(f"Could not derive video_id from audio path '{source_audio_path}' in {json_path}. Skipping file.")
         return [], None
    transcript_id = utils.parse_transcript_id(json_path, video_id)
    if not transcript_id:
         logging.warning(f"Could not derive transcript_id from json path '{json_path}' using video_id '{video_id}'. Skipping file.")
         return [], None
    # ----------------------------------

    # --- Restartability Check --- 
    # Check if this source audio file is already fully represented in the manifest for this country
    if source_audio_path in existing_audio_paths_for_country:
        logging.debug(f"Skipping {json_path} because source audio '{source_audio_path}' already exists in manifest for country '{country_name}'.")
        return [], None
    # ---------------------------

    if not source_audio_path:
         logging.warning(f"Missing source audio path in {json_path}. Skipping segments.")
         return [], None # Cannot process without audio path
    # Check if file exists at generation time - optional but helpful
    # Convert to absolute path for consistent checking if needed
    # source_audio_path_abs = Path(source_audio_path).resolve()
    # if not source_audio_path_abs.is_file():
    elif not Path(source_audio_path).is_file():
       logging.warning(f"Source audio path '{source_audio_path}' not found during manifest generation in {json_path}. Segments will be added but upload will fail.")
       pass # Allow adding segments, but batch upload will fail

    file_had_new_records = False
    for segment in segments:
        start = segment.get(utils.START_FIELD)
        end = segment.get(utils.END_FIELD)
        asr_text = segment.get(utils.ASR_TRANSCRIPT_FIELD)
        human_text = segment.get(utils.HUMAN_TRANSCRIPT_FIELD)
        cer = segment.get(utils.CER_FIELD)
        start_idx = segment.get(utils.START_IDX_FIELD)
        end_idx = segment.get(utils.END_IDX_FIELD)

        if None in [start, end, asr_text, human_text, cer, start_idx, end_idx]:
            logging.warning(f"Skipping segment due to missing fields in {json_path}: {segment}")
            continue

        duration = end - start
        if duration <= 0:
             logging.warning(f"Skipping segment with non-positive duration ({duration}) in {json_path}: {segment}")
             continue

        key = utils.generate_segment_key(country_name, video_id, start, end)

        # Avoid adding exact segment duplicates
        if key in existing_keys:
            continue

        wer = utils.calculate_wer(human_text, asr_text)

        record = {
            'key': key,
            'country': country_name,
            'language': language_code,
            'video_id': video_id,
            'transcript_id': transcript_id,
            'source_audio_path': source_audio_path, # Store path even if invalid now
            'start_seconds': start,
            'end_seconds': end,
            'duration_seconds': duration,
            'asr_transcript': asr_text,
            'human_transcript': human_text,
            'cer': cer,
            'wer': wer,
            'original_transcript_start_idx': start_idx,
            'original_transcript_end_idx': end_idx,
            'status': 'pending', # Initial status
            'error_message': None,
            'batch_id': None
        }
        records.append(record)
        existing_keys.add(key) # Add key to prevent duplicates within this run
        file_had_new_records = True

    if file_had_new_records:
        source_audio_path_processed = source_audio_path
        # Add this path to the set for the current run to prevent reprocessing if multiple JSONs point to the same audio
        # Note: existing_audio_paths_for_country is modified in place
        if source_audio_path: # Only add if path was valid
             existing_audio_paths_for_country.add(source_audio_path)

    return records, source_audio_path_processed

def get_file_size_mb(file_path):
    """Get file size in megabytes."""
    try:
        size_bytes = Path(file_path).stat().st_size
        return size_bytes / (1024 * 1024)  # Convert to MB
    except Exception as e:
        logging.warning(f"Could not get file size for {file_path}: {e}")
        return None

def create_split_assignments(country_dir, manifest_dir):
    """Create or load split assignments for all audio files/video_ids for a country.
    
    Args:
        country_dir (Path): Path to the country directory
        manifest_dir (Path): Path to directory for storing manifests and splits
        
    Returns:
        dict: Mapping of source_audio_path -> split assignment ('train', 'test', or 'validation')
    """
    country_name = country_dir.name
    split_file_path = manifest_dir / f"{country_name}_splits.csv"
    
    # Check if split file already exists
    if split_file_path.exists():
        try:
            split_df = pd.read_csv(split_file_path)
            splits_dict = dict(zip(split_df['source_audio_path'], split_df['split']))
            logging.info(f"Loaded existing splits from {split_file_path} ({len(splits_dict)} files)")
            return splits_dict
        except Exception as e:
            logging.error(f"Error loading existing split file {split_file_path}: {e}. Creating new splits.")
    
    # Calculate audio durations and gather file information
    audio_info = {}  # {source_audio_path: {'duration': seconds, 'size_mb': mb}}
    json_files = find_alignment_files_for_country(country_dir)
    
    logging.info(f"Calculating durations and sizes for audio files in {country_name}...")
    for json_path in tqdm(json_files, desc=f"Scanning files for {country_name} info"):
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                source_audio_path = data.get(utils.AUDIO_FILE_FIELD)
                if not source_audio_path:
                    continue
                
                # Initialize audio file info if we haven't seen it yet
                if source_audio_path not in audio_info:
                    audio_info[source_audio_path] = {
                        'duration': 0.0,
                        'size_mb': get_file_size_mb(source_audio_path)
                    }
                
                # Extract segments and calculate total duration
                segments = data.get(utils.SEGMENTS_FIELD, [])
                for segment in segments:
                    start = segment.get(utils.START_FIELD)
                    end = segment.get(utils.END_FIELD)
                    if start is not None and end is not None:
                        duration = end - start
                        if duration > 0:
                            audio_info[source_audio_path]['duration'] += duration
                            
        except Exception as e:
            logging.warning(f"Error reading {json_path} during info gathering: {e}")
    
    if not audio_info:
        logging.warning(f"No audio paths with valid information found for country {country_name}. Cannot create splits.")
        return {}
    
    # Convert durations to hours and prepare for allocation
    for path_info in audio_info.values():
        path_info['duration_hours'] = path_info['duration'] / 3600.0
    
    # Sort audio paths by duration (optional, helps with more balanced allocation)
    sorted_paths = sorted(audio_info.keys(), 
                        key=lambda p: audio_info[p]['duration_hours'],
                        reverse=True)
    
    # Calculate target hours for each split
    total_hours = sum(info['duration_hours'] for info in audio_info.values())
    min_test_hours = max(0.01, total_hours * TEST_SPLIT_PERCENT / 100)
    min_val_hours = max(0.01, total_hours * VALIDATION_SPLIT_PERCENT / 100)
    
    logging.info(f"Total audio duration for {country_name}: {total_hours:.2f} hours")
    logging.info(f"Target hours - Test: {min_test_hours:.2f}, Validation: {min_val_hours:.2f}")
    
    # Assign splits
    splits_dict = {}
    test_hours = val_hours = train_hours = 0.0
    
    # First try to find files for test set
    for path in sorted_paths:
        duration_hours = audio_info[path]['duration_hours']
        if test_hours < min_test_hours:
            splits_dict[path] = 'test'
            test_hours += duration_hours
        elif val_hours < min_val_hours:
            splits_dict[path] = 'validation'
            val_hours += duration_hours
        else:
            splits_dict[path] = 'train'
            train_hours += duration_hours
    
    # Save splits to CSV with duration and size information
    split_data = []
    for audio_path, split in splits_dict.items():
        video_id = utils.parse_video_id_from_audio_path(audio_path)
        info = audio_info[audio_path]
        split_data.append({
            'source_audio_path': audio_path,
            'video_id': video_id,
            'duration_hours': info['duration_hours'],
            'size_mb': info['size_mb'],
            'split': split
        })
    
    split_df = pd.DataFrame(split_data)
    
    # Calculate and log total size per split
    size_by_split = split_df.groupby('split').agg({
        'size_mb': ['sum', 'count'],
        'duration_hours': 'sum'
    })
    
    # Format size statistics
    total_size_gb = split_df['size_mb'].sum() / 1024  # Convert to GB
    logging.info(f"\nSplit statistics for {country_name}:")
    for split_name in ['train', 'test', 'validation']:
        if split_name in size_by_split.index:
            split_size_gb = size_by_split.loc[split_name, ('size_mb', 'sum')] / 1024
            file_count = size_by_split.loc[split_name, ('size_mb', 'count')]
            hours = size_by_split.loc[split_name, ('duration_hours', 'sum')]
            logging.info(f"{split_name.capitalize()}: {file_count} files, "
                        f"{split_size_gb:.2f}GB ({split_size_gb/total_size_gb:.1%}), "
                        f"{hours:.2f}h ({hours/total_hours:.1%})")
    
    # Save the DataFrame
    split_df.to_csv(split_file_path, index=False)
    
    return splits_dict

def process_country(country_dir, manifest_dir, max_files):
    """Generates or updates the manifest file for a single country."""
    country_name = country_dir.name
    output_path = manifest_dir / f"{country_name}_manifest.csv"
    logging.info(f"\n--- Processing country: {country_name} -> {output_path} ---")

    all_records = []
    existing_keys = set()
    existing_audio_paths_for_country = set()

    # Create or load split assignments for this country
    split_assignments = create_split_assignments(country_dir, manifest_dir)

    # Load existing manifest for this country
    if output_path.exists():
        logging.info(f"Loading existing manifest from {output_path}")
        try:
            existing_df = pd.read_csv(output_path, keep_default_na=False)
            existing_keys.update(existing_df['key'].tolist())
            if 'source_audio_path' in existing_df.columns:
                 # Only load paths relevant to this specific country
                valid_paths = existing_df[pd.notna(existing_df['source_audio_path'])]['source_audio_path'].unique()
                existing_audio_paths_for_country.update(valid_paths)

            logging.info(f"Loaded {len(existing_keys)} existing segment keys and {len(existing_audio_paths_for_country)} existing audio file paths for {country_name}.")
            all_records = existing_df.to_dict('records')
        except Exception as e:
            logging.error(f"Error loading existing manifest {output_path}: {e}. Starting fresh for {country_name}.")
            all_records = []
            existing_keys = set()
            existing_audio_paths_for_country = set()

    json_files_to_process = find_alignment_files_for_country(country_dir)
    if not json_files_to_process:
        logging.info(f"No alignment JSON files found for {country_name}.")
        # Save empty or existing manifest if no files found
        if not all_records:
             logging.warning(f"No records found or generated for {country_name}.")
        else:
             # Ensure columns and save the existing data
             manifest_df = pd.DataFrame(all_records)
             for col in MANIFEST_COLUMNS: manifest_df[col] = manifest_df.get(col)
             manifest_df = manifest_df[MANIFEST_COLUMNS]
             manifest_df.to_csv(output_path, index=False, encoding='utf-8')
             logging.info(f"Existing manifest for {country_name} saved with {len(manifest_df)} records.")
        return # Nothing more to do for this country

    logging.info(f"Processing {len(json_files_to_process)} JSON files for {country_name}...")
    new_audio_files_processed_count = 0
    all_new_records = []
    # Keep track of paths processed in *this run* (for this country)
    audio_paths_processed_this_run = set()

    for json_file in tqdm(json_files_to_process, desc=f"Processing {country_name}"):
        # Pass the set of existing paths for this country
        current_country_audio_paths = existing_audio_paths_for_country.copy()
        # Also add paths processed earlier *in this specific run*
        current_country_audio_paths.update(audio_paths_processed_this_run)

        new_records, audio_path_processed = process_alignment_file(json_file, existing_keys, current_country_audio_paths)

        if new_records:
            # Assign split to each record based on source_audio_path
            for record in new_records:
                audio_path = record['source_audio_path']
                record['split'] = split_assignments.get(audio_path, 'train')  # Default to train if not found
                
            all_new_records.extend(new_records)
            # Check if this audio file is genuinely new for this run (wasn't in loaded manifest)
            if audio_path_processed and audio_path_processed not in existing_audio_paths_for_country:
                # Check if it's the *first time* we process it in *this run*
                if audio_path_processed not in audio_paths_processed_this_run:
                    new_audio_files_processed_count += 1
                    audio_paths_processed_this_run.add(audio_path_processed)

        # Check max_files limit
        if max_files is not None and new_audio_files_processed_count >= max_files:
            logging.info(f"Reached max-files limit ({max_files}) for country {country_name}. Stopping manifest generation for this country.")
            break

    new_records_count = len(all_new_records)
    if new_records_count > 0:
        logging.info(f"Adding {new_records_count} new segment records from {new_audio_files_processed_count} new source audio files for {country_name}.")
        all_records.extend(all_new_records)
    else:
        logging.info(f"No new records to add for {country_name}.")

    if not all_records:
        logging.warning(f"No records found or generated for {country_name}. Manifest file will be empty or unchanged.")
        return

    # Update split field for any existing records that might not have it
    manifest_df = pd.DataFrame(all_records)
    for col in MANIFEST_COLUMNS:
        if col not in manifest_df.columns:
            # Use pd.NA for missing numeric/object, empty string for error_message
            default_val = '' if col == 'error_message' else ('pending' if col == 'status' else pd.NA)
            manifest_df[col] = default_val
    
    # For any rows missing split assignment, assign based on source_audio_path
    if 'split' in manifest_df.columns:
        for idx, row in manifest_df[manifest_df['split'].isna() | (manifest_df['split'] == '')].iterrows():
            audio_path = row['source_audio_path']
            manifest_df.at[idx, 'split'] = split_assignments.get(audio_path, 'train')
    
    manifest_df = manifest_df[MANIFEST_COLUMNS]

    try:
        manifest_df.to_csv(output_path, index=False, encoding='utf-8')
        logging.info(f"Manifest generation for {country_name} complete.")
        logging.info(f"Total records in {output_path}: {len(manifest_df)}")
    except Exception as e: 
        logging.error(f"Error saving manifest to {output_path}: {e}")

def main():
    parser = argparse.ArgumentParser(description="Generate or update per-country manifest CSVs.")
    parser.add_argument("--countries-dir", default="/itet-stor/spfisterer/net_scratch/Downloading/countries", help="Path to the root directory containing country subdirectories.")
    parser.add_argument("--manifest-dir", default="/itet-stor/spfisterer/net_scratch/Downloading/countries/upload_dataset/manifests", help="Directory to store the output manifest CSV files (e.g., manifest_dir/germany_manifest.csv).")
    parser.add_argument("--country", default=None, help="Process only this specific country subdirectory.")
    parser.add_argument("--max-files", type=int, default=None, help="For each country, stop after adding segments from this many *new* source audio files.")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducible splits.")
    args = parser.parse_args()

    # Set random seed for reproducible splits
    random.seed(args.seed)

    manifest_dir = Path(args.manifest_dir)
    manifest_dir.mkdir(parents=True, exist_ok=True)

    try:
        country_dirs_to_process = find_country_dirs(args.countries_dir, args.country)
    except FileNotFoundError as e:
        logging.error(e)
        return

    if not country_dirs_to_process:
        logging.warning("No country directories found to process.")
        return

    logging.info(f"Processing {len(country_dirs_to_process)} countries...")
    for country_dir in tqdm(country_dirs_to_process, desc="Processing Countries"):
        process_country(country_dir, manifest_dir, args.max_files)

    logging.info("\nManifest generation process finished for all specified countries.")

if __name__ == "__main__":
    main() 