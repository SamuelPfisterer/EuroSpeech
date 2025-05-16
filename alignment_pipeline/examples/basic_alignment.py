#!/usr/bin/env python3
"""
Basic alignment example

This script demonstrates how to use the parliament_transcript_aligner
library to align an audio file with a transcript.
"""

import os
import sys
from pathlib import Path

# Add parent directory to sys.path to make package importable
parent_dir = str(Path(__file__).resolve().parent.parent)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from parliament_transcript_aligner import (
    AudioSegmenter,
    TranscriptAligner,
    initialize_vad_pipeline,
    initialize_diarization_pipeline,
    save_alignments,
    save_transcribed_segments,
    load_transcribed_segments
)

def align_audio_with_transcript(
    audio_path: str,
    transcript_path: str,
    output_dir: str,
    use_cache: bool = True
):
    """
    Align an audio file with a transcript.
    
    Args:
        audio_path: Path to the audio file (.opus or .wav)
        transcript_path: Path to the transcript file (.txt)
        output_dir: Directory to save results
        use_cache: Whether to use cached segments if available
    """
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Define cache and output paths
    cache_path = Path(output_dir) / f"{Path(audio_path).stem}_segments.pkl"
    alignment_path = Path(output_dir) / f"{Path(audio_path).stem}_aligned.json"
    
    # Initialize pipelines
    print("Initializing VAD pipeline...")
    vad_pipeline = initialize_vad_pipeline()
    
    print("Initializing diarization pipeline...")
    diarization_pipeline = initialize_diarization_pipeline()
    
    # Initialize audio segmenter
    segmenter = AudioSegmenter(vad_pipeline, diarization_pipeline)
    
    # Segment and transcribe audio
    if use_cache and cache_path.exists():
        print(f"Loading cached segments from {cache_path}")
        transcribed_segments = load_transcribed_segments(cache_path)
    else:
        print(f"Segmenting and transcribing audio: {audio_path}")
        transcribed_segments = segmenter.segment_and_transcribe(audio_path)
        
        # Cache the results
        print(f"Caching segments to {cache_path}")
        save_transcribed_segments(transcribed_segments, cache_path)
    
    # Load transcript
    print(f"Loading transcript: {transcript_path}")
    with open(transcript_path, "r", encoding="utf-8") as f:
        human_transcript = f.read()
    
    # Initialize aligner
    aligner = TranscriptAligner()
    
    # Align transcript
    print("Aligning transcript...")
    aligned_segments = aligner.align_transcript(
        transcribed_segments, 
        human_transcript
    )
    
    # Save alignments
    print(f"Saving alignments to {alignment_path}")
    save_alignments(aligned_segments, audio_path, str(alignment_path))
    
    # Print results summary
    print("\nAlignment Results:")
    print(f"  Total segments: {len(aligned_segments)}")
    
    avg_cer = sum(segment.cer for segment in aligned_segments) / len(aligned_segments)
    print(f"  Average CER: {avg_cer:.3f}")
    
    # Print a few examples
    print("\nExample Alignments:")
    for i, segment in enumerate(aligned_segments[:3]):
        print(f"\nSegment {i+1}:")
        print(f"  Time: [{segment.start:.1f}s → {segment.end:.1f}s]")
        print(f"  ASR:    {segment.asr_text}")
        print(f"  Human:  {segment.human_text}")
        print(f"  CER:    {segment.cer:.3f}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Align audio with transcript")
    parser.add_argument("audio_path", help="Path to audio file (.opus or .wav)")
    parser.add_argument("transcript_path", help="Path to transcript file (.txt)")
    parser.add_argument("--output-dir", "-o", default="output", 
                      help="Directory to save results")
    parser.add_argument("--no-cache", action="store_true",
                      help="Don't use cached segments")
    
    args = parser.parse_args()
    
    align_audio_with_transcript(
        args.audio_path,
        args.transcript_path,
        args.output_dir,
        use_cache=not args.no_cache
    ) 