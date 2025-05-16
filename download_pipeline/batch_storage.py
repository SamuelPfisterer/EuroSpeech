import os
import json
import logging
import threading
from datetime import datetime
from typing import Dict, Union, Optional, Any

class BatchStorageManager:
    """
    Manages storage of transcripts in batch JSON files.
    Each batch file corresponds to a specific range of rows and transcript type.
    """
    
    _instances = {}  # Cache of instances by subfolder
    
    @classmethod
    def get_instance(cls, subfolder_path, start_idx, end_idx, update_frequency=10):
        """Get or create a storage instance for the given subfolder."""
        if subfolder_path not in cls._instances:
            cls._instances[subfolder_path] = BatchStorageManager(subfolder_path, start_idx, end_idx, update_frequency)
        return cls._instances[subfolder_path]
    
    def __init__(self, subfolder_path, start_idx, end_idx, update_frequency=10):
        """
        Initialize the batch storage manager.
        
        Args:
            subfolder_path: Path to the subfolder for this transcript type
            start_idx: Starting row index for this process
            end_idx: Ending row index for this process
            update_frequency: How often to write to disk (every N transcripts)
        """
        self.subfolder_path = subfolder_path
        self.start_idx = start_idx
        self.end_idx = end_idx
        self.update_frequency = update_frequency
        
        # Create batch file name based on row range
        self.batch_file = os.path.join(subfolder_path, f"batch_{start_idx:06d}_{end_idx:06d}.json")
        
        # Lock for thread safety
        self.lock = threading.Lock()
        
        # In-memory storage
        self.transcripts = {}
        self.count = 0
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(self.batch_file), exist_ok=True)
        
        # Load existing data if available
        self._load_existing()
    
    def _load_existing(self):
        """Load existing transcripts from the batch file if it exists."""
        if os.path.exists(self.batch_file):
            try:
                with open(self.batch_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.transcripts = data.get("transcripts", {})
                    self.count = len(self.transcripts)
                logging.info(f"Loaded {self.count} transcripts from {self.batch_file}")
            except Exception as e:
                logging.error(f"Error loading batch file {self.batch_file}: {str(e)}")
                # Initialize as empty if loading fails
                self.transcripts = {}
                self.count = 0
    
    def _save(self):
        """Save all transcripts to the batch file."""
        try:
            # Create data structure with metadata
            data = {
                "metadata": {
                    "start_idx": self.start_idx,
                    "end_idx": self.end_idx,
                    "updated_at": datetime.now().isoformat(),
                    "transcript_count": len(self.transcripts)
                },
                "transcripts": self.transcripts
            }
            
            # Write to file
            with open(self.batch_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logging.info(f"Saved {len(self.transcripts)} transcripts to {self.batch_file}")
        except Exception as e:
            logging.error(f"Error saving batch file {self.batch_file}: {str(e)}")
    
    def _encode_content(self, content: Union[str, bytes]) -> Dict[str, Any]:
        """
        Encode content for JSON storage, handling both string and bytes.
        
        Args:
            content: The content to encode (string or bytes)
            
        Returns:
            Dictionary with encoded content and type information
        """
        if isinstance(content, str):
            return {
                "type": "string",
                "data": content
            }
        elif isinstance(content, bytes):
            # Encode bytes as base64 string
            import base64
            return {
                "type": "bytes",
                "data": base64.b64encode(content).decode('ascii'),
                "encoding": "base64"
            }
        else:
            # For other types, convert to string
            return {
                "type": "other",
                "data": str(content)
            }
    
    def _decode_content(self, encoded_content: Dict[str, Any]) -> Union[str, bytes]:
        """
        Decode content from JSON storage.
        
        Args:
            encoded_content: Dictionary with encoded content and type information
            
        Returns:
            Original content (string or bytes)
        """
        content_type = encoded_content.get("type", "string")
        data = encoded_content.get("data", "")
        
        if content_type == "string":
            return data
        elif content_type == "bytes":
            # Decode base64 string back to bytes
            import base64
            return base64.b64decode(data)
        else:
            # For other types, return as string
            return data
    
    def add_transcript(self, transcript_id, content, url=None, metadata=None):
        """
        Add a transcript to the batch storage.
        
        Args:
            transcript_id: Unique identifier for the transcript
            content: The transcript content (string or bytes)
            url: Original URL of the transcript
            metadata: Additional metadata about the transcript
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with self.lock:
                # Create transcript entry
                transcript_entry = {
                    "content": self._encode_content(content),
                    "added_at": datetime.now().isoformat()
                }
                
                if url:
                    transcript_entry["url"] = url
                
                if metadata:
                    transcript_entry["metadata"] = metadata
                
                # Add to storage
                self.transcripts[transcript_id] = transcript_entry
                self.count += 1
                
                # Save to file based on update frequency
                if self.count % self.update_frequency == 0:
                    self._save()
                
                return True
        except Exception as e:
            logging.error(f"Error adding transcript {transcript_id}: {str(e)}")
            return False
    
    def get_transcript(self, transcript_id):
        """
        Retrieve a transcript by its ID.
        
        Args:
            transcript_id: Unique identifier for the transcript
            
        Returns:
            The transcript content (string or bytes) or None if not found
        """
        with self.lock:
            if transcript_id in self.transcripts:
                encoded_content = self.transcripts[transcript_id].get("content")
                if encoded_content:
                    return self._decode_content(encoded_content)
            return None
    
    def get_transcript_data(self, transcript_id):
        """
        Retrieve all data for a transcript by its ID.
        
        Args:
            transcript_id: Unique identifier for the transcript
            
        Returns:
            Dictionary with all transcript data or None if not found
        """
        with self.lock:
            if transcript_id in self.transcripts:
                # Make a copy of the transcript data
                transcript_data = dict(self.transcripts[transcript_id])
                
                # Decode the content
                if "content" in transcript_data:
                    transcript_data["content"] = self._decode_content(transcript_data["content"])
                
                return transcript_data
            return None
    
    def cleanup(self):
        """Save any pending changes and clean up resources."""
        with self.lock:
            if self.transcripts:
                self._save() 