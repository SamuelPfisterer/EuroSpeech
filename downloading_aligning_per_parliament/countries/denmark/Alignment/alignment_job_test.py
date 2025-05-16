from parliament_transcript_aligner import AlignmentPipeline
from dotenv import load_dotenv
import os
import pandas as pd
import sys
import glob
from typing import Dict

# Load environment variables
load_dotenv("/itet-stor/spfisterer/net_scratch/Alignment/testing/own_pipeline/.env")

def main():
    
    
    # Get HuggingFace credentials
    hf_cache_dir = os.getenv("HF_CACHE_DIR")
    hf_token = os.getenv("HF_AUTH_TOKEN")
    
    print(f"Cache directory: {hf_cache_dir}")
    
    
    base_dir = "/itet-stor/spfisterer/net_scratch/Downloading/countries/denmark"
    csv_path = f"{base_dir}/links/denmark_links.csv"
    alignment_output_dir = f"{base_dir}/Alignment/alignment_output"

    

    def process_ft_transcript(html_string: str, config: Dict) -> str:
        """
        Processes Folketidende (FT) HTML transcript to extract spoken text with speaker names.

        Args:
            html_string: A string containing the HTML content of the transcript.
            config: A dictionary (currently unused but kept for Callable type).

        Returns:
            A single string with speaker names in ** ** and spoken text on the following line.
        """
        try:
            from bs4 import BeautifulSoup
        except ImportError:
            print("BeautifulSoup is not installed. Please install it using 'pip install beautifulsoup4'.")
            return ""
        soup = BeautifulSoup(html_string, 'html.parser')
        output = ""
        speaker_infos = soup.find_all('meta', {'name': 'Start MetaSpeakerMP'})

        for speaker_info in speaker_infos:
            speaker_block_start = speaker_info.find_next_sibling()
            speaker_name_element = None
            while speaker_block_start and speaker_block_start.name != 'meta' and not speaker_block_start.find('span', class_='Bold'):
                speaker_block_start = speaker_block_start.find_next_sibling()

            if speaker_block_start and speaker_block_start.name != 'meta':
                speaker_name_element = speaker_block_start.find('span', class_='Bold')
                if speaker_name_element:
                    speaker_text = speaker_name_element.get_text(strip=True).replace(':', '')
                    output += f"**{speaker_text}**\n"

                    speech_segment_start = speaker_block_start.find_next_sibling()
                    while speech_segment_start and speech_segment_start.name != 'meta' and speech_segment_start.get('class') == ['Tekst']:
                        speech_text = speech_segment_start.get_text(separator=' ', strip=True)
                        output += f"{speech_text}\n"
                        speech_segment_start = speech_segment_start.find_next_sibling()

        # Handle text without explicit speaker meta (though less common in this format)
        plain_texts = soup.find_all('p', class_='Tekst')
        for text_element in plain_texts:
            if not text_element.find_previous('p', class_='TalerTitel'):
                spoken_text = text_element.get_text(separator=' ', strip=True)
                output += f"{spoken_text}\n"

        return output.strip()

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
        cer_threshold=1.1,
        language="da",
        batch_size=1,
        supabase_logging_enabled=True,
        parliament_id="denmark",
        with_pydub_silences=False,
        html_processor=markdownify_html_processor
    )
    
    # Process the subset
    aligner.process_subset(["20101M001_2010-10-05_1200"])

if __name__ == "__main__":
    main()
