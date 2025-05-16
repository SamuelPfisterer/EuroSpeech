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
    bosnian_abbreviations = {
        "BiH": "Bosne i Hercegovine",
        "PSBiH": "Parlamentarna skupština BiH",
        "KM": "Konvertibilna marka"
    }
    
    base_dir = "/itet-stor/spfisterer/net_scratch/Downloading/countries/bosnia-herzegovina"
    csv_path = f"{base_dir}/links/bosnia-herzegovina_links.csv"
    
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
        language="bs",
        batch_size=1,
        abbreviations=bosnian_abbreviations,
        supabase_logging_enabled=True,
        parliament_id="bosnia-herzegovina"
    )
    
    # Load all video IDs

    """
    df = pd.read_csv(csv_path)
    all_video_ids = df["video_id"].astype(str).tolist()
    total_ids = len(all_video_ids)
    
    # Calculate which subset of video IDs this task should process
    ids_per_task = total_ids // total_tasks
    start_idx = task_id * ids_per_task
    
    # For the last task, process all remaining IDs
    if task_id == total_tasks - 1:
        end_idx = total_ids
    else:
        end_idx = start_idx + ids_per_task
    
    # Get subset of video IDs for this job
    video_ids_subset = all_video_ids[start_idx:end_idx]
    
    print(f"Task {task_id+1}/{total_tasks}: Processing {len(video_ids_subset)} video IDs from index {start_idx} to {end_idx-1}")
    if video_ids_subset:
        print(f"First few IDs to process: {video_ids_subset[:min(5, len(video_ids_subset))]}")
    
    # Process the subset
    aligner.process_subset(video_ids_subset)
    """

    aligner.process_subset(["1682"])

if __name__ == "__main__":
    main()
