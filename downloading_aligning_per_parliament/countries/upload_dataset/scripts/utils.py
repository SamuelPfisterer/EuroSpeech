"""Utility functions for the dataset upload process."""

import jiwer
import os
import logging
import pandas as pd

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Constants --- 
HUMAN_TRANSCRIPT_FIELD = 'human_text' # Adjust if field name differs
ASR_TRANSCRIPT_FIELD = 'asr_text'       # Adjust if field name differs
AUDIO_FILE_FIELD = 'audio_file'
SEGMENTS_FIELD = 'segments'
START_FIELD = 'start'
END_FIELD = 'end'
CER_FIELD = 'cer'
START_IDX_FIELD = 'start_idx'
END_IDX_FIELD = 'end_idx'

# Mapping from country directory name to ISO 639-1 language code
# TODO: Extend this mapping as needed
LANGUAGE_MAP = {
    'germany': 'de',
    'serbia': 'sr'
    # Add other countries here, e.g.:
    # 'france': 'fr',
    # 'spain': 'es',
}

# --- Functions --- 

def get_language_code(country_name):
    """Get the language code for a given country directory name."""
    return LANGUAGE_MAP.get(country_name.lower(), None)

def calculate_wer(human_transcript, asr_transcript):
    """Calculate Word Error Rate (WER)."""
    try:
        # Handle potential empty strings which jiwer might dislike depending on version/settings
        human = human_transcript if human_transcript else ""
        asr = asr_transcript if asr_transcript else ""
        # Handle cases where inputs might be non-string (e.g., NaN from pandas)
        if not isinstance(human, str): human = str(human)
        if not isinstance(asr, str): asr = str(asr)

        measures = jiwer.compute_measures(human, asr)
        return measures['wer']
    except Exception as e:
        logging.error(f"Error calculating WER for human='{human_transcript}', asr='{asr_transcript}': {e}")
        return None # Or some other indicator like -1.0

def generate_segment_key(country, video_id, start_seconds, end_seconds):
    """Generate a unique key for an audio segment."""
    start_ms = int(start_seconds * 1000)
    end_ms = int(end_seconds * 1000)
    return f"{country}_{video_id}_{start_ms}_{end_ms}"

def parse_video_id_from_audio_path(audio_path):
    """Extract the video_id from the source audio filename (basename without extension)."""
    if not audio_path:
        return None
    try:
        base_name = os.path.basename(str(audio_path))
        video_id, _ = os.path.splitext(base_name)
        return video_id
    except Exception as e:
        logging.error(f"Error parsing video_id from audio path '{audio_path}': {e}")
        return None

def parse_transcript_id(json_path, video_id):
    """Extract the transcript_id from the alignment JSON filename,
    given the already extracted video_id.

    Assumes format like: [video_id]_[transcript_id]_aligned.json
    It removes the known video_id prefix and the suffix.
    """
    if not json_path or not video_id:
        return None
    try:
        json_filename = os.path.basename(str(json_path))
        suffix = "_aligned.json"
        prefix = video_id + "_"

        if json_filename.startswith(prefix) and json_filename.endswith(suffix):
            # Remove prefix and suffix
            transcript_id = json_filename[len(prefix):-len(suffix)]
            # Handle cases where video_id might appear again in transcript_id?
            # For now, assume simple structure.
            return transcript_id
        else:
            logging.warning(f"Could not parse transcript_id from filename '{json_filename}' using video_id '{video_id}'. Filename might not match expected pattern.")
            return None
    except Exception as e:
        logging.error(f"Error parsing transcript_id from '{json_path}' with video_id '{video_id}': {e}")
        return None

# Add more utility functions as needed, e.g., for safe CSV handling,
# audio sample rate detection, etc.

# Example of a more robust CSV update function structure (conceptual)
# This still doesn't solve parallelism without external locking mechanisms.
def update_manifest_statuses(csv_path, status_updates):
    """Updates statuses and error messages in the manifest CSV.

    Args:
        csv_path (str): Path to the manifest CSV.
        status_updates (dict): A dictionary where keys are segment keys (str)
                               and values are tuples of (new_status: str, error_message: str | None).
                               Example: {'key1': ('uploaded', None), 'key2': ('error', 'Audio load failed')}

    Returns:
        bool: True if successful, False otherwise.
    """
    if not status_updates:
        return True

    logging.info(f"Updating manifest {csv_path} for {len(status_updates)} keys.")
    try:
        # Use a try-except block for the entire file operation
        try:
            df = pd.read_csv(csv_path, keep_default_na=False) # keep_default_na=False helps with empty strings vs NaN
        except FileNotFoundError:
            logging.error(f"Manifest file not found: {csv_path}")
            return False
        except Exception as e:
            logging.error(f"Error reading manifest {csv_path}: {e}")
            return False

        if 'key' not in df.columns:
            logging.error(f"Manifest {csv_path} missing 'key' column.")
            return False
        if 'status' not in df.columns: df['status'] = 'pending'
        if 'error_message' not in df.columns: df['error_message'] = '' # Use empty string for consistency

        keys_updated = 0
        for key, (new_status, error_msg) in status_updates.items():
            # Find index(es) for the key - should ideally be one
            idx = df.index[df['key'] == key].tolist()
            if idx:
                # Prepare error message (use empty string for None to avoid NaN issues with pandas)
                error_msg_val = str(error_msg) if error_msg is not None else ''
                df.loc[idx, 'status'] = new_status
                df.loc[idx, 'error_message'] = error_msg_val
                keys_updated += len(idx)
            else:
                logging.warning(f"Key '{key}' not found in manifest during status update.")

        # Overwrite CSV
        df.to_csv(csv_path, index=False, encoding='utf-8')
        logging.info(f"Manifest update complete. Attempted {len(status_updates)} updates, modified {keys_updated} rows.")
        return True

    except Exception as e:
        # Catch any unexpected errors during the update process or saving
        logging.error(f"CRITICAL: Failed during update/save of manifest {csv_path}: {e}")
        return False 