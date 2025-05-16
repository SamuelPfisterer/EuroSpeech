import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import re
import logging
from typing import Optional, Dict
from functools import lru_cache

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TranscriptError(Exception):
    """Custom exception for transcript processing errors."""
    pass

@lru_cache(maxsize=1000)
def _get_transcript_link(session_url: str) -> Optional[str]:
    """
    Extract transcript link from a parliamentary session page.
    Cached to avoid redundant requests.
    
    Args:
        session_url: URL of the parliamentary session
        
    Returns:
        Optional[str]: URL of the transcript if found, None otherwise
        
    Raises:
        TranscriptError: If there's an error processing the page
    """
    try:
        logger.info(f"Extracting transcript link from: {session_url}")
        response = requests.get(session_url, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        transcript_anchor = soup.find('a', string=re.compile(r'Ver diário nos Debates Parlamentares'))
        
        if not transcript_anchor or 'href' not in transcript_anchor.attrs:
            logger.warning(f"No transcript link found in {session_url}")
            return None
            
        transcript_link = transcript_anchor['href']
        logger.info(f"Found transcript link: {transcript_link}")
        return transcript_link
        
    except requests.RequestException as e:
        raise TranscriptError(f"Network error accessing {session_url}: {str(e)}")
    except Exception as e:
        raise TranscriptError(f"Error processing session page {session_url}: {str(e)}")

def _extract_parameters(transcript_url: str) -> Dict[str, str]:
    """
    Extract parameters from transcript URL for the export request.
    
    Args:
        transcript_url: URL of the transcript page
        
    Returns:
        Dict[str, str]: Parameters for the export request
        
    Raises:
        TranscriptError: If URL format is invalid
    """
    try:
        parsed_url = urlparse(transcript_url)
        path_parts = parsed_url.path.split('/')
        
        if len(path_parts) < 9:
            raise TranscriptError(f"Invalid transcript URL format: {transcript_url}")
        
        return {
            "periodo": path_parts[2],
            "publicacao": path_parts[3],
            "serie": path_parts[4],
            "legis": path_parts[5],
            "sessao": path_parts[6],
            "numero": path_parts[7],
            "data": path_parts[8],
            "exportType": "txt",
            "exportControl": "documentoCompleto"
        }
    except Exception as e:
        raise TranscriptError(f"Failed to parse transcript URL {transcript_url}: {str(e)}")

def process_transcript_text(url: str) -> str:
    """
    Process a transcript URL and return text content.
    Implementation of the required interface from transcript_processors_template.py.
    
    Args:
        url: The session URL to process
        
    Returns:
        str: The transcript text content
        
    Raises:
        ValueError: If processing fails
    """
    try:
        # Step 1: Get the transcript link from the session page
        transcript_url = _get_transcript_link(url)
        if not transcript_url:
            raise TranscriptError(f"No transcript link found for session: {url}")
        
        # Step 2: Extract parameters for the export request
        params = _extract_parameters(transcript_url)
        
        # Step 3: Make the export request to get the transcript text
        logger.info(f"Downloading transcript from debates.parlamento.pt")
        response = requests.post(
            "https://debates.parlamento.pt/pagina/export",
            data=params,
            timeout=30
        )
        response.raise_for_status()
        
        # Verify we got text content
        if not response.text.strip():
            raise TranscriptError("Received empty transcript text")
            
        logger.info(f"Successfully downloaded transcript for {url}")
        return response.text
        
    except TranscriptError as e:
        # Convert our custom exception to the expected ValueError
        raise ValueError(str(e))
    except Exception as e:
        raise ValueError(f"Failed to process transcript: {str(e)}") 