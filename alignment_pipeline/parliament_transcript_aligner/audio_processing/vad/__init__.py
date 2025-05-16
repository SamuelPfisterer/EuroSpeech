"""
Voice Activity Detection Module

Contains different VAD implementations for speech detection.
"""

from .pyannote_vad import initialize_vad_pipeline
from .silero_vad import get_silero_vad

__all__ = [
    "initialize_vad_pipeline",
    "get_silero_vad"
]