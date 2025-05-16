from parliament_transcript_aligner import (
    TranscriptAligner, 
    AlignmentPipeline,
    AudioSegmenter,
    initialize_vad_pipeline,
    get_silero_vad,
    initialize_diarization_pipeline
)

from dotenv import load_dotenv
import os

load_dotenv("/itet-stor/spfisterer/net_scratch/Alignment/testing/own_pipeline/.env")


def main():

    hf_cache_dir = os.getenv("HF_CACHE_DIR")
    print(f"Cache directory: {hf_cache_dir}")
    hf_token = os.getenv("HF_AUTH_TOKEN")
    print(f"HF token: {hf_token}")

    
    aligner = AlignmentPipeline(
        csv_path= "/itet-stor/spfisterer/net_scratch/Downloading/Germany/Links/germany_parliament_file_links_filtered_subtitles.csv",
        base_dir= "/itet-stor/spfisterer/net_scratch/Downloading/Germany",
        output_dir= "/itet-stor/spfisterer/net_scratch/Downloading/Germany/Alignment",
        use_cache= True,
        delete_wav_files= True,
        wav_dir= "/itet-stor/spfisterer/net_scratch/Downloading/Germany/Wavs", 
        audio_dirs=["downloaded_audio"],
        transcript_dirs=["downloaded_transcript", "downloaded_subtitle"],
        hf_cache_dir=hf_cache_dir,
        hf_token=hf_token,
        with_diarization=False,
        cer_threshold=0.8,
        language="de",
        batch_size=4
    )
    aligner.process_subset(["7604103"])
    """
    vad_pipeline = initialize_vad_pipeline(hf_cache_dir=hf_cache_dir, hf_token=hf_token)
    diarization_pipeline = initialize_diarization_pipeline(hf_cache_dir=hf_cache_dir, hf_token=hf_token)
    segmenter = AudioSegmenter(
        vad_pipeline=vad_pipeline,
        diarization_pipeline=diarization_pipeline,
        language="de"
    )
    segments = segmenter.segment_and_transcribe(
        audio_path= "/itet-stor/spfisterer/net_scratch/Downloading/Germany/7501579_960s.wav",
    )
    print(segments)
    """


if __name__ == "__main__":
    main()