"""
Utilities Module

Contains utility functions for I/O operations, caching, logging, etc.
"""

from .io import save_alignments, save_transcribed_segments, load_transcribed_segments, get_audio_duration, get_alignment_stats, get_alignment_stats_for_single_file, get_audio_directory_stats
from .logging.supabase_logging import (
    get_supabase,
    SupabaseClient,
    SupabaseClientError,
    AlignmentMetrics
)

__all__ = [
    # I/O utilities
    "save_alignments",
    "save_transcribed_segments",
    "load_transcribed_segments",
    
    # Supabase logging
    "get_supabase",
    "SupabaseClient",
    "SupabaseClientError",
    "AlignmentMetrics"
]