# Parliament Transcript Aligner

A Python library designed to create high-quality speech-text datasets from challenging source material. Its core purpose is to take **multi-hour long audio recordings** and a collection of **multiple, potentially matching transcript files** (which can be in various formats like PDF, DOCX, HTML, TXT, SRT, and may include significant noise, annotations, or be non-verbatim) and transform them into a dataset of **short, aligned audio segments (typically 3-20 seconds)** paired with their **corresponding textual transcriptions**. This library is a key component of the EuroSpeech project (see "EuroSpeech: A Multilingual Speech Corpus" for more context on its application in building large-scale multilingual speech corpora from parliamentary proceedings).

## Project Status: Alpha 🚧

This project is under active development. While core functionalities are implemented, APIs might change, and some features are still being refined or added.

## Key Features

-   **Audio Segmentation**: Segments long audio files into smaller chunks suitable for ASR, using VAD (Voice Activity Detection) and speaker diarization.
-   **ASR Transcription**: Transcribes audio segments using Hugging Face Transformers models (defaults to Whisper-large-v3-turbo).
-   **Transcript Preprocessing**: Supports various transcript formats:
    -   Plain Text (.txt)
    -   PDF (.pdf) - with optional LLM-based cleaning and Docling conversion.
    -   SRT Subtitles (.srt)
    -   Word Documents (.docx, .doc) - converted to PDF then processed.
    -   HTML (.html, .htm) - with configurable custom processors.
-   **Alignment**: Aligns ASR-generated text with preprocessed human transcripts using Character Error Rate (CER).
-   **Flexible Pipeline**: Orchestrates the entire process from audio input to aligned text output, with a two-level selection strategy for handling multiple transcript versions/formats per audio file.
-   **Caching**: Supports caching of intermediate results (e.g., transcribed segments) to speed up reprocessing.
-   **Supabase Logging**: Optional integration for logging progress and metrics to a Supabase database.
-   **Configurable**: Offers various parameters to customize behavior, including language, ASR batch size, VAD settings, and Hugging Face model caching.

## Installation

1.  **Clone the repository:**
    ```bash
    git clone <repository-url> # Replace <repository-url> with the actual URL
    cd alignment_pipeline # Assuming you clone the parent repo and cd into this sub-directory
    ```
2.  **Create and activate a virtual environment (recommended):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    ```
3.  **Install the package and its dependencies:**
    ```bash
    pip install .
    ```
    This will install the package from `setup.py` along with dependencies like `pyannote.audio`, `transformers`, `torch`, `Levenshtein`, etc.

## Quick Start

This example demonstrates how to use the `AlignmentPipeline` to process an audio file and its associated transcripts defined in a CSV metadata file.

```python
from parliament_transcript_aligner.pipeline import AlignmentPipeline
import os

# --- Configuration ---
# Adjust these paths and parameters as needed

# Base directory where 'downloaded_audio' and 'downloaded_transcript' reside
# e.g., if your data is in /data/parliament_x/downloaded_audio, base_dir is /data/parliament_x
BASE_DATA_DIR = "/path/to/your/parliament/data_root"

# Path to your CSV metadata file
# This CSV should map audio files to potential transcript files.
# See docs/diagrams/alignment_pipeline.md for expected CSV structure hints.
# Example: If BASE_DATA_DIR is 'EuroSpeech/data_sourcing/parliaments/lithuania'
# then CSV_METADATA_PATH might be 'EuroSpeech/data_sourcing/parliaments/lithuania/links/lithuanian_parliament_sessions.csv'
CSV_METADATA_PATH = os.path.join(BASE_DATA_DIR, "links/your_metadata_file.csv")

# Directory where alignment results will be saved
OUTPUT_DIR = os.path.join(BASE_DATA_DIR, "alignment_output")
# Directory for caching intermediate results (e.g., ASR transcriptions)
CACHE_DIR = os.path.join(OUTPUT_DIR, "cache")
# Optional: Directory for Hugging Face model cache
HF_MODEL_CACHE_DIR = os.path.join(os.path.expanduser("~"), ".cache/huggingface_models_aligner")

# --- Initialize and Run Pipeline ---
if __name__ == "__main__":
    # Ensure paths exist (or create them)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(CACHE_DIR, exist_ok=True)
    os.makedirs(HF_MODEL_CACHE_DIR, exist_ok=True)

    # Example: Create a dummy CSV if it doesn't exist
    if not os.path.exists(CSV_METADATA_PATH):
        os.makedirs(os.path.dirname(CSV_METADATA_PATH), exist_ok=True)
        with open(CSV_METADATA_PATH, "w") as f:
            f.write("video_id,transcript_id\n") # Header
            # Replace with actual IDs from your filenames (without extensions)
            f.write("my_audio_session_1,my_transcript_session_1\n") 
        print(f"Created dummy CSV: {CSV_METADATA_PATH}. Please populate it with your data.")
        # You would also need dummy audio (e.g., downloaded_audio/.../my_audio_session_1.opus)
        # and transcript (e.g., downloaded_transcript/.../my_transcript_session_1.txt) files.

    pipeline = AlignmentPipeline(
        base_dir=BASE_DATA_DIR,
        csv_path=CSV_METADATA_PATH,
        output_dir=OUTPUT_DIR,
        cache_dir=CACHE_DIR,
        hf_cache_dir=HF_MODEL_CACHE_DIR,
        language="en",  # Specify the language of your audio (e.g., "lt" for Lithuanian)
        cer_threshold=0.3, # Example CER threshold for selecting best transcript
        multi_transcript_strategy="best_only", # Strategy for multiple transcripts
        with_diarization=False, # Enable speaker diarization if needed
        batch_size=8, # ASR batch size (adjust based on VRAM)
        # Supabase logging (optional) - ensure .env file is set up if using
        # supabase_logging_enabled=True,
        # parliament_id="my_parliament", 
        # supabase_environment_file_path=".env" # if SUPABASE_URL/KEY are in .env
    )

    print(f"Starting alignment process. Results will be saved in: {OUTPUT_DIR}")
    # To process all entries in the CSV:
    pipeline.process_all()

    # To process a specific subset of video IDs:
    # pipeline.process_subset(video_ids=["my_audio_session_1"])

    print("Alignment process finished.")
```

For a more granular example using individual components like `AudioSegmenter` and `TranscriptAligner`, see `examples/basic_alignment.py`.

## Core Components

-   **`AlignmentPipeline`**: The main orchestrator. It reads metadata, finds audio and transcript files, manages segmentation, preprocessing, alignment, and selection of the best transcript(s).
-   **`AudioSegmenter`**: Handles audio segmentation (breaking audio into smaller pieces) and transcription of these segments using an ASR model.
-   **`TranscriptAligner`**: Aligns the ASR-transcribed segments with the text from human-generated transcripts.
-   **Transcript Preprocessors**: A system of classes (`TxtPreprocessor`, `PdfPreprocessor`, `SrtPreprocessor`, `DocxPreprocessor`, `HtmlPreprocessor`) that clean and prepare transcript files of various formats for alignment. They are dynamically chosen based on file extension.
-   **Data Models (`TranscribedSegment`, `AlignedTranscript`)**: Dataclasses representing ASR segments and the final aligned output.

## Configuration

The `AlignmentPipeline` and its underlying components can be configured with various parameters during initialization, including:

-   Paths for data, output, and caches.
-   Hugging Face token and cache directory for models.
-   Language for ASR.
-   ASR batch size.
-   CER thresholds for transcript selection.
-   Strategy for handling multiple transcripts for a single audio file (`best_only`, `threshold_all`, `force_all`).
-   Flags for enabling/disabling diarization and pydub silence detection.
-   Custom HTML processor function.
-   Supabase logging credentials and settings.

Refer to the `AlignmentPipeline.__init__` method in `parliament_transcript_aligner/pipeline/alignment_pipeline.py` for a full list of parameters.

## Supabase Logging

The pipeline supports optional logging of progress and metrics to a Supabase database. To enable this:
1.  Set `supabase_logging_enabled=True` when initializing `AlignmentPipeline`.
2.  Provide `parliament_id`.
3.  Provide Supabase credentials (`supabase_url`, `supabase_key`) directly, or set them as environment variables, or provide a path to an environment file (`supabase_environment_file_path`) containing them.
    Example `.env` file (place it in the directory where you run your script, e.g., `alignment_pipeline/.env`):
    ```env
    SUPABASE_URL="your_supabase_url"
    SUPABASE_KEY="your_supabase_key"
    ```
    Ensure `python-dotenv` is installed (`pip install python-dotenv`) for automatic loading from `.env`.

See `parliament_transcript_aligner/utils/logging/supabase_logging.py` and `docs/diagrams/improved_logging.md` for more details on the schema and client.

## Detailed Documentation

For more detailed information on the architecture, components, data flow, and implementation status, please refer to the `docs/` directory:
-   [Component Interaction](docs/diagrams/component_diagram.md)
-   [Data Flow](docs/diagrams/data_flow.md)
-   [Implementation Status](docs/diagrams/implementation_status.md)
-   [Directory Structure](docs/directory_structure.md)
-   [Alignment Pipeline Details](parliament_transcript_aligner/pipeline/alignment_pipeline.md)
-   [Supabase Logging Details](parliament_transcript_aligner/utils/logging/supabase_loggin.md)

## Contributing

Contributions are welcome! Please refer to (TBD - Contribution Guidelines to be added) for more information on how to contribute.

## License

The license for this project is currently TBD. Please see the `LICENSE` file for more details once it is finalized.
