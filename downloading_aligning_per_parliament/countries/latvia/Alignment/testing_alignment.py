from parliament_transcript_aligner import AlignmentPipeline
from parliament_transcript_aligner.utils import get_alignment_stats
from dotenv import load_dotenv
import os
import pandas as pd
import sys

# Load environment variables
load_dotenv("/itet-stor/spfisterer/net_scratch/Alignment/testing/own_pipeline/.env")

def main():
    """
    alignment_file = "/itet-stor/spfisterer/net_scratch/Downloading/countries/bosnia-herzegovina/Alignment/alignment_output/242_242_aligned.json"
    stats = get_alignment_stats([alignment_file])
    print(stats)
    """


    """
    # Get task ID and total number of tasks from command line arguments
    task_id = int(sys.argv[1])
    total_tasks = int(sys.argv[2])
    """
    
    # Get HuggingFace credentials
    hf_cache_dir = os.getenv("HF_CACHE_DIR")
    hf_token = os.getenv("HF_AUTH_TOKEN")
    
    print(f"Cache directory: {hf_cache_dir}")
    
    # Load Bosnian abbreviations
    
    base_dir = "/itet-stor/spfisterer/net_scratch/Downloading/countries/latvia"
    csv_path = f"{base_dir}/links/latvia_links.csv"


    def html_processor(html_text: str, config: dict) -> str:
        """
        Process the HTML text to extract the text content.
        """
        try:
            from bs4 import BeautifulSoup
        except ImportError:
            raise ImportError("BeautifulSoup is not installed. Please install it with 'pip install beautifulsoup4. This comes from the custom html_processor function in the AlignmentPipeline class.")

        soup = BeautifulSoup(html_text, 'html.parser')
        speech_elements = soup.find('div', class_='text').find_all('p')
        all_speech_text = "\n".join(element.get_text(strip=True) for element in speech_elements if element.get_text(strip=True))
        return all_speech_text
    
    # Initialize aligner
    aligner = AlignmentPipeline(
        csv_path=csv_path,
        base_dir=base_dir,
        output_dir=f"{base_dir}/Alignment/alignment_output",
        use_cache=True,
        delete_wav_files=True,
        wav_dir=f"{base_dir}/Wavs",
        hf_cache_dir=hf_cache_dir,
        hf_token=hf_token,
        with_diarization=False,
        cer_threshold=0.8,
        language="lv",
        batch_size=32,
        supabase_logging_enabled=True,
        parliament_id="latvia",
        html_processor=html_processor
    )

    aligner.process_subset(["20111222152303"])

if __name__ == "__main__":
    main()
