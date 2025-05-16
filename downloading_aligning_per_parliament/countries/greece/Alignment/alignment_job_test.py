from parliament_transcript_aligner import AlignmentPipeline
from dotenv import load_dotenv
import os
import pandas as pd
import sys
import glob
from typing import Dict
from markdownify import markdownify

# Load environment variables
load_dotenv("/itet-stor/spfisterer/net_scratch/Alignment/testing/own_pipeline/.env")

def main():
    
    
    # Get HuggingFace credentials
    hf_cache_dir = os.getenv("HF_CACHE_DIR")
    hf_token = os.getenv("HF_AUTH_TOKEN")
    
    print(f"Cache directory: {hf_cache_dir}")
    
    
    base_dir = "/itet-stor/spfisterer/net_scratch/Downloading/countries/greece"
    csv_path = f"{base_dir}/links/greece_links.csv"
    alignment_output_dir = f"{base_dir}/Alignment/alignment_output"


    def markdownify_html_processor(html_string: str, config: Dict) -> str:
        """
        Processes HTML transcript to convert it into Markdown format.

        Args:
            html_string: A string containing the HTML content of the transcript.
            config: A dictionary (currently unused but kept for Callable type).

        Returns:
            A string with the transcript converted to Markdown format.
        """
        try:
            from markdownify import markdownify 
        except ImportError:
            print("markdownify is not installed. Please install it using 'pip install markdownify'.")
            raise ImportError("markdownify is not installed. Please install it using 'pip install markdownify'.")
        md = markdownify(html_string)
        return md

    
    # Initialize aligner
    aligner = AlignmentPipeline(
        csv_path=csv_path,
        base_dir=base_dir,
        output_dir=alignment_output_dir,
        use_cache=True,
        delete_wav_files=True,
        wav_dir=f"{base_dir}/Wavs",
        hf_cache_dir=hf_cache_dir,
        hf_token=hf_token,
        with_diarization=False,
        cer_threshold=0.8,
        language="el",
        batch_size=8,
        supabase_logging_enabled=True,
        parliament_id="greece",
        with_pydub_silences=False,
        html_processor=markdownify_html_processor
    )
    
    # Process the subset
    aligner.process_subset(["olomeleia-20100607"])

if __name__ == "__main__":
    main()
