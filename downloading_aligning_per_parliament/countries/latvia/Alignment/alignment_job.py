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
    
    
    base_dir = "/itet-stor/spfisterer/net_scratch/Downloading/countries/latvia"
    csv_path = f"{base_dir}/links/latvia_links.csv"
    alignment_output_dir = f"{base_dir}/Alignment/alignment_output"

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
        language="lv",
        batch_size=64,
        supabase_logging_enabled=True,
        parliament_id="latvia",
        html_processor=html_processor
    )
    
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
