"""
Parliament Transcript Aligner

A library for aligning parliamentary audio recordings with their corresponding transcripts.
"""

from .audio_processing.segmenter import AudioSegmenter
from .audio_processing.diarization import initialize_diarization_pipeline
from .audio_processing.vad import initialize_vad_pipeline, get_silero_vad
from .transcript.aligner import TranscriptAligner
from .transcript.preprocessor import create_preprocessor
from .data_models.models import TranscribedSegment, AlignedTranscript
from .utils.io import (
    save_alignments, 
    load_alignments,
    save_transcribed_segments,
    load_transcribed_segments
)
from .pipeline.alignment_pipeline import AlignmentPipeline

__all__ = [
    # Audio Processing
    'AudioSegmenter',
    'initialize_diarization_pipeline',
    'initialize_vad_pipeline',
    'get_silero_vad',
    
    # Transcript Alignment
    'TranscriptAligner',

    # Transcript Processing
    'create_preprocessor',
    
    # Pipeline
    'AlignmentPipeline',
    
    # Data Models
    'TranscribedSegment',
    'AlignedTranscript',
    
    # I/O Utilities
    'save_alignments',
    'load_alignments', 
    'save_transcribed_segments',
    'load_transcribed_segments'
]

__version__ = '0.1.0' 