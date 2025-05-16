"""
Supabase configuration and utility functions for the Bulgarian Parliament download system.
"""

from datetime import datetime
from typing import Dict, Any, Optional
from supabase import create_client, Client
import logging

# Supabase configuration
SUPABASE_URL = "https://jyrujzmpicrqjcdwfwwr.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imp5cnVqem1waWNycWpjZHdmd3dyIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzYwOTI3ODcsImV4cCI6MjA1MTY2ODc4N30.jzAOM2BFVAH25kZNfR4ownHYqRF_XXqpYq9DiERi-Lk"

# Constants
PARLIAMENT_ID = 'slovenia'
STATUS_PENDING = 'pending'
STATUS_DOWNLOADING = 'downloading'
STATUS_COMPLETED = 'completed'
STATUS_FAILED = 'failed'

class SupabaseClient:
    _instance: Optional['SupabaseClient'] = None
    _client: Optional[Client] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._client is None:
            if not SUPABASE_URL or not SUPABASE_KEY:
                raise ValueError("Supabase credentials not configured")
            self._client = create_client(SUPABASE_URL, SUPABASE_KEY)

    @property
    def client(self) -> Client:
        return self._client

def get_supabase() -> Client:
    """Get the Supabase client instance."""
    return SupabaseClient().client

def session_exists(session_id: str) -> bool:
    """Check if a session already exists in Supabase.
    
    Args:
        session_id: Unique identifier for the download session
        
    Returns:
        bool: True if session exists, False otherwise
    """
    try:
        client = get_supabase()
        response = client.table('download_status')\
            .select('session_id')\
            .eq('session_id', session_id)\
            .eq('parliament_id', PARLIAMENT_ID)\
            .execute()
        return len(response.data) > 0
    except Exception as e:
        logging.error(f"Error checking session existence: {str(e)}")
        return False  # Assume session doesn't exist if we can't check

def start_download(session_id: str, modality: str) -> None:
    """Record download start."""
    client = get_supabase()
    client.table('download_status').update({
        'parliament_id': PARLIAMENT_ID,
        f'{modality}_status': STATUS_DOWNLOADING,
        f'{modality}_download_started': datetime.now().isoformat()
    }).eq('session_id', session_id).execute()

def complete_download(session_id: str, modality: str, metrics: Optional[Dict[str, Any]] = None) -> None:
    """Record successful download with metrics for videos."""
    update_data = {
        'parliament_id': PARLIAMENT_ID,
        f'{modality}_status': STATUS_COMPLETED,
        f'{modality}_download_completed': datetime.now().isoformat()
    }
    
    # Add video metrics if available
    if modality == 'video' and metrics:
        duration = metrics.get('duration')
        if duration is not None:
            duration = int(float(duration))  # Convert to integer, handling potential float values
        
        update_data.update({
            'video_duration_seconds': duration,
            'video_size_bytes': metrics.get('size')
        })
    
    client = get_supabase()
    client.table('download_status').update(update_data)\
        .eq('session_id', session_id).execute()

def fail_download(session_id: str, modality: str, error_msg: str, retry_count: int) -> None:
    """Record failed download with error and retry count."""
    client = get_supabase()
    client.table('download_status').update({
        'parliament_id': PARLIAMENT_ID,
        f'{modality}_status': STATUS_FAILED,
        'last_error': error_msg,
        'last_error_timestamp': datetime.now().isoformat(),
        'retry_count': retry_count
    }).eq('session_id', session_id).execute()

def create_download_entry(session_id: str) -> None:
    """Create a new download entry in Supabase.
    
    Args:
        session_id: Unique identifier for the download session
        
    Raises:
        Exception: If there is any error creating the entry, including if it already exists
    """
    client = get_supabase()
    
    # Create entry - will raise an exception if it fails for any reason
    client.table('download_status').insert({
        'session_id': session_id,
        'parliament_id': PARLIAMENT_ID,
        'created_at': datetime.now().isoformat(),
        'video_status': STATUS_PENDING,
        'transcript_status': STATUS_PENDING,
        'video_download_started': None,
        'video_download_completed': None,
        'transcript_download_started': None,
        'transcript_download_completed': None
    }).execute()
    logging.info(f"Created download entry for session {session_id}")

def get_download_status(session_id: str) -> Dict[str, Any]:
    """Get the current status of a download entry."""
    client = get_supabase()
    response = client.table('download_status')\
        .select('*')\
        .eq('session_id', session_id)\
        .single()\
        .execute()
    return response.data if response else None

def get_parliament_progress() -> Dict[str, Any]:
    """Get the current progress for the Bulgarian parliament."""
    client = get_supabase()
    response = client.table('parliament_progress')\
        .select('*')\
        .eq('parliament_id', PARLIAMENT_ID)\
        .single()\
        .execute()
    return response.data if response else None 