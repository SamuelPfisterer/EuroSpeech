from parliament_transcript_aligner import AlignmentPipeline
from dotenv import load_dotenv
import os
import pandas as pd

# Load environment variables
load_dotenv("/itet-stor/spfisterer/net_scratch/Alignment/testing/own_pipeline/.env")

def main():
    print("I am the cleaner job, I will go over all files and log everything to supabase if it hasn't already")
    
    # Get HuggingFace credentials
    hf_cache_dir = os.getenv("HF_CACHE_DIR")
    hf_token = os.getenv("HF_AUTH_TOKEN")
    
    print(f"Cache directory: {hf_cache_dir}")
    
    # Load Bosnian abbreviations
    bosnian_abbreviations = {
        "BiH": "Bosne i Hercegovine",
        "PSBiH": "Parlamentarna skupština BiH",
        "KM": "Konvertibilna marka"
    }
    
    base_dir = "/itet-stor/spfisterer/net_scratch/Downloading/countries/bosnia-herzegovina"
    csv_path = f"{base_dir}/links/bosnia-herzegovina_links.csv"
    alignment_output_dir = f"{base_dir}/Alignment/alignment_output"
    
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
        language="bs",
        batch_size=1,
        abbreviations=bosnian_abbreviations,
        supabase_logging_enabled=True,
        parliament_id="bosnia-herzegovina"
    )
    
    print("Starting cleaning process for all files...")
    # Process all files with the cleaner
    aligner.process_all()
    
    print("Cleaning process completed successfully")

if __name__ == "__main__":
    main()
