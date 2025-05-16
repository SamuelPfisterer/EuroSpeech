import json
import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse, parse_qs

from process_session import process_session

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class SpeechMetadata:
    """Data class for speech metadata."""
    speaker_name: str
    speaker_party: Optional[str]
    speaker_role: Optional[str]
    speech_type: str
    section_number: Optional[float]
    section_title: Optional[str]
    time: Optional[str]
    timing: Dict

class TranscriptFormatter:
    """Formats transcript data into structured text."""
    
    @staticmethod
    def format_raw_content(speeches: List[Dict]) -> str:
        """Formats speeches into raw concatenated content."""
        return "\n\n".join(
            "\n".join(speech["content"]) 
            for speech in speeches
        )
    
    @staticmethod
    def format_structured_content(speeches: List[Dict]) -> str:
        """Formats speeches into structured content with metadata."""
        structured_parts = []
        
        for i, speech in enumerate(speeches, 1):
            metadata = SpeechMetadata(
                speaker_name=speech["speaker"]["name"],
                speaker_party=speech["speaker"]["party"],
                speaker_role=speech["speaker"]["role"],
                speech_type=speech["type"],
                section_number=speech["section_number"],
                section_title=speech["section_title"],
                time=speech["time"],
                timing=speech["timing"]
            )
            
            # Format metadata
            meta_lines = [
                f"[Speech {i}]",
                f"Speaker: {metadata.speaker_name}",
                f"Party: {metadata.speaker_party or 'N/A'}",
                f"Role: {metadata.speaker_role or 'N/A'}",
                f"Type: {metadata.speech_type}",
                f"Section: {metadata.section_number or 'N/A'} - {metadata.section_title or 'N/A'}",
                f"Time: {metadata.time or 'N/A'}",
                "Content:"
            ]
            
            # Format content
            content = "\n".join(speech["content"])
            
            # Combine metadata and content
            structured_parts.append(
                "\n".join(meta_lines) + "\n" + content + "\n"
            )
        
        return "\n" + "-" * 80 + "\n".join(structured_parts)

class TranscriptProcessor:
    """Processes parliamentary session transcripts."""
    
    def __init__(self):
        self.formatter = TranscriptFormatter()
    
    def _extract_session_id(self, url: str) -> Optional[str]:
        """Extract session ID from URL."""
        try:
            parsed_url = urlparse(url)
            path_parts = parsed_url.path.split('/')
            
            # Find the part that contains 'taysistunto-'
            for part in path_parts:
                if part.startswith('taysistunto-'):
                    # Extract session number and year
                    num_year = part.replace('taysistunto-', '').split('-')
                    if len(num_year) == 2:
                        return f"PTK_{num_year[0]}_{num_year[1]}"
            
            logger.error(f"Could not extract session ID from URL: {url}")
            return None
            
        except Exception as e:
            logger.error(f"Error extracting session ID from URL: {e}")
            return None
    
    def process_transcript_text(self, url: str) -> str:
        """
        Process a transcript URL and return text content.
        
        Args:
            url: The URL to process
            
        Returns:
            str: The processed text content
            
        Raises:
            ValueError: If processing fails
        """
        try:
            # Extract session ID from URL
            session_id = self._extract_session_id(url)
            if not session_id:
                raise ValueError(f"Invalid URL format: {url}")
            
            # Process session
            logger.info(f"Processing session {session_id}")
            parsed_data = process_session(session_id)
            if not parsed_data:
                raise ValueError(f"Failed to process session {session_id}")
            
            # Get speeches in chronological order
            speeches = parsed_data["speeches"]
            
            # Format content
            raw_content = self.formatter.format_raw_content(speeches)
            structured_content = self.formatter.format_structured_content(speeches)
            
            # Combine both sections
            full_content = (
                "=== RAW CONTENT ===\n\n"
                f"{raw_content}\n\n"
                "=== STRUCTURED CONTENT ==="
                f"{structured_content}"
            )
            
            return full_content
            
        except Exception as e:
            error_msg = f"Failed to process transcript: {str(e)}"
            logger.error(error_msg)
            raise ValueError(error_msg)
    
    def process_transcript_html(self, url: str) -> str:
        """
        Process a transcript URL and return HTML content.
        
        Args:
            url: The URL to process
            
        Returns:
            str: The processed HTML content
            
        Raises:
            ValueError: If processing fails
        """
        raise NotImplementedError("HTML processing not implemented for this parliament")
    
def process_transcript_text(url: str) -> str:
    processor = TranscriptProcessor()
    return processor.process_transcript_text(url)

def process_transcript_html(url: str) -> str:
    processor = TranscriptProcessor()
    return processor.process_transcript_html(url)