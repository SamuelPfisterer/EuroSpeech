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
import pandas as pd
load_dotenv("/itet-stor/spfisterer/net_scratch/Alignment/testing/own_pipeline/.env")


def main():

    hf_cache_dir = os.getenv("HF_CACHE_DIR")
    print(f"Cache directory: {hf_cache_dir}")
    hf_token = os.getenv("HF_AUTH_TOKEN")
    print(f"HF token: {hf_token}")

    bosnian_abbreviations = {
    "BiH": "Bosne i Hercegovine",
    "PSBiH": "Parlamentarna skupština BiH",
    "KM": "Konvertibilna marka"
}
    
    aligner = AlignmentPipeline(
        csv_path= "/itet-stor/spfisterer/net_scratch/Downloading/countries/bosnia-herzegovina/links/bosnia-herzegovina_links.csv",
        base_dir= "/itet-stor/spfisterer/net_scratch/Downloading/countries/bosnia-herzegovina",
        output_dir= "/itet-stor/spfisterer/net_scratch/Downloading/countries/bosnia-herzegovina/Alignment/alignment_output",
        use_cache= True,
        delete_wav_files= True,
        wav_dir= "/itet-stor/spfisterer/net_scratch/Downloading/countries/bosnia-herzegovina/Wavs",
        hf_cache_dir=hf_cache_dir,
        hf_token=hf_token,
        with_diarization=False,
        cer_threshold=0.8,
        language="bs",
        batch_size=1,
        abbreviations=bosnian_abbreviations
    )

    # get 5 random video_id values from the csv file "/itet-stor/spfisterer/net_scratch/Downloading/countries/bosnia-herzegovina/links/bosnia-herzegovina_links.csv"
    df = pd.read_csv("/itet-stor/spfisterer/net_scratch/Downloading/countries/bosnia-herzegovina/links/bosnia-herzegovina_links.csv")
    # video_ids should be strings
    video_ids = df["video_id"].sample(n=5).astype(str).tolist()
    print(video_ids)    
    print(f"Number of video ids: {len(df['video_id'].unique())}")

    print(type(video_ids[0]))
    # 2597 is the ID of the file that we want to align

    # transform the video_ids
    aligner.process_subset(video_ids)
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