import torch
from pyannote.core import Segment, Timeline
from pydub import AudioSegment
from typing import Optional
from pydub.silence import detect_silence

def get_silero_vad(audio_path: str, 
                   threshold: float = 0.5, 
                   min_silence_duration_ms: int = 10) -> Timeline:
    """Initialize and run Silero VAD on audio file.
    
    Args:
        audio_path: Path to audio file
        threshold: Speech probability threshold
        min_silence_duration_ms: Minimum silence duration in milliseconds
        
    Returns:
        Timeline containing non-speech regions
    """
    # Load Silero VAD model
    model, utils = torch.hub.load(repo_or_dir='snakers4/silero-vad',
                                model='silero_vad',
                                force_reload=False)
    
    (get_speech_timestamps, _, read_audio, _, _) = utils
    
    # Load audio
    sampling_rate = 16000
    wav = read_audio(audio_path, sampling_rate=sampling_rate)
    
    # Get speech timestamps
    speech_timestamps = get_speech_timestamps(
        wav, 
        model, 
        threshold=threshold,
        sampling_rate=sampling_rate,
        min_silence_duration_ms=min_silence_duration_ms
    )
    
    # Convert to non-speech regions (silence)
    non_speech_regions = Timeline()
    
    # Get audio duration
    audio = AudioSegment.from_file(audio_path)
    audio_duration = len(audio) / 1000  # in seconds
    
    # First silence if needed
    if speech_timestamps and speech_timestamps[0]['start'] > 0:
        non_speech_regions.add(Segment(0, speech_timestamps[0]['start'] / sampling_rate))
    
    # Middle silences
    for i in range(len(speech_timestamps) - 1):
        silence_start = speech_timestamps[i]['end'] / sampling_rate
        silence_end = speech_timestamps[i + 1]['start'] / sampling_rate
        non_speech_regions.add(Segment(silence_start, silence_end))
    
    # Final silence if needed
    if speech_timestamps:
        last_end = speech_timestamps[-1]['end'] / sampling_rate
        if last_end < audio_duration:
            non_speech_regions.add(Segment(last_end, audio_duration))
    
    return non_speech_regions 