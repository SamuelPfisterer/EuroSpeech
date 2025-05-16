"""
Alignment Pipeline

This module contains the AlignmentPipeline class, which orchestrates the process
of aligning audio recordings with their corresponding transcripts.
"""

import csv
import json
import statistics
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Tuple, Callable

from ..audio_processing.segmenter import AudioSegmenter
from ..audio_processing.diarization import initialize_diarization_pipeline
from ..audio_processing.vad import initialize_vad_pipeline
from ..transcript.aligner import TranscriptAligner
from ..transcript.preprocessor import create_preprocessor
from ..data_models.models import TranscribedSegment, AlignedTranscript
from ..utils.io import save_alignments, save_transcribed_segments, load_transcribed_segments, get_alignment_stats

from ..utils.logging.supabase_logging import (
    get_supabase,
    SupabaseClient,
    SupabaseClientError,
    AlignmentMetrics
)

from typeguard import typechecked
import traceback
import logging


SUPABASE_URL = "https://jyrujzmpicrqjcdwfwwr.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imp5cnVqem1waWNycWpjZHdmd3dyIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzYwOTI3ODcsImV4cCI6MjA1MTY2ODc4N30.jzAOM2BFVAH25kZNfR4ownHYqRF_XXqpYq9DiERi-Lk"


class AlignmentPipeline:
    """
    Orchestrates the process of aligning audio recordings with transcripts.
    Handles the two-level selection:
    1. Select best modality for each transcript ID
    2. Select best transcript(s) among potential matches
    """
    
    def __init__(self, 
                 base_dir: str, 
                 csv_path: str, 
                 output_dir: str, 
                 cer_threshold: float = 0.3, 
                 multi_transcript_strategy: str = "best_only",
                 audio_dirs: Optional[List[str]] = None, 
                 transcript_dirs: Optional[List[str]] = None,
                 cache_dir: Optional[str] = None,
                 use_cache: bool = True,
                 hf_cache_dir: Optional[str] = None,
                 hf_token: Optional[str] = None,
                 delete_wav_files: bool = False,
                 wav_dir: Optional[Union[str, Path]] = None,
                 with_diarization: bool = False,
                 language: str = "en",
                 batch_size: int = 1,
                 abbreviations: Optional[Dict[str, str]] = {},
                 html_processor: Optional[Callable] = None,
                 supabase_logging_enabled: bool = True,
                 supabase_url: Optional[str] = SUPABASE_URL,
                 supabase_key: Optional[str] = SUPABASE_KEY,
                 supabase_environment_file_path: Optional[str] = None,
                 parliament_id: Optional[str] = None,
                 with_pydub_silences: bool = False):
        """
        Initialize the pipeline with configuration parameters.
        
        Args:
            base_dir: Root directory containing all data
            csv_path: Path to CSV metadata file
            output_dir: Directory to save alignment results
            cer_threshold: Maximum acceptable median CER
            multi_transcript_strategy: How to handle multiple transcripts
                ("best_only", "threshold_all", "force_all")
            audio_dirs: List of directories to search for audio files
            transcript_dirs: List of directories to search for transcript files
            cache_dir: Directory for caching results
            use_cache: Whether to use cached results
            hf_cache_dir: Directory for Hugging Face cache
            hf_token: Hugging Face token
            delete_wav_files: Whether to delete WAV that are created during segmentation by converting opus files
            wav_dir: Directory to save WAV files that are created during segmentation by converting opus files
            with_diarization: Whether to use diarization
            language: Audio language code using ISO 639-1 standard (default: "en" for English). Examples: "es" for Spanish, "fr" for French, "de" for German.
            batch_size: Number of segments the ASR model processes at once (default: 1, i.e. no batching, make sure to check how much VRAM is needed)
            abbreviations: Dictionary mapping abbreviations to their full forms
            html_processor: Custom function for processing HTML transcripts, must be of type Callable[[str, Dict], str], i.e. it takes a html string and a dictionary and returns a string
            supabase_logging_enabled: Whether to enable logging to Supabase
            supabase_url: Supabase URL
            supabase_key: Supabase key
            supabase_environment_file_path: Path to environment file containing Supabase URL and key
            parliament_id: Parliament ID
            with_pydub_silences: Whether to use pydub to detect silences, when no silences are detected with VAD (default: False)
        """
        self.base_dir = Path(base_dir)
        self.csv_path = Path(csv_path)
        self.output_dir = Path(output_dir)
        self.cer_threshold = cer_threshold
        self.multi_transcript_strategy = multi_transcript_strategy
        self.with_diarization = with_diarization
        self.language = language
        self.batch_size = batch_size
        self.abbreviations = abbreviations
        self.html_processor = html_processor
        self.supabase_logging_enabled = supabase_logging_enabled
        self.supabase_url = supabase_url
        self.supabase_key = supabase_key
        self.supabase_environment_file_path = supabase_environment_file_path
        self.parliament_id = parliament_id
        self.with_pydub_silences = with_pydub_silences
        # Default directories if not specified
        self.audio_dirs = audio_dirs or [
            "downloaded_audio/mp4_converted",
            "downloaded_audio/youtube_converted",
            "downloaded_audio/m3u8_streams",
            "downloaded_audio/generic_video",
            "downloaded_audio/mp3_audio",
            "downloaded_audio/processed_video"
        ]
        
        self.transcript_dirs = transcript_dirs or [
            "downloaded_transcript/pdf_transcripts",
            "downloaded_transcript/html_transcripts",
            "downloaded_transcript/dynamic_html_transcripts",
            "downloaded_transcript/processed_html_transcripts",
            "downloaded_transcript/processed_text_transcripts",
            "downloaded_transcript/doc_transcripts",
            "downloaded_subtitle/srt_subtitles"
        ]

        # supabase check
        self.supabase_client = None
        if supabase_logging_enabled:
            if not parliament_id:
                raise ValueError("parliament_id is required when using SupabaseClient")
            if not (supabase_url and supabase_key) and not supabase_environment_file_path:
                raise ValueError("supabase_url and supabase_key or supabase_environment_file_path is required when using SupabaseClient")
            self.supabase_client = get_supabase(
                url=self.supabase_url,
                key=self.supabase_key,
                environment_file_path=self.supabase_environment_file_path,
                parliament_id=parliament_id,
                audio_dirs=[str(self.base_dir / audio_dir) for audio_dir in self.audio_dirs]
            )
            # check if the parliament_id exist in the database

        
        self.cache_dir = Path(cache_dir) if cache_dir else self.output_dir / "cache"
        self.use_cache = use_cache

        self.hf_cache_dir = Path(hf_cache_dir) if hf_cache_dir else None
        self.hf_token = hf_token if hf_token else None

        self.delete_wav_files = delete_wav_files
        self.wav_dir = Path(wav_dir) if wav_dir else None
        
        # Initialize components
        self.audio_segmenter = self._initialize_audio_segmenter()
        self.transcript_aligner = TranscriptAligner()
        
        # Create output directories
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    
    def _initialize_audio_segmenter(self) -> AudioSegmenter:
        """Initialize the AudioSegmenter with VAD and diarization.
        
        Returns:
            AudioSegmenter instance
        """
        vad_pipeline = None #initialize_vad_pipeline(hf_cache_dir=self.hf_cache_dir, hf_token=self.hf_token)
        diarization_pipeline = None # initialize_diarization_pipeline(hf_cache_dir=self.hf_cache_dir, hf_token=self.hf_token)
        logging.warning("Diarization pipeline and VAD pipeline not initialized!!! We did this because of the weights only problem")
        return AudioSegmenter(vad_pipeline, diarization_pipeline, hf_cache_dir=self.hf_cache_dir, with_diarization=self.with_diarization, language=self.language, batch_size=self.batch_size, supabase_client=self.supabase_client, with_pydub_silences=self.with_pydub_silences, wav_directory=self.wav_dir, delete_wav_files=self.delete_wav_files)
    
    def _load_csv_metadata(self) -> Dict[str, List[str]]:
        """
        Load and parse the CSV metadata file.
        
        Returns:
            A dictionary mapping video_ids to potential transcript_ids.

        Raises:
            ValueError: If no video_id or transcript_id is found for a row.
        """
        metadata = {}
        
        with open(self.csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Extract video_id and transcript_id based on CSV format
                video_id = row.get('video_id')
                transcript_id = row.get('transcript_id')
                
                # If video_id is not present, transcript_id is the video_id
                if not video_id:
                    if not transcript_id:
                        raise ValueError(f"No video_id or transcript_id found for row: {row}")
                    video_id = transcript_id
                
                if video_id:
                    if video_id not in metadata:
                        metadata[video_id] = []
                    
                    if transcript_id:
                        # If transcript_id and video_id, we have to try transcript_id or f"{video_id}_{transcript_id}"
                        metadata[video_id].append(transcript_id)
                        metadata[video_id].append(f"{video_id}_{transcript_id}")
                    elif video_id not in metadata[video_id]:
                        metadata[video_id].append(video_id)
        
        return metadata
    
    def _extract_id_from_url(self, url: str) -> Optional[str]:
        """
        Extract ID from URL if needed.
        
        Args:
            url: The URL to extract ID from
            
        Returns:
            Extracted ID or None if extraction fails
        """
        # This is a simplified example, actual implementation may vary
        # based on the specific URL patterns in the dataset
        if not url:
            return None
            
        # Extract the last component of the URL path
        parts = url.rstrip('/').split('/')
        if parts:
            return parts[-1]
            
        return None
    
    def _find_audio_file(self, video_id: str) -> Optional[Path]:
        """
        Find the audio file for a given video_id.
        
        Args:
            video_id: The video ID to search for
            
        Returns:
            The path to the audio file or None if not found
        """
        for audio_dir in self.audio_dirs:
            full_dir = self.base_dir / audio_dir
            if not full_dir.exists():
                continue
                
            # Check for opus file
            file_path = full_dir / f"{video_id}.opus"
            if file_path.exists():
                return file_path
        
        return None
    
    def _find_transcript_files(self, transcript_id: str) -> Dict[str, Path]:
        """
        Find all transcript files for a given transcript_id across all formats.
        
        Args:
            transcript_id: The transcript ID to search for
            
        Returns:
            A dictionary mapping format to file path
        """
        transcript_files = {}

        found_valid_transcript_directory = False
        valid_extensions = ['.pdf', '.html', '.txt', '.srt', '.docx', '.doc']
        
        for transcript_dir in self.transcript_dirs:
            full_dir = self.base_dir / transcript_dir
            if not full_dir.exists():
                continue
            
            found_valid_transcript_directory = True
            # Check for different format extensions
            for ext in valid_extensions:
                file_path = full_dir / f"{transcript_id}{ext}"
                if file_path.exists():
                    format_type = ext[1:]  # Remove the dot
                    transcript_files[format_type] = file_path

        if not found_valid_transcript_directory:
            print(f"No valid transcript directory found for {transcript_id}")

        if not transcript_files:
            print(f"No transcript files found for {transcript_id}. Searched {valid_extensions}")
        
        return transcript_files
    
    def _get_cache_path(self, video_id: str) -> Path:
        """
        Get the path for cached segmentation results.
        
        Args:
            video_id: The video ID
            
        Returns:
            Path to the cache file
        """
        return self.cache_dir / f"{video_id}_segments.pkl"
    
    def _segment_audio(self, audio_path: Path, video_id: str) -> List[TranscribedSegment]:
        """
        Segment audio and transcribe, using cache if available.
        
        Args:
            audio_path: Path to the audio file
            video_id: The video ID for caching
            
        Returns:
            List of transcribed segments
        """
        cache_path = self._get_cache_path(video_id)
        
        if self.use_cache and cache_path.exists():
            print(f"Using cached segments for {video_id}")
            return load_transcribed_segments(cache_path)
        
        print(f"Segmenting audio for {video_id}")
        # Segment and transcribe
        segments = self.audio_segmenter.segment_and_transcribe(str(audio_path), video_id=video_id)
        
        # Cache results
        print(f"Caching segments for {video_id}")
        save_transcribed_segments(segments, cache_path)
        
        return segments
    
    def _preprocess_transcript(self, transcript_path: Path, format_type: str) -> str:
        """
        Preprocess a transcript file using appropriate preprocessor.
        
        Args:
            transcript_path: Path to the transcript file
            format_type: The format type (pdf, html, txt, srt)
            
        Returns:
            The preprocessed text
        """
        print(f"Preprocessing {format_type} transcript: {transcript_path}")
        
        # Create preprocessor config
        config = {}
        
        # Add HTML processor to config if available and this is an HTML file
        if format_type == 'html' and self.html_processor:
            config['html_processor'] = self.html_processor
            print(f"Using custom HTML processor for {transcript_path}")
        
        # Use the factory to create an appropriate preprocessor
        preprocessor = create_preprocessor(str(transcript_path), config=config)
        if self.abbreviations:
            preprocessor.abbreviations = self.abbreviations
        
        # Preprocess the transcript
        return preprocessor.preprocess(str(transcript_path))
    
    def _calculate_median_cer(self, aligned_segments: List[AlignedTranscript]) -> float:
        """
        Calculate the median CER from aligned segments.
        
        Args:
            aligned_segments: List of aligned transcript segments
            
        Returns:
            Median CER value
        """
        if not aligned_segments:
            return 1.0  # Worst possible CER
            
        cers = [segment.cer for segment in aligned_segments]
        return statistics.median(cers)
    
    def _align_transcript(self, segments: List[TranscribedSegment], transcript_text: str) -> List[AlignedTranscript]:
        """
        Align transcribed segments with a transcript.
        
        Args:
            segments: List of transcribed segments
            transcript_text: The preprocessed transcript text
            
        Returns:
            List of aligned transcript segments
        """
        print(f"Aligning transcript with {len(segments)} segments")
        try:
            return self.transcript_aligner.align_transcript(segments, transcript_text)
        except Exception as e:
            print(f"Error aligning transcript: {e}")
            traceback.print_exc()
            raise e
    
    def _process_single_audio(self, video_id: str, metadata: Dict[str, List[str]]) -> Optional[Dict[str, Any]]:
        """
        Process a single audio file and its potential transcripts.
        Implements the two-level selection process.
        
        Args:
            video_id: The video ID to process
            metadata: The metadata dictionary
            
        Returns:
            Results dictionary or None if processing failed
        """
        print(f"\nProcessing audio file for video_id: {video_id}")
        
        # Find audio file
        audio_path = self._find_audio_file(video_id)
        if not audio_path:
            print(f"Audio file not found for video_id: {video_id}")
            return None
            
        print(f"Found audio file: {audio_path}")
            
        # Get potential transcript IDs
        transcript_ids = metadata.get(video_id, [])
        if not transcript_ids:
            print(f"No transcript IDs found for video_id: {video_id}")
            return None
            
        print(f"Found {len(transcript_ids)} potential transcript IDs")
            
        # Segment audio
        audio_segments = self._segment_audio(audio_path, video_id)
        
        # Level 1: Find best modality for each transcript ID
        best_modalities = {}
        
        for transcript_id in transcript_ids:
            print(f"\nProcessing transcript_id: {transcript_id}")
            
            # Find all format modalities
            transcript_files = self._find_transcript_files(transcript_id)
            
            if not transcript_files:
                print(f"No transcript files found for transcript_id: {transcript_id}")
                continue
                
            print(f"Found {len(transcript_files)} format modalities: {', '.join(transcript_files.keys())}")
                
            # Process each modality
            best_cer = 1.0
            best_aligned = None
            best_format = None
            
            for format_type, file_path in transcript_files.items():
                print(f"Processing {format_type} format")
                
                # Preprocess transcript
                transcript_text = self._preprocess_transcript(file_path, format_type)
                
                # Align with audio segments
                aligned_segments = self._align_transcript(audio_segments, transcript_text)

                # remove all none elements from aligned_segments
                aligned_segments = [segment for segment in aligned_segments if segment is not None]
                #TODO: maybe we should add logging here if we have removed many elements
                
                # Calculate CER
                median_cer = self._calculate_median_cer(aligned_segments)
                print(f"Median CER for {format_type}: {median_cer:.4f}")
                
                # Check if this is the best modality so far
                if median_cer < best_cer:
                    best_cer = median_cer
                    best_aligned = aligned_segments
                    best_format = format_type
            
            # Store best modality
            if best_aligned:
                print(f"Best modality for {transcript_id}: {best_format} with CER {best_cer:.4f}")
                best_modalities[transcript_id] = {
                    'cer': best_cer,
                    'aligned_segments': best_aligned,
                    'format': best_format
                }
        
        if not best_modalities:
            print(f"No valid alignments found for any transcript")
            return None
        
        # Level 2: Select best transcript(s) across all transcript IDs
        selected_transcripts = []
        
        print("\nSelecting best transcript(s) using strategy:", self.multi_transcript_strategy)
        
        if self.multi_transcript_strategy == "best_only":
            # Find transcript with lowest CER
            best_transcript_id = min(
                best_modalities, 
                key=lambda tid: best_modalities[tid]['cer'],
                default=None
            )
            
            if best_transcript_id and best_modalities[best_transcript_id]['cer'] <= self.cer_threshold:
                print(f"Selected best transcript: {best_transcript_id} with CER {best_modalities[best_transcript_id]['cer']:.4f}")
                selected_transcripts.append({
                    'transcript_id': best_transcript_id,
                    **best_modalities[best_transcript_id]
                })
            else:
                print("No transcript met the CER threshold")
                
        elif self.multi_transcript_strategy == "threshold_all":
            # Keep all transcripts below threshold
            for tid, data in best_modalities.items():
                if data['cer'] <= self.cer_threshold:
                    print(f"Selected transcript: {tid} with CER {data['cer']:.4f}")
                    selected_transcripts.append({
                        'transcript_id': tid,
                        **data
                    })
            
            if not selected_transcripts:
                print("No transcript met the CER threshold")
                    
        elif self.multi_transcript_strategy == "force_all":
            # Keep all transcripts
            for tid, data in best_modalities.items():
                print(f"Selected transcript: {tid} with CER {data['cer']:.4f}")
                selected_transcripts.append({
                    'transcript_id': tid,
                    **data
                })
        
        if not selected_transcripts:
            print("No transcripts were selected")
            return None
        
        # Save results
        results = {
            'video_id': video_id,
            'audio_path': str(audio_path),
            'selected_transcripts': selected_transcripts
        } 
        
        self._save_results(video_id, results)

        if self.supabase_client:
            transcript_paths = [f"{self.output_dir}/{video_id}_{transcript_data['transcript_id']}_aligned.json" for transcript_data in results['selected_transcripts']] # depends on _save_results
            metrics = get_alignment_stats(transcript_paths)
            self.supabase_client.complete_video_alignment(video_id, metrics)

        return results
    
    def _save_results(self, video_id: str, results: Dict[str, Any]) -> None:
        """
        Save alignment results to output directory.
        
        Args:
            video_id: The video ID
            results: The results dictionary
        """
        # Create a copy of results without the aligned_segments for the summary file
        summary_results = {
            'video_id': results['video_id'],
            'audio_path': results['audio_path'],
            'selected_transcripts': []
        }
        
        for transcript_data in results['selected_transcripts']:
            # Store the aligned segments separately
            aligned_segments = transcript_data['aligned_segments']
            transcript_id = transcript_data['transcript_id']
            
            # Add a summary to the main results file (without the actual segments)
            summary_transcript = transcript_data.copy()
            summary_transcript.pop('aligned_segments')
            summary_transcript['segment_count'] = len(aligned_segments)
            summary_results['selected_transcripts'].append(summary_transcript)
            
            # Save individual alignment file
            alignment_path = self.output_dir / f"{video_id}_{transcript_id}_aligned.json"
            print(f"Saving alignment for {transcript_id} to {alignment_path}")
            save_alignments(aligned_segments, results['audio_path'], str(alignment_path))
        
        # Save the summary results
        output_path = self.output_dir / f"{video_id}_alignment_summary.json"
        print(f"Saving summary results to {output_path}")
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(summary_results, f, indent=2, ensure_ascii=False)
    
    def process_all(self) -> None:
        """Process all audio files found in the metadata."""
        print(f"Loading metadata from {self.csv_path}")
        metadata = self._load_csv_metadata()
        
        print(f"Found {len(metadata)} video IDs in metadata")

        
        for video_id in metadata:
            if self.supabase_client:
                is_new = self.supabase_client.start_video_alignment(video_id)
                if not is_new:
                    print(f"Video {video_id} already exists in the database, skipping")
                    continue

            try:
                self._process_single_audio(video_id, metadata)
            except Exception as e:
                print(f"Error processing video {video_id}: {e}")
                traceback.print_exc()
                if self.supabase_client:
                    self.supabase_client.fail_video_alignment(video_id, str(e))
                # Continue with next video
    
    @typechecked
    def process_subset(self, video_ids: List[str]) -> None:
        """
        Process only a subset of video IDs.
        
        Args:
            video_ids: List of video IDs to process
        """
        print(f"Loading metadata from {self.csv_path}")
        metadata = self._load_csv_metadata()
        print(f"Found {len(metadata)} video IDs in metadata")
        
        
        
        for video_id in video_ids:
            if video_id in metadata:
                if self.supabase_client:
                    self.supabase_client.start_video_alignment(video_id) # we might check if the video_id already exists in the database, whcih is supported by start_video_alignment
                try:
                    self._process_single_audio(video_id, metadata)
                except Exception as e:
                    print(f"Error processing video {video_id}: {e}")
                    traceback.print_exc()
                    if self.supabase_client:
                        self.supabase_client.fail_video_alignment(video_id, str(e))
            else:
                print(f"Video ID {video_id} not found in metadata")
