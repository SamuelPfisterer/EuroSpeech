from parliament_transcript_aligner import AlignmentPipeline
from dotenv import load_dotenv
import os
import pandas as pd
import sys
import glob

# Load environment variables
load_dotenv("/itet-stor/spfisterer/net_scratch/Alignment/testing/own_pipeline/.env")

def main():
    # Get task ID and total number of tasks from command line arguments
    task_id = int(sys.argv[1])
    total_tasks = int(sys.argv[2])
    
    # Get HuggingFace credentials
    hf_cache_dir = os.getenv("HF_CACHE_DIR")
    hf_token = os.getenv("HF_AUTH_TOKEN")
    
    print(f"Cache directory: {hf_cache_dir}")
    
    
    base_dir = "/itet-stor/spfisterer/net_scratch/Downloading/countries/croatia"
    csv_path = f"{base_dir}/croatian_parliament_media_links_final.csv"
    alignment_output_dir = f"{base_dir}/Alignment/alignment_output"

    def html_processing(html_string: str, metadata: dict) -> str:
        """
        Extracts spoken text and speaker names from the given HTML string into a single string.

        Args:
            html_string: A string containing the HTML content.
            metadata: A dictionary containing additional metadata about the transcript.

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
        speaker_divs = soup.find_all('div', class_='contentHeader speaker')
        for speaker_div in speaker_divs:
            speaker_link = speaker_div.find('a')
            if speaker_link and speaker_link.h2:
                speaker_name = speaker_link.h2.text.strip()
                output += f"**{speaker_name}**\n"
            spoken_text_div = speaker_div.find_next_sibling('div', class_='singleContent')
            if spoken_text_div:
                spoken_text_dd = spoken_text_div.find('dd', class_='textColor')
                if spoken_text_dd:
                    spoken_text = spoken_text_dd.get_text(separator=' ', strip=True)
                    output += f"{spoken_text}\n"

        # Handle cases where spoken text might exist without a preceding speaker div
        text_dds_without_speaker = soup.select('div.singleContent dd.textColor:not(div.singleContentContainer + div.singleContentContainer > div.singleContent > dd.textColor)')
        for text_dd in text_dds_without_speaker:
            if not text_dd.find_previous('div', class_='contentHeader speaker'):
                spoken_text = text_dd.get_text(separator=' ', strip=True)
                if spoken_text:
                    output += f"{spoken_text}\n"

        return output.strip()

    
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
        language="hr",
        batch_size=1,
        supabase_logging_enabled=True,
        parliament_id="croatia",
        with_pydub_silences=False,
        html_processor=html_processing
    )

     # Find already processed video IDs
    processed_files = glob.glob(os.path.join(alignment_output_dir, "*_*_aligned.json"))
    processed_video_ids = set()
    for file_path in processed_files:
        file_name = os.path.basename(file_path)
        # Extract the video ID from filenames like "242_242_aligned.json"
        if "_aligned.json" in file_name:
            video_id = file_name.split("_")[0]
            processed_video_ids.add(video_id)
    
    print(f"Found {len(processed_video_ids)} already processed video IDs")
    
    # Load all video IDs
    df = pd.read_csv(csv_path)
    all_video_ids = df["video_id"].astype(str).tolist()
    
    # Filter out already processed video IDs
    video_ids_to_process = [vid for vid in all_video_ids if vid not in processed_video_ids]
    total_ids = len(video_ids_to_process)
    
    print(f"Total video IDs to process: {total_ids} out of {len(all_video_ids)} total videos")
    
    if total_ids == 0:
        print("No videos left to process. Exiting.")
        return
    
    # Calculate which subset of video IDs this task should process
    ids_per_task = total_ids // total_tasks
    start_idx = task_id * ids_per_task
    
    # For the last task, process all remaining IDs
    if task_id == total_tasks - 1:
        end_idx = total_ids
    else:
        end_idx = start_idx + ids_per_task
    
    # Get subset of video IDs for this job
    video_ids_subset = video_ids_to_process[start_idx:end_idx]
    
    print(f"Task {task_id+1}/{total_tasks}: Processing {len(video_ids_subset)} video IDs from index {start_idx} to {end_idx-1}")
    if video_ids_subset:
        print(f"First few IDs to process: {video_ids_subset[:min(5, len(video_ids_subset))]}")
    
    # Process the subset
    aligner.process_subset(video_ids_subset)

if __name__ == "__main__":
    main()
