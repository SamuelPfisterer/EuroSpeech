from typing import List, Optional, Union
import os
import warnings
from pathlib import Path
import torch
from pyannote.audio.pipelines import VoiceActivityDetection
from pyannote.core import Segment, Timeline
from pyannote.audio import Pipeline
from transformers import pipeline, AutoModelForSpeechSeq2Seq, AutoProcessor
from pydub import AudioSegment
from pydub import silence  # Added this import for silence detection
import numpy as np
from tqdm import tqdm  # Added tqdm for progress bar
import time
import logging
import shutil
from ..data_models.models import TranscribedSegment
from ..audio_processing.vad.silero_vad import get_silero_vad  # Import get_silero_vad directly
from ..utils.logging.supabase_logging import SupabaseClient

class AudioSegmenter:
    def __init__(self, 
                 vad_pipeline: VoiceActivityDetection, 
                 diarization_pipeline: Pipeline, 
                 window_min_size: float = 10.0, 
                 window_max_size: float = 20.0,
                 hf_cache_dir: Optional[Union[Path, str]] = None,
                 delete_wav_files: bool = True,
                 wav_directory: Optional[Union[Path, str]] = None,
                 with_diarization: bool = False,
                 language: str = "en",
                 batch_size: int = 1,
                 supabase_client: Optional[SupabaseClient] = None,
                 with_pydub_silences: bool = False,
                 temp_directory: Optional[Union[Path, str]] = None):
        """Initialize the AudioSegmenter.
        
        Args:
            vad_pipeline: PyAnnote VAD pipeline
            diarization_pipeline: PyAnnote diarization pipeline
            window_min_size: Minimum size of the window to look for silence in seconds
            window_max_size: Maximum size of the window to look for silence in seconds
            hf_cache_dir: Optional directory for Hugging Face cache
            delete_wav_files: Whether to delete temporary WAV files after processing (default: False)
            wav_directory: Optional directory to store WAV files (default: same directory as audio file)
            with_diarization: Whether to use diarization (default: False)
            language: Audio language code using ISO 639-1 standard (default: "en" for English). Examples: "es" for Spanish, "fr" for French, "de" for German.
            batch_size: Number of segments the ASR model processes at once (default: 1, i.e. no batching, make sure to check how much VRAM is needed)
            with_pydub_silences: Whether to use pydub to detect silences, when no silences are detected with VAD (default: False)
            temp_directory: Optional directory for temporary files (default: system temp directory)
        """
        self.vad_pipeline = vad_pipeline
        self.diarization_pipeline = diarization_pipeline
        self.window_min_size = window_min_size
        self.window_max_size = window_max_size
        self.with_diarization = with_diarization
        self.language = language
        self.batch_size = batch_size
        self.supabase_client = supabase_client
        self.with_pydub_silences = with_pydub_silences
        self.wav_directory = wav_directory
        self.temp_directory = Path(temp_directory) if temp_directory else Path("/tmp/") 
        self.temp_directory.mkdir(parents=True, exist_ok=True)
        
        # Set cache directory for Hugging Face
        hf_cache_dir = hf_cache_dir if hf_cache_dir is not None else os.getenv("HF_CACHE_DIR")
        
        # Set environment variable to ensure HF uses the correct cache
        if hf_cache_dir is not None:
            os.environ['HF_HOME'] = str(hf_cache_dir)
            os.environ['TRANSFORMERS_CACHE'] = str(hf_cache_dir)
            os.environ['TORCH_HOME'] = str(hf_cache_dir)
        else:
            warnings.warn("No cache directory provided, using default cache directory")
            print("No cache directory provided, using default cache directory")

        #model_name = "openai/whisper-large-v3"
        #model_name = "distil-whisper/distil-large-v3"
        #model_name = "distil-whisper/distil-large-v3.5" # doesn't support languages other than English unfortunatelly
        model_name = "openai/whisper-large-v3-turbo"

        # Load the model and processor with cache_dir
        model = AutoModelForSpeechSeq2Seq.from_pretrained(
            model_name,
            #torch_dtype=torch.float16,
            low_cpu_mem_usage=True,
            #attn_implementation="flash_attention_2",
            cache_dir=hf_cache_dir,
            device_map="cuda" if torch.cuda.is_available() else "cpu"
        )

        processor = AutoProcessor.from_pretrained(
            model_name,
            cache_dir=hf_cache_dir
        )

        # Create the pipeline using the loaded model and processor
        print(f"Using language: {self.language}")
        self.asr_pipeline = pipeline(
            "automatic-speech-recognition",
            model=model,
            tokenizer=processor.tokenizer,
            feature_extractor=processor.feature_extractor,
            generate_kwargs={"language": self.language},
            batch_size=self.batch_size
        )
        
        self.delete_wav_files = delete_wav_files
        self.wav_directory = Path(wav_directory) if wav_directory is not None else None
        
        # Set up logging
        self.logger = logging.getLogger(__name__)
        
    def get_longest_silence(self, 
                          non_speech_regions: Timeline, 
                          start: float, 
                          end: float) -> Optional[Segment]:
        """Get the longest silence segment in the given time window.
        
        Args:
            non_speech_regions: Timeline containing non-speech segments
            start: Start time of window to search in
            end: End time of window to search in
            
        Returns:
            The longest silence segment in the window, or None if no silence found
        """
        # Create a support segment for the window we're analyzing
        support = Segment(start, end)
        
        # Get all silence segments in this window
        window_silences = non_speech_regions.crop(support=support, mode="intersection")
        
        # Find the longest silence segment
        if not window_silences:
            return None
            
        return max(window_silences, key=lambda s: s.duration)

    def convert_audio_to_wav(self, audio_path: str) -> str:
        """Convert audio file to wav format using ffmpeg if needed.
        
        Args:
            audio_path: Path to audio file (.opus or .wav)
            
        Returns:
            Path to wav file
        """
        if not audio_path.endswith(('.opus', '.wav')):
            raise ValueError("Audio file must be .opus or .wav format")
        
        if audio_path.endswith('.wav'):
            return audio_path
        
        if self.wav_directory:
            self.wav_directory.mkdir(parents=True, exist_ok=True)
            wav_path = str(self.wav_directory / Path(audio_path).with_suffix('.wav').name)
        else:
            wav_path = str(Path(audio_path).with_suffix('.wav'))
        
        if not os.path.exists(wav_path):
            print(f"Converting {audio_path} to {wav_path}")
            cmd = f'ffmpeg -y -i {audio_path} -ac 1 -ar 16000 {wav_path}'
            os.system(cmd)
        
        return wav_path

    def _check_disk_space(self, required_mb: int = 100) -> bool:
        """Check if there's enough disk space in temp directory.
        
        Args:
            required_mb: Required space in megabytes
            
        Returns:
            bool: True if enough space available, False otherwise
        """
        try:
            total, used, free = shutil.disk_usage(self.temp_directory)
            free_mb = free // (1024 * 1024)  # Convert to MB
            used_mb = used // (1024 * 1024)  # Convert to MB
            total_mb = total // (1024 * 1024)  # Convert to MB
            self.logger.info(f"Available disk space in temp directory: {free_mb}MB. Used: {used_mb}MB. Total: {total_mb}MB")
            if free_mb < required_mb:
                self.logger.error(f"Insufficient disk space. Only {free_mb}MB available, need {required_mb}MB")
                return False
            return True
        except Exception as e:
            self.logger.error(f"Error checking disk space: {e}")
            return False

    def extract_audio_segment(self, audio_path: str, start: float, end: float) -> str:
        """Extract a segment from an audio file and return a temporary path.
        
        Args:
            audio_path: Path to audio file (.opus or .wav)
            start: Start time in seconds
            end: End time in seconds
            
        Returns:
            Path to temporary wav file containing the segment
        """
        try:
            # Check disk space before proceeding
            segment_duration = end - start
            estimated_size_mb = int(segment_duration * 32)  # Rough estimate: 32KB per second
            if not self._check_disk_space(estimated_size_mb):
                raise OSError(f"Insufficient disk space for audio segment (need ~{estimated_size_mb}MB)")
            
            # Convert to wav if needed
            wav_path = self.convert_audio_to_wav(audio_path)
            
            audio = AudioSegment.from_file(wav_path)
            segment = audio[start * 1000:end * 1000]  # pydub works in milliseconds
            
            # Use temp_directory instead of /tmp
            temp_path = str(self.temp_directory / f"segment_{start}_{end}.wav")
            self.logger.debug(f"Creating temporary segment file: {temp_path}")
            
            segment.export(temp_path, format="wav")
            return temp_path
            
        except Exception as e:
            self.logger.error(f"Error extracting audio segment: {e}")
            raise

    def segment_and_transcribe(self, audio_path: str, video_id: Optional[str] = None) -> List[TranscribedSegment]:
        """Segment audio file and transcribe each segment.
        
        Args:
            audio_path: Path to audio file
            
        Returns:
            List of TranscribedSegments containing timing and text
        """
        converted_wav_path = None
        temp_paths = []
        
        try:
            # Convert to WAV if needed
            print(f"Converting audio file to wav before segmenting: {audio_path}")
            converted_wav_path = self.convert_audio_to_wav(audio_path)

            if self.supabase_client:
                if video_id is None:
                    raise ValueError("video_id is required when using SupabaseClient")
                self.supabase_client.update_transcribing_start(video_id)
            segmentation_start_time = time.time()    
            
            segments_timeline = self.segment_audio(converted_wav_path)

            segmentation_duration = time.time() - segmentation_start_time

            print(f"Segmentation duration: {segmentation_duration} seconds")

            if self.supabase_client:
                if video_id is None:
                    raise ValueError("video_id is required when using SupabaseClient")
                self.supabase_client.update_segmentation_complete(video_id, segmentation_duration, len(segments_timeline))



            if self.supabase_client: 
                if video_id is None:
                    raise ValueError("video_id is required when using SupabaseClient")
                self.supabase_client.update_transcribing_start(video_id)
            transcribing_start_time = time.time()

            transcribed_segments = []

            if self.batch_size > 1:
                try:
                    temp_paths = [ self.extract_audio_segment(converted_wav_path, segment.start, segment.end) for segment in segments_timeline]
                    for i in tqdm(range(0, len(temp_paths), self.batch_size), desc="Batch Transcribing Segments with Batch Size of {self.batch_size}", mininterval=60.0):
                        batch_temp_paths = temp_paths[i:i+self.batch_size]
                        results = self.asr_pipeline(
                            batch_temp_paths,
                            return_timestamps=False  # Faster than word-level timestamps
                        )

                        # Cleanup and result mapping
                        for temp_path, result in zip(batch_temp_paths, results):
                            os.remove(temp_path)
                            text = result["text"].strip()
                            transcribed_segments.append(TranscribedSegment(segments_timeline[i], text))
                            i += 1
                except Exception as e:
                    print(f"Error transcribing segments: {e}")
                    raise e
                finally:
                    for temp_path in temp_paths:
                        if temp_path and os.path.exists(temp_path):
                            os.remove(temp_path)
            else:
                # Use tqdm to create a progress bar for segment processing
                for segment in tqdm(segments_timeline, desc="Transcribing segments", unit="segment", mininterval=60.0):
                    try:
                        temp_path = self.extract_audio_segment(converted_wav_path, segment.start, segment.end)
                        text = self.asr_pipeline(temp_path)["text"].strip()
                    
                        # Clean up
                        os.remove(temp_path)
                        
                        transcribed_segments.append(TranscribedSegment(segment, text))
                    except Exception as e:
                        print(f"Error transcribing segment: {e}")
                        raise e
                    finally:
                        if temp_path and os.path.exists(temp_path):
                            os.remove(temp_path)
            
            transcribing_duration = time.time() - transcribing_start_time
            print(f"Transcribing duration: {transcribing_duration} seconds")

            if self.supabase_client:
                if video_id is None:
                    raise ValueError("video_id is required when using SupabaseClient")
                self.supabase_client.update_transcribing_complete(video_id, transcribing_duration)

            return transcribed_segments
        finally:
            # Clean up the converted WAV file if needed
            if self.delete_wav_files and converted_wav_path and converted_wav_path != audio_path:
                os.remove(converted_wav_path)

    def segment_audio(self, audio_path: str) -> Timeline:
        """Segment audio file based on silence detection.
        
        Args:
            audio_path: Path to audio file
            
        Returns:
            Timeline containing all segments
        """
        # Get speech regions for the entire audio
        print(f"Segmenting audio file: {audio_path}")
        
        # Using PyAnnote VAD
        #speech_regions = self.vad_pipeline(audio_path)
        
        # Instead of deriving non_speech_regions from PyAnnote, use Silero VAD directly
        # non_speech_regions = speech_regions.get_timeline().gaps()
        non_speech_regions = get_silero_vad(audio_path)
        
        if self.with_diarization:
            diarization = self.diarization_pipeline(audio_path)
            overlapping_speaker_segments = diarization.get_overlap()
        else:
            diarization = None
            overlapping_speaker_segments = None
        
        audio = AudioSegment.from_file(audio_path)
        audio = audio.normalize(headroom=5)
        silence_threshold = np.percentile([frame.rms for frame in audio[::100]], 15)
        if self.with_pydub_silences:
            silences = silence.detect_silence(audio, min_silence_len=200, silence_thresh=silence_threshold, seek_step=15)
            silence_regions = Timeline([Segment(start/1000, end/1000) for start, end in silences])
        else:
            silence_regions = None
        
        segments = Timeline()

        # TODO: I think we don't need this necessarily as we should skip full silences anyways
        """
        # Skip initial silence
        current_pos = speech_regions.get_timeline().extent().start
        # Skip the last silence
        audio_end = speech_regions.get_timeline().extent().end
        """
        current_pos = non_speech_regions.extent().start
        audio_end = non_speech_regions.extent().end
        
        while current_pos < audio_end:
            # Define the window we're looking at
            window_start = current_pos + self.window_min_size
            window_end = current_pos + self.window_max_size

            # Check if the window only contains silence
            max_segment_silence = self.get_longest_silence(
                non_speech_regions, 
                current_pos, 
                window_end
            )
            if max_segment_silence and max_segment_silence.start == current_pos and max_segment_silence.duration > self.window_min_size:
                # If the segment we are checking only contains silence, skip it
                current_pos = max_segment_silence.end
                continue
            
            # Check if the segment starts with an overlapping speaker segment
            if overlapping_speaker_segments and diarization:
                overlapping_speaker_segments_window_start = overlapping_speaker_segments.crop(
                    Segment(current_pos, window_end), 
                    mode="loose"
                )
                if overlapping_speaker_segments_window_start:
                    # If there is an overlapping speaker segment, move to its end
                    current_pos = overlapping_speaker_segments_window_start[0].end + 1e-6
                    continue

                # Check if there is a speaker change in this segment
                overlapping_segments = diarization.crop(
                    Segment(current_pos, window_end), 
                    mode="intersection"
                )
                last_speaker = None
                speaker_change_detected = False
            
                # Iterate through speaker segments
                for segment, track, label in overlapping_segments.itertracks(yield_label=True):
                    if last_speaker is None:
                        last_speaker = label
                    elif label != last_speaker:
                        segments.add(Segment(current_pos, segment.start))
                        current_pos = segment.start
                        speaker_change_detected = True
                        break
                        
                if speaker_change_detected:
                    continue
                
            # Get the longest silence in this window
            max_silence = self.get_longest_silence(
                non_speech_regions, 
                window_start, 
                window_end
            )
            
            if max_silence is None:
                if self.with_pydub_silences and silence_regions:
                    # If no silence found with pyannote, try pydub
                    max_silence = self.get_longest_silence(
                        silence_regions, 
                        window_start, 
                        window_end
                    )
                if max_silence is None:
                    # If no silence found with pydub, add the whole window
                    segments.add(Segment(current_pos, window_end))
                    current_pos = window_end
                else:
                    # End segment at middle of silence
                    silence_middle = max_silence.middle
                    segments.add(Segment(current_pos, silence_middle))
                    current_pos = silence_middle
            else:
                # End segment at middle of silence
                silence_middle = max_silence.middle
                segments.add(Segment(current_pos, silence_middle))
                current_pos = silence_middle
                
        return segments 