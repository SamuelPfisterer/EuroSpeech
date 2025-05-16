import json
import logging
from datetime import datetime
from typing import Any, Dict, Optional, Union, List

import dotenv

from supabase import create_client, Client

from ...utils.io import get_audio_directory_stats

logger = logging.getLogger(__name__)

# Video alignment status constants
STATUS_INITIALIZING = 'initializing'  # Just created entry
STATUS_SEGMENTING = 'segmenting'
STATUS_SEGMENTING_COMPLETE = 'segmenting_complete'
STATUS_TRANSCRIBING = 'transcribing'  # ASR processing in progress
STATUS_TRANSCRIBING_COMPLETE = 'transcribing_complete'
STATUS_COMPLETED = 'completed'        # Successfully aligned
STATUS_FAILED = 'failed'              # Failed to align


class AlignmentMetrics:
    """Class representing alignment metrics."""
    
    def __init__(self, 
                 median_cer: float, 
                 transcript_count: int,
                 total_video_file_duration: float,
                 total_aligned_segments_duration: float,
                 aligned_duration_cer30: float,
                 aligned_duration_cer10: float):
        self.median_cer = median_cer
        self.transcript_count = transcript_count
        self.total_video_file_duration = total_video_file_duration
        self.total_aligned_segments_duration = total_aligned_segments_duration
        self.aligned_duration_cer30 = aligned_duration_cer30
        self.aligned_duration_cer10 = aligned_duration_cer10
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary."""
        return {
            'median_cer': self.median_cer,
            'transcript_count': self.transcript_count,
            'total_video_file_duration': self.total_video_file_duration,
            'total_aligned_segments_duration': self.total_aligned_segments_duration,
            'aligned_duration_cer30': self.aligned_duration_cer30,
            'aligned_duration_cer10': self.aligned_duration_cer10
        }


class SupabaseClientError(Exception):
    """Exception raised for Supabase client errors."""
    pass


class SupabaseClient:
    """Client for logging to Supabase."""
    
    def __init__(self, url: str, key: str, parliament_id: str, audio_dirs: List[str]):
        """
        Initialize Supabase client.
        
        Args:
            url: Supabase URL
            key: Supabase API key
            parliament_id: Unique identifier for the parliament
        """
        self.client: Client = create_client(url, key)
        self.parliament_id = parliament_id

        # check if the parliament_id exist in the database
        response = self.client.table('ParliamentAlignment') \
            .select('parliament_id') \
            .eq('parliament_id', parliament_id) \
            .execute()

        if not response.data:
            logger.info(f"Parliament {parliament_id} does not exist in the database, creating a new entry")
            found_non_empty_dir = False  # Flag to track if a non-empty directory is found
            for audio_dir in audio_dirs:
                audio_stats = get_audio_directory_stats(audio_dir)
                if audio_stats['total_audio_files'] > 0:
                    logger.info(f"Found {audio_stats['total_audio_files']} audio files in {audio_dir}, selecting this directory for parliament stats")
                    self.create_parliament_entry(parliament_id, audio_stats['total_audio_files'], audio_stats['total_audio_duration_hours'])
                    found_non_empty_dir = True
                    break
            if not found_non_empty_dir:
                logger.error(f"All audio directories are empty, please check the audio_dirs parameter. The following directories were checked: {audio_dirs}")
                raise SupabaseClientError(f"All audio directories are empty, please check the audio_dirs parameter")
            
    def create_parliament_entry(self, 
                              parliament_id: str,
                              total_audio_files: int,
                              total_audio_duration_hours: float) -> bool:
        """
        Create a parliament entry if it doesn't already exist.
        
        Args:
            parliament_id: Unique identifier for the parliament
            total_audio_files: Total number of audio files
            total_audio_duration_hours: Total duration of all audio files in hours
            
        Returns:
            True if created, False if already exists
            
        Raises:
            SupabaseClientError: If there is an error creating the entry
        """
        try:
            # Check if parliament already exists
            response = self.client.table('ParliamentAlignment') \
                .select('parliament_id') \
                .eq('parliament_id', parliament_id) \
                .execute()
                
            if response.data:
                logger.info(f"Parliament {parliament_id} already exists")
                return False
                
            # Create new parliament entry
            now = datetime.now().isoformat()
            entry = {
                'parliament_id': parliament_id,
                'total_audio_files': total_audio_files,
                'total_audio_duration_hours': total_audio_duration_hours,
                'created_at': now,
                'updated_at': now
            }
            
            self.client.table('ParliamentAlignment').insert(entry).execute()
            logger.info(f"Created parliament entry for {parliament_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error creating parliament entry: {e}")
            raise SupabaseClientError(f"Failed to create parliament entry: {e}")

    def start_video_alignment(self, 
                            video_id: str, 
                            job_id: Optional[str] = None,
                            force_start: bool = False) -> bool:
        """
        Record the start of video alignment process.
        
        Args:
            video_id: Identifier for the video, if not provided, will use the current_video_id attribute of the SupabaseClient instance
            job_id: Optional identifier for the job
            force_start: If True, will update existing entry. If False, will return False if entry exists.
            
        Returns:
            True if new entry created or existing entry updated, False if entry exists and force_start is False
            
        Raises:
            SupabaseClientError: If there is an error recording the start
        """
        try:
            now = datetime.now().isoformat()
            
            # Check if entry already exists
            response = self.client.table('VideoAlignment') \
                .select('video_id') \
                .eq('video_id', video_id) \
                .eq('parliament_id', self.parliament_id) \
                .execute()
                
            if response.data:
                if not force_start:
                    logger.info(f"Video alignment entry for {video_id} already exists")
                    return False
                
                logger.info(f"Still updating existing entry for {video_id} as force_start is True")
                # Update existing entry
                response = self.client.table('VideoAlignment') \
                    .update({
                        'status': STATUS_INITIALIZING,
                        'process_start': now,
                        'job_id': job_id
                    }) \
                    .eq('video_id', video_id) \
                    .eq('parliament_id', self.parliament_id) \
                    .execute()
                
                if response.data and len(response.data) > 0:
                    logger.info(f"Updated video alignment start for {video_id}")
                else:
                    logger.error(f"Failed to update video alignment start for {video_id}")
                    raise SupabaseClientError(f"Failed to update video alignment start for {video_id}, probably no matching entry was found in the database")
            else:
                # Create new entry
                entry = {
                    'video_id': video_id,
                    'parliament_id': self.parliament_id,
                    'job_id': job_id,
                    'process_start': now,
                    'status': STATUS_INITIALIZING
                }
                response = self.client.table('VideoAlignment').insert(entry).execute()
                
                if response.data and len(response.data) > 0:
                    logger.info(f"Created video alignment entry for {video_id}")
                else:
                    logger.error(f"Failed to create video alignment entry for {video_id}")
                    raise SupabaseClientError(f"Failed to create video alignment entry for {video_id}")
                
            return True
                
        except Exception as e:
            logger.error(f"Error starting video alignment: {e}")
            raise SupabaseClientError(f"Failed to start video alignment: {e}")

    def update_segmentation_start(self, video_id: str) -> None:
        """
        Record segmentation start

        Args:
            video_id: Identifier for the video, if not provided, will use the current_video_id attribute of the SupabaseClient instance

        Raises:
            SupabaseClientError: If there is an error updating the record
        """
        try:
            response = self.client.table('VideoAlignment') \
                .update({'status': STATUS_SEGMENTING}) \
                .eq('video_id', video_id) \
                .eq('parliament_id', self.parliament_id) \
                .execute()
                
            if response.data and len(response.data) > 0:
                logger.info(f"Updated segmentation start for {video_id}")
            else:
                logger.error(f"Failed to update segmentation start for {video_id}")
                raise SupabaseClientError(f"Failed to update segmentation start for {video_id}, probably no matching entry was found in the database")
        except Exception as e:
            logger.error(f"Error updating segmentation start: {e}")
            raise SupabaseClientError(f"Failed to update segmentation start: {e}")

    def update_segmentation_complete(self, 
                                   video_id: str, 
                                   duration_seconds: float,
                                   segment_count: Optional[int] = None) -> None:
        """
        Record segmentation completion with duration.
        
        Args:
            video_id: Identifier for the video, if not provided, will use the current_video_id attribute of the SupabaseClient instance
            duration_seconds: Time taken for segmentation in seconds
            segment_count: Optional count of segments created
            
        Raises:
            SupabaseClientError: If there is an error updating the record
        """
        try:
            update_data = {
                'status': STATUS_SEGMENTING_COMPLETE,
                'segmentation_process_duration_seconds': duration_seconds
            }
            
            if segment_count is not None:
                update_data['segment_count'] = segment_count
                
            response = self.client.table('VideoAlignment') \
                .update(update_data) \
                .eq('video_id', video_id) \
                .eq('parliament_id', self.parliament_id) \
                .execute()
                
            if response.data and len(response.data) > 0:
                logger.info(f"Updated segmentation completion for {video_id}")
            else:
                logger.error(f"Failed to update segmentation completion for {video_id}")
                raise SupabaseClientError(f"Failed to update segmentation completion for {video_id}, probably no matching entry was found in the database")
        except Exception as e:
            logger.error(f"Error updating segmentation completion: {e}")
            raise SupabaseClientError(f"Failed to update segmentation completion: {e}")

    def update_transcribing_start(self, video_id: str) -> None:
        """
        Record transcribing start

        Args:
            video_id: Identifier for the video
        """
        try:
            response = self.client.table('VideoAlignment') \
                .update({'status': STATUS_TRANSCRIBING}) \
                .eq('video_id', video_id) \
                .eq('parliament_id', self.parliament_id) \
                .execute()
                
            if response.data and len(response.data) > 0:
                logger.info(f"Updated transcribing start for {video_id}")
            else:
                logger.error(f"Failed to update transcribing start for {video_id}")
                raise SupabaseClientError(f"Failed to update transcribing start for {video_id}, probably no matching entry was found in the database")
        except Exception as e:
            logger.error(f"Error updating transcribing start: {e}")
            raise SupabaseClientError(f"Failed to update transcribing start: {e}")

    def update_transcribing_complete(self, 
                          video_id: str, 
                          duration_seconds: float) -> None:
        """
        Record ASR completion with duration.
        
        Args:
            video_id: Identifier for the video
            duration_seconds: Time taken for ASR in seconds
            
        Raises:
            SupabaseClientError: If there is an error updating the record
        """
        try:
            response = self.client.table('VideoAlignment') \
                .update({
                    'status': STATUS_TRANSCRIBING_COMPLETE,
                    'asr_process_duration_seconds': duration_seconds
                }) \
                .eq('video_id', video_id) \
                .eq('parliament_id', self.parliament_id) \
                .execute()
                
            if response.data and len(response.data) > 0:
                logger.info(f"Updated ASR completion for {video_id}")
            else:
                logger.error(f"Failed to update ASR completion for {video_id}")
                raise SupabaseClientError(f"Failed to update ASR completion for {video_id}, probably no matching entry was found in the database")
        except Exception as e:
            logger.error(f"Error updating ASR completion: {e}")
            raise SupabaseClientError(f"Failed to update ASR completion: {e}")

    def complete_video_alignment(self, 
                               video_id: str, 
                               metrics: Union[AlignmentMetrics, Dict[str, Any]],
                               with_diarization: bool = False,
                               enable_subset: bool = False) -> None:
        """
        Record successful alignment with metrics.
        
        Args:
            video_id: Identifier for the video
            metrics: Alignment metrics (either AlignmentMetrics object or dict)
            with_diarization: Whether diarization was used
            enable_subset: If True, allows subset of fields; if False, requires all fields
            
        Raises:
            SupabaseClientError: If there is an error recording completion
            ValueError: If invalid fields or values are provided
        """
        try:
            # Define allowed fields with their expected types
            field_types = {
                'median_cer': float,
                'transcript_count': int,
                'total_video_file_duration': float,
                'total_aligned_segments_duration': float,
                'aligned_duration_cer30': float,
                'aligned_duration_cer10': float
            }
            
            # Convert metrics to dict if needed
            if isinstance(metrics, AlignmentMetrics):
                metrics_dict = metrics.to_dict()
            else:
                metrics_dict = metrics.copy()  # Create a copy to avoid modifying the original
            
            # Check for invalid fields
            invalid_fields = set(metrics_dict.keys()) - set(field_types.keys())
            if invalid_fields:
                raise ValueError(f"Invalid fields in metrics: {invalid_fields}")
            
            # Check if all required fields are present when subset is not enabled
            if not enable_subset:
                missing_fields = set(field_types.keys()) - set(metrics_dict.keys())
                if missing_fields:
                    raise ValueError(f"Missing required fields: {missing_fields}. Set enable_subset=True to allow partial updates.")
            
            # Validate types for all provided fields
            for field, value in metrics_dict.items():
                expected_type = field_types[field]
                if not isinstance(value, expected_type):
                    raise ValueError(f"Field '{field}' has incorrect type: expected {expected_type.__name__}, got {type(value).__name__}")
            
            # Prepare update data
            update_data = {
                'status': STATUS_COMPLETED,
                'process_end': datetime.now().isoformat(),
                'with_diarization': with_diarization,
                **metrics_dict  # Add all validated fields
            }
            
            # Perform the update
            response = self.client.table('VideoAlignment') \
                .update(update_data) \
                .eq('video_id', video_id) \
                .eq('parliament_id', self.parliament_id) \
                .execute()
            if response.data and len(response.data) > 0:
                logger.info(f"Completed video alignment for {video_id} with updating data: {update_data}")
            else:
                logger.error(f"Failed to complete video alignment for {video_id}")
                raise SupabaseClientError(f"Failed to complete video alignment for {video_id}, probably no matching entry was found in the database")
        except ValueError as e:
            logger.error(f"Validation error: {e}")
            raise
        except Exception as e:
            logger.error(f"Error completing video alignment: {e}")
            raise SupabaseClientError(f"Failed to complete video alignment: {e}")

    def fail_video_alignment(self, 
                           video_id: str, 
                           error_info: Union[str, Dict[str, Any]]) -> None:
        """
        Record failed alignment with error details.
        
        Args:
            video_id: Identifier for the video
            error_info: Error details (string or dict)
            
        Raises:
            SupabaseClientError: If there is an error recording failure
        """
        try:
            # Convert error_info to JSON string if it's a dict
            if isinstance(error_info, dict):
                error_info_json = json.dumps(error_info)
            else:
                error_info_json = error_info
                
            response = self.client.table('VideoAlignment') \
                .update({
                    'status': STATUS_FAILED,
                    'process_end': datetime.now().isoformat(),
                    'error_info': error_info_json
                }) \
                .eq('video_id', video_id) \
                .eq('parliament_id', self.parliament_id) \
                .execute()
                
            if response.data and len(response.data) > 0:
                logger.info(f"Recorded alignment failure for {video_id}")
            else:
                logger.error(f"Failed to record alignment failure for {video_id}")
                raise SupabaseClientError(f"Failed to record alignment failure for {video_id}, probably no matching entry was found in the database")
        except Exception as e:
            logger.error(f"Error recording alignment failure: {e}")
            raise SupabaseClientError(f"Failed to record alignment failure: {e}")


def get_supabase( parliament_id: str, audio_dirs: List[str], url: Optional[str] = None, key: Optional[str] = None, environment_file_path: Optional[str] = None) -> SupabaseClient:
    """
    Get a Supabase client instance.
    
    Args:
        url: Optional Supabase URL (uses environment variable if None)
        key: Optional Supabase API key (uses environment variable if None)
        environment_file_path: Optional path to environment file containing Supabase URL and key
        
    Returns:
        SupabaseClient instance
    """
    import os
    if environment_file_path:
        dotenv.load_dotenv(environment_file_path)
    
    url = url or os.environ.get('SUPABASE_URL')
    key = key or os.environ.get('SUPABASE_KEY')
    
    if not url or not key:
        raise ValueError("Supabase URL and key must be provided or set as environment variables (file path can be passed as environment_file_path)")
        
    return SupabaseClient(url, key, parliament_id, audio_dirs)