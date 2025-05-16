"""
Audio Processing Module

Contains components for audio segmentation, Voice Activity Detection (VAD), 
and speaker diarization.
"""

from .segmenter import AudioSegmenter
from .vad import initialize_vad_pipeline
from .vad import get_silero_vad
from .diarization import initialize_diarization_pipeline

__all__ = [
    "AudioSegmenter",
    "initialize_vad_pipeline",
    "initialize_diarization_pipeline",
    "get_silero_vad" 
]