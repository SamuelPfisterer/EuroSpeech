import json
import pickle
import statistics
from pathlib import Path
import os
from typing import List, Tuple, Dict, Any, Optional, Union
import subprocess
from pydub import AudioSegment
import logging

from ..data_models.models import TranscribedSegment, AlignedTranscript

def save_alignments(aligned_segments: List[AlignedTranscript], 
                   audio_path: str,
                   output_path: str) -> None:
    """Save aligned segments to JSON file.
    
    Args:
        aligned_segments: List of aligned transcripts
        audio_path: Path to original audio file
        output_path: Path to save JSON file
    """
    data = {
        "audio_file": audio_path,
        "segments": [segment.to_dict() for segment in aligned_segments]
    }
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def load_alignments(json_path: str) -> Tuple[str, List[Dict[str, Any]]]:
    """Load aligned segments from JSON file.
    
    Args:
        json_path: Path to JSON file
        
    Returns:
        Tuple of (audio_path, list of segment dictionaries)
    """
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["audio_file"], data["segments"]

def save_transcribed_segments(segments: List[TranscribedSegment], output_path: Path) -> None:
    """Save transcribed segments using pickle.
    
    Args:
        segments: List of TranscribedSegments
        output_path: Path to save pickle file
    """
    # Create parent directories if they don't exist
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, "wb") as f:
        pickle.dump(segments, f)

def load_transcribed_segments(pickle_path: Path) -> List[TranscribedSegment]:
    """Load transcribed segments from pickle file.
    
    Args:
        pickle_path: Path to pickle file
        
    Returns:
        List of TranscribedSegment objects
    """
    with open(pickle_path, "rb") as f:
        return pickle.load(f)

def get_audio_duration(file_path: Union[str, Path]) -> float:
    """Get duration of an opus audio file in seconds.
    
    Works only with .opus files.
    
    Args:
        file_path: Path to opus audio file
        
    Returns:
        Duration in seconds
    
    Raises:
        ValueError: If file is not an .opus file or doesn't exist
    """
    file_path = Path(file_path) if isinstance(file_path, str) else file_path
    
    if not file_path.exists():
        raise ValueError(f"File does not exist: {file_path}")
    
    # Only allow opus files
    if file_path.suffix.lower() != '.opus':
        raise ValueError(f"Only .opus files are supported, got: {file_path.suffix}")
    
    try:
        cmd = [
            'ffprobe', 
            '-v', 'error', 
            '-show_entries', 'format=duration', 
            '-of', 'default=noprint_wrappers=1:nokey=1', 
            str(file_path)
        ]
        output = subprocess.check_output(cmd).decode('utf-8').strip()
        return float(output)
    except (subprocess.SubprocessError, ValueError) as e:
        raise ValueError(f"Error getting duration of opus file: {e}")

def get_alignment_stats(alignment_paths: List[str]) -> Dict[str, float]:
    """Calculate alignment statistics for multiple alignment files.
    
    Args:
        alignment_paths: List of paths to alignment JSON files
        
    Returns:
        Dictionary with statistics:
            - median_cer: Median Character Error Rate
            - total_aligned_segments_duration: Total duration of aligned segments in seconds
            - aligned_duration_cer30: Duration of segments with CER <= 0.3
            - aligned_duration_cer10: Duration of segments with CER <= 0.1
            - total_video_file_duration: Total duration of all aligned audio files
            - transcript_count: Number of transcripts processed
    """
    all_cers = []
    total_aligned_duration = 0.0
    aligned_duration_cer30 = 0.0
    aligned_duration_cer10 = 0.0
    audio_files = set()
    transcript_count = len(alignment_paths)
    
    for path in alignment_paths:
        audio_path, segments = load_alignments(path)
        audio_files.add(audio_path)
        print(f"Number of segments: {len(segments)}")
        invalid_segments = 0
        
        for segment in segments:
            not_valid_semgents = 0
            # Skip segments with missing data
            if 'cer' not in segment or 'start' not in segment or 'end' not in segment:
                invalid_segments += 1
                if not_valid_semgents < 10:
                    logging.warning(f"Invalid segment: {segment}, cer, start, or end is missing")
                    not_valid_semgents += 1
                continue
                
            cer = segment['cer']
            duration = segment['end'] - segment['start']
            
            if cer is not None and duration is not None:
                all_cers.append(cer)
                total_aligned_duration += duration
                
                if cer <= 0.3:
                    aligned_duration_cer30 += duration
                
                if cer <= 0.1:
                    aligned_duration_cer10 += duration
    
    # Calculate total audio duration
    total_audio_duration = 0.0
    for audio_file in audio_files:
        try:
            total_audio_duration += get_audio_duration(audio_file)
        except ValueError:
            # If we can't get the duration, we continue without it
            pass
    
    # Calculate median CER
    median_cer = statistics.median(all_cers) if all_cers else 0.0
    
    return {
        'median_cer': median_cer,
        'total_aligned_segments_duration': total_aligned_duration,
        'aligned_duration_cer30': aligned_duration_cer30,
        'aligned_duration_cer10': aligned_duration_cer10,
        'total_video_file_duration': total_audio_duration,
        'transcript_count': transcript_count
    }

def get_alignment_stats_for_single_file(alignment_path: str, audio_path: Optional[str] = None) -> Dict[str, float]:
    """Calculate alignment statistics for a single alignment file.
    
    Args:
        alignment_path: Path to alignment JSON file
        audio_path: Optional path to audio file if different from what's in the JSON
        
    Returns:
        Dictionary with statistics (same as get_alignment_stats)
    """
    return get_alignment_stats([alignment_path])

def get_audio_directory_stats(directory_path: Union[str, Path]) -> Dict[str, Any]:
    """Get statistics about opus files in a directory.
    
    Args:
        directory_path: Path to directory containing opus files
        
    Returns:
        Dictionary with:
            - total_audio_files: Number of opus files
            - total_audio_duration_hours: Total duration in hours
            
    Raises:
        ValueError: If directory doesn't exist
    """
    directory_path = Path(directory_path) if isinstance(directory_path, str) else directory_path
    
    if not directory_path.exists() or not directory_path.is_dir():
        import logging
        logging.warning(f"Directory does not exist: {directory_path}")
        return {
            'total_audio_files': 0,
            'total_audio_duration_hours': 0.0
        }
    
    opus_files = list(directory_path.glob("**/*.opus"))
    total_duration_seconds = 0.0
    processed_files = 0
    
    for opus_file in opus_files:
        try:
            total_duration_seconds += get_audio_duration(opus_file)
            processed_files += 1
        except ValueError as e:
            # Log error but continue with other files
            import logging
            logging.warning(f"Error processing {opus_file}: {e}")
    
    # Convert seconds to hours
    total_duration_hours = total_duration_seconds / 3600.0
    
    return {
        'total_audio_files': processed_files,
        'total_audio_duration_hours': total_duration_hours
    } 