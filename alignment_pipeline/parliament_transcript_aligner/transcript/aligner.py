from typing import List, Optional, Dict, Any
import Levenshtein
from tqdm import tqdm
import heapq

from ..data_models.models import TranscribedSegment, AlignedTranscript

class TranscriptAligner:
    def __init__(self, 
                 window_token_margin: int = 30,
                 region_cer_threshold: float = 0.3,
                 finetune_cer_threshold: float = 0.05):
        """Initialize the TranscriptAligner.
        
        Args:
            window_token_margin: Extra tokens to consider on each side of the window
            region_cer_threshold: Maximum allowable Character Error Rate for a region to be considered a good match
            finetune_cer_threshold: Maximum allowable Character Error Rate for early stopping during fine-tuning
        """
        self.window_token_margin = window_token_margin
        self.region_cer_threshold = region_cer_threshold
        self.finetune_cer_threshold = finetune_cer_threshold
        
    def compute_cer(self, asr_text: str, human_text: str) -> float:
        """Compute Character Error Rate between two strings.
        
        Args:
            text1: First text string
            text2: Second text string
            
        Returns:
            Character Error Rate between 0 and 1
        """
        distance = Levenshtein.distance(asr_text, human_text)
        asr_len = len(asr_text)  # Length of ASR text. We use this as baseline length for CER
        return distance / asr_len if asr_len > 0 else 1.0
        
    def find_best_match(self, 
                       asr_segment: TranscribedSegment,
                       transcript_tokens: List[str],
                       start_search_idx: int = 0) -> AlignedTranscript:
        """Find best matching segment in human transcript for ASR segment.
        
        Uses a two-phase approach:
        1. Find the most promising region in the transcript
        2. Fine-tune the exact match boundaries within that region
        
        Args:
            asr_segment: TranscribedSegment from ASR
            transcript_tokens: Tokenized human transcript
            start_search_idx: Index to start searching from
            
        Returns:
            AlignedTranscript containing the best match
        """
        # Phase 1: Find the best matching region
        region_start_idxs = self._find_match_region(
            asr_segment.text,
            transcript_tokens,
            start_search_idx, 
            coarse_window_size=len(asr_segment.text.split())
        )
        
        best_matches = []
        for region_start_idx in region_start_idxs:
            best_match = self._fine_tune_match(asr_segment, transcript_tokens, region_start_idx)
            if not best_match:
                #TODO: maybe we should add some logging here
                continue
            if best_match.cer <= self.region_cer_threshold:
                best_matches.append(best_match)
                
        if best_matches:
            return min(best_matches, key=lambda x: x.cer)
            
        # No good matching region found, try from beginning
        region_start_idxs = self._find_match_region(
            asr_segment.text,
            transcript_tokens,
            0,
            coarse_window_size=len(asr_segment.text.split()),
        )
        
        best_matches = []
        for region_start_idx in region_start_idxs:
            best_match = self._fine_tune_match(asr_segment, transcript_tokens, region_start_idx)
            if not best_match:
                #TODO: maybe we should add some logging here
                continue
            if best_match.cer <= self.region_cer_threshold * 1.5:
                best_matches.append(best_match)
                
        if best_matches:
            return min(best_matches, key=lambda x: x.cer)

        # No good matching region found, create fallback alignment
        return self._create_fallback_alignment(asr_segment, transcript_tokens, start_search_idx)

    def _find_match_region(self,
                          asr_text: str,
                          transcript_tokens: List[str],
                          start_search_idx: int,
                          coarse_window_size: int = 50,
                          region_cer_threshold: float = 0.3,
                          max_backward_search: int = 250,
                          forward_priority: int = 5,
                          step_size: float = 0.5,
                          top_k: int = 3) -> List[int]:
        """Find the most promising region for matching.
        
        Uses an expanding search pattern that prioritizes forward search.
        
        Args:
            asr_text: Text from ASR segment
            transcript_tokens: Full transcript tokens
            start_search_idx: Starting point for search
            coarse_window_size: Size of window for coarse search
            region_cer_threshold: Maximum CER to consider a region as promising
            max_backward_search: Maximum tokens to search backward
            forward_priority: Number of forward windows to check before each backward window
            step_size: Step size for window movement
            top_k: Number of top matches to return
            
        Returns:
            List of starting indices for best matching regions
        """
        best_matches = []
        best_cer = float('inf')
        best_start_idx = None
        
        # Initialize search boundaries
        backward_limit = max(0, start_search_idx - max_backward_search)
        forward_limit = len(transcript_tokens)
        
        # Initialize positions
        forward_pos = start_search_idx
        backward_pos = start_search_idx
        forward_steps = 0
        reached_forward_limit = False
        
        while True:
            # Check forward positions with priority
            while forward_steps < forward_priority and forward_pos < forward_limit and (not reached_forward_limit):
                if forward_pos + coarse_window_size > forward_limit:
                    forward_pos = forward_limit - coarse_window_size
                    reached_forward_limit = True
                    
                candidate_end = min(forward_pos + coarse_window_size, forward_limit)
                candidate_text = " ".join(transcript_tokens[forward_pos:candidate_end])
                cer = self.compute_cer(asr_text, candidate_text)
                best_matches.append((cer, forward_pos))
                
                if cer < best_cer:
                    best_cer = cer
                    best_start_idx = forward_pos
                    
                    if cer <= region_cer_threshold:
                        return [forward_pos]
                        
                forward_pos += max(int(coarse_window_size*step_size), 1)
                forward_steps += 1
            
            # Reset forward steps counter
            forward_steps = 0
            
            # Try one backward position if within bounds
            if backward_pos > backward_limit:
                backwards_step = max(int(coarse_window_size*step_size), 1)
                backward_pos = max(backward_pos - backwards_step, backward_limit)
                candidate_end = min(backward_pos + coarse_window_size, forward_limit)
                candidate_text = " ".join(transcript_tokens[backward_pos:candidate_end])
                cer = self.compute_cer(asr_text, candidate_text)
                best_matches.append((cer, backward_pos))
                
                if cer < best_cer:
                    best_cer = cer
                    best_start_idx = backward_pos
                    
                    if cer <= region_cer_threshold:
                        return [backward_pos]
            
            # Stop if we've searched the entire valid range
            if (forward_pos >= forward_limit or reached_forward_limit) and backward_pos <= backward_limit:
                break

        return [match[1] for match in heapq.nsmallest(top_k, best_matches)]

    def _fine_tune_match(self,
                        asr_segment: TranscribedSegment,
                        transcript_tokens: List[str],
                        region_start_idx: int) -> AlignedTranscript:
        """Fine-tune the exact match boundaries within the identified region."""
        asr_tokens = asr_segment.text.split()
        num_predicted = len(asr_tokens)
        best_cer = float('inf')
        crossed_cer_threshold = False
        best_match = None
        
        # Search within a smaller window around the identified region
        local_margin = self.window_token_margin // 2
        
        for start_offset in range(-local_margin, local_margin + 1):
            candidate_start = region_start_idx + start_offset
            if candidate_start < 0:
                continue
                
            best_cer_for_candidate_start = float('inf')
                
            for window_tokens in range(num_predicted - local_margin, 
                                     num_predicted + local_margin + 1):
                candidate_end = candidate_start + window_tokens
                if candidate_end > len(transcript_tokens):
                    break
                    
                candidate_text = " ".join(transcript_tokens[candidate_start:candidate_end])
                cer = self.compute_cer(asr_segment.text, candidate_text)
                best_cer_for_candidate_start = min(best_cer_for_candidate_start, cer)
                
                if cer < best_cer:
                    best_cer = cer
                    best_match = AlignedTranscript(
                        asr_segment=asr_segment,
                        human_text=candidate_text,
                        start_idx=candidate_start,
                        end_idx=candidate_end,
                        cer=cer
                    )
                    
                    if cer <= self.finetune_cer_threshold:
                        crossed_cer_threshold = True
            
            if crossed_cer_threshold and best_cer_for_candidate_start > self.finetune_cer_threshold:
                return best_match
        if best_match is None:
            """
            print(f"No best match found for {asr_segment.text}")
            # print the values relevant for the for looops, to see if we didn't go into some loops/ break always
            print(f"num_predicted: {num_predicted}")
            print(f"local_margin: {local_margin}")
            print(f"region_start_idx: {region_start_idx}")
            print(f"transcript_tokens length: {len(transcript_tokens)}")
            """
            

        return best_match

    def _create_fallback_alignment(self,
                                 asr_segment: TranscribedSegment,
                                 transcript_tokens: List[str],
                                 start_search_idx: int) -> AlignedTranscript:
        """Create a fallback alignment when no good match is found."""
        return self._fine_tune_match(asr_segment, transcript_tokens, start_search_idx)

    def align_transcript(self, 
                        transcribed_segments: List[TranscribedSegment],
                        human_transcript: str) -> List[AlignedTranscript]:
        """Align all ASR segments with human transcript.
        
        Args:
            transcribed_segments: List of TranscribedSegments from ASR
            human_transcript: Full human transcript text
            
        Returns:
            List of AlignedTranscript objects
        """
        transcript_tokens = human_transcript.split()
        aligned_segments = []
        last_end_idx = 0
        
        # Add progress bar for alignment
        for segment in tqdm(transcribed_segments, desc="Aligning segments", mininterval=60.0):
            aligned = self.find_best_match(
                segment, 
                transcript_tokens,
                start_search_idx=last_end_idx
            )
            aligned_segments.append(aligned)
            last_end_idx = aligned.end_idx if aligned else last_end_idx
            
        return aligned_segments 