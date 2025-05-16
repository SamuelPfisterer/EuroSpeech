"""Optional Supabase configuration and tracking functions.

This module provides both real Supabase integration and dummy functions when Supabase is disabled.
"""

import os
from typing import Dict, Optional

# Flag to enable/disable Supabase integration
SUPABASE_ENABLED = os.getenv('USE_SUPABASE', '').lower() == 'true'

if SUPABASE_ENABLED:
    try:
        from supabase import create_client, Client
        
        # Supabase configuration
        SUPABASE_URL = os.getenv('SUPABASE_URL')
        SUPABASE_KEY = os.getenv('SUPABASE_KEY')
        
        if not SUPABASE_URL or not SUPABASE_KEY:
            raise ValueError("Supabase URL and key must be provided when Supabase is enabled")
            
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    except ImportError:
        raise ImportError("supabase-py package required when Supabase is enabled. Install with: pip install supabase")
else:
    # Dummy functions when Supabase is disabled
    def session_exists(session_id: str) -> bool:
        """Dummy function when Supabase is disabled."""
        return False

    def create_download_entry(session_id: str) -> None:
        """Dummy function when Supabase is disabled."""
        pass

    def start_download(session_id: str, modality: str) -> None:
        """Dummy function when Supabase is disabled."""
        pass

    def complete_download(session_id: str, modality: str, metrics: Optional[Dict] = None) -> None:
        """Dummy function when Supabase is disabled."""
        pass

    def fail_download(session_id: str, modality: str, error: str, retry_count: int = 0) -> None:
        """Dummy function when Supabase is disabled."""
        pass

if SUPABASE_ENABLED:
    def session_exists(session_id: str) -> bool:
        """Check if a session already exists in Supabase."""
        try:
            result = supabase.table('downloads').select('id').eq('id', session_id).execute()
            return len(result.data) > 0
        except Exception as e:
            print(f"Error checking session existence: {str(e)}")
            return False

    def create_download_entry(session_id: str) -> None:
        """Create a new download entry in Supabase."""
        try:
            supabase.table('downloads').insert({
                'id': session_id,
                'status': 'pending'
            }).execute()
        except Exception as e:
            print(f"Error creating download entry: {str(e)}")

    def start_download(session_id: str, modality: str) -> None:
        """Mark a download as started in Supabase."""
        try:
            supabase.table('downloads').update({
                f'{modality}_status': 'downloading',
                f'{modality}_started_at': 'now()'
            }).eq('id', session_id).execute()
        except Exception as e:
            print(f"Error starting download: {str(e)}")

    def complete_download(session_id: str, modality: str, metrics: Optional[Dict] = None) -> None:
        """Mark a download as completed in Supabase."""
        try:
            update_data = {
                f'{modality}_status': 'completed',
                f'{modality}_completed_at': 'now()'
            }
            if metrics:
                update_data.update({
                    f'{modality}_{key}': value 
                    for key, value in metrics.items()
                })
            
            supabase.table('downloads').update(update_data).eq('id', session_id).execute()
        except Exception as e:
            print(f"Error completing download: {str(e)}")

    def fail_download(session_id: str, modality: str, error: str, retry_count: int = 0) -> None:
        """Mark a download as failed in Supabase."""
        try:
            supabase.table('downloads').update({
                f'{modality}_status': 'failed',
                f'{modality}_error': error,
                f'{modality}_retry_count': retry_count,
                f'{modality}_failed_at': 'now()'
            }).eq('id', session_id).execute()
        except Exception as e:
            print(f"Error marking download as failed: {str(e)}") 