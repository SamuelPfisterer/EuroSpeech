import os
from pyannote.audio.pipelines import VoiceActivityDetection
from pyannote.audio import Model
from typing import Optional
from pathlib import Path
import torch
import torch.serialization


def initialize_vad_pipeline(hf_cache_dir: Optional[Path] = None, hf_token: Optional[str] = None) -> VoiceActivityDetection:
    """Initialize the pyannote VAD pipeline.
    
    Args:
        cache_dir: Optional directory for caching models. If None, uses environment variable.
    
    Returns:
        Configured VAD pipeline
    """
    
    # Add omegaconf.listconfig.ListConfig to safe globals for PyTorch 2.6+ compatibility
    from omegaconf import ListConfig
    from omegaconf.base import ContainerMetadata

    torch.serialization.add_safe_globals([ListConfig, ContainerMetadata])
    torch.serialization.add_safe_globals([object])


    # First load the model with cache_dir
    model = Model.from_pretrained(
        "pyannote/segmentation",
        use_auth_token=hf_token if hf_token is not None else os.getenv("HF_TOKEN"),
        cache_dir=hf_cache_dir if hf_cache_dir is not None else os.getenv("HF_CACHE_DIR")
    )
    
    # Then create the VAD pipeline using the loaded model
    vad_pipeline = VoiceActivityDetection(segmentation=model)
    
    # Configure the pipeline parameters
    vad_pipeline.instantiate({
        "onset": 0.9,
        "offset": 0.9,
        "min_duration_on": 0.2,
        "min_duration_off": 0.0
    })
    
    return vad_pipeline 