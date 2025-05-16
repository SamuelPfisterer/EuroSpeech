from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional
from pyannote.core import Segment

@dataclass
class TranscribedSegment:
    segment: Segment   
    text: str
    
    # Convenience properties to access segment attributes
    @property
    def start(self) -> float:
        return self.segment.start
        
    @property
    def end(self) -> float:
        return self.segment.end
        
    @property
    def duration(self) -> float:
        return self.segment.duration
        
    def __str__(self) -> str:
        return f"[{self.start:.1f}s → {self.end:.1f}s] {self.text}"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "start": self.start,
            "end": self.end,
            "text": self.text
        }

@dataclass
class AlignedTranscript:
    """Represents an aligned segment between ASR and human transcript."""
    asr_segment: TranscribedSegment
    human_text: str
    start_idx: int  # Token index in human transcript
    end_idx: int    # Token index in human transcript
    cer: float
    
    # Convenience properties to access ASR segment timing
    @property
    def start(self) -> float:
        return self.asr_segment.start
        
    @property
    def end(self) -> float:
        return self.asr_segment.end
        
    @property
    def duration(self) -> float:
        return self.asr_segment.duration
        
    @property
    def asr_text(self) -> str:
        return self.asr_segment.text
    
    def __str__(self) -> str:
        return (f"[{self.start:.1f}s → {self.end:.1f}s]\n"
                f"ASR: {self.asr_text}\n"
                f"Human: {self.human_text}\n"
                f"CER: {self.cer:.3f}")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "start": self.start,
            "end": self.end,
            "asr_text": self.asr_text,
            "human_text": self.human_text,
            "cer": self.cer,
            "start_idx": self.start_idx,
            "end_idx": self.end_idx
        }