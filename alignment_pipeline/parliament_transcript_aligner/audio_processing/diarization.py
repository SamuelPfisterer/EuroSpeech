import os
import torch
from pyannote.audio import Pipeline
from typing import Optional
from pathlib import Path

def initialize_diarization_pipeline(hf_cache_dir: Optional[Path] = None, hf_token: Optional[str] = None) -> Pipeline:
    """Initialize the pyannote diarization pipeline.
    
    Returns:
        Configured diarization pipeline
    """
    hf_token = hf_token if hf_token is not None else os.getenv("HF_AUTH_TOKEN")
    cache_dir = hf_cache_dir if hf_cache_dir is not None else os.getenv("HF_CACHE_DIR")
    
    pipeline = Pipeline.from_pretrained(
        "pyannote/speaker-diarization",
        use_auth_token=hf_token,
        cache_dir=cache_dir
    )

    # Move to GPU if available
    pipeline.to(torch.device("cuda" if torch.cuda.is_available() else "cpu"))

    return pipeline 