# EuroSpeech: A Multilingual Parliamentary Speech Corpus and Processing Toolkit

This repository contains the complete toolkit and resources for the EuroSpeech project, aimed at creating large-scale multilingual speech datasets from parliamentary recordings. Our work introduces a scalable pipeline for dataset construction and the EuroSpeech corpus itself, which provides substantial high-quality speech data across numerous European languages.

**For a detailed understanding of the project, the dataset, and the pipeline's impact, please refer to our paper: "EuroSpeech: A Multilingual Speech Corpus" (NeurIPS 2025 Submission).**

The EuroSpeech dataset, built using this toolkit, comprises over 61,000 hours of aligned speech segments from 22 European parliaments, with 19 languages exceeding 1,000 hours and 22 languages exceeding 500 hours of high-quality speech data.

## Repository Structure and Workflow

The process of creating the EuroSpeech dataset involves several stages, each supported by a dedicated component within this repository:

1.  **`data_sourcing/`**:
    *   **Purpose**: Contains scripts and artifacts used for the initial data sourcing and metadata collection. This involves manually inspecting parliamentary websites, developing custom scraping scripts to extract links to media (audio/video) and transcripts, and organizing this information into standardized CSV files.
    *   **Output**: Metadata CSV files for each parliament, serving as input for the `download_pipeline`.
    *   (See `data_sourcing/DATA_SOURCING_README.md` for more details)

2.  **`download_pipeline/`**:
    *   **Purpose**: Automates the retrieval of audio, video, and transcript files based on the CSVs from `data_sourcing`. It handles diverse source types, converts media to a standard format (Opus audio), and organizes downloaded content. It also supports Supabase integration for progress tracking and optional batch storage for transcripts.
    *   **Input**: Metadata CSV files from `data_sourcing`.
    *   **Output**: Downloaded raw audio (.opus) and transcript files (various formats) organized by parliament and type.
    *   (See `download_pipeline/README.md` for setup and usage)

3.  **`downloading_aligning_per_parliament/`**:
    *   **Purpose**: Contains scripts and configurations tailored for each specific parliament for both downloading (using the `download_pipeline`) and aligning (using the `alignment_pipeline`). This directory often includes custom `transcript_processors.py`, `video_link_extractors.py`, and Slurm `job_scripts/` for execution on computing clusters.
    *   **Key Contents**: Country-specific directories, `parliament_adjustment.md` detailing necessary modifications, and scripts for download and alignment.
    *   (See `downloading_aligning_per_parliament/README.md` for more details on structure per parliament)

4.  **`alignment_pipeline/`**:
    *   **Purpose**: Transforms the raw, long-form audio and potentially noisy/non-verbatim transcripts into a dataset of short, precisely aligned audio segments (typically 3-20 seconds) paired with their corresponding textual transcriptions. It segments audio, transcribes segments using ASR, preprocesses various transcript formats, and employs a robust two-stage dynamic alignment algorithm.
    *   **Input**: Downloaded audio and transcript files from the `download_pipeline` (via `downloading_aligning_per_parliament` configurations).
    *   **Output**: JSON files containing aligned speech segments with timestamps and CER scores.
    *   (See `alignment_pipeline/README.md` for setup and usage)

5.  **`asr-fine-tuning/`**:
    *   **Purpose**: Provides scripts for fine-tuning ASR models (e.g., OpenAI Whisper) on the datasets created by the `alignment_pipeline`. This component was used to validate the quality of the EuroSpeech dataset and demonstrate its effectiveness in improving ASR performance for various languages.
    *   **Input**: Aligned speech datasets from the `alignment_pipeline`.
    *   **Output**: Fine-tuned ASR models and evaluation metrics (e.g., WER).
    *   (See `asr-fine-tuning/README.md` for setup and usage)

## General Setup

Each pipeline component (`download_pipeline`, `alignment_pipeline`, `asr-fine-tuning`) has its own specific setup instructions and dependencies, detailed in their respective `README.md` files and often managed via a `requirements.txt`.

Generally, you will need Python (>=3.8 recommended) and `pip`. It's highly recommended to use virtual environments for each component or for the project as a whole.

Example for setting up a component (e.g., `alignment_pipeline`):
```bash
cd alignment_pipeline
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt # If requirements.txt exists, or pip install . if setup.py is present
```

## Using the Toolkit

1.  **Data Sourcing**: Start by collecting metadata for the target parliament(s) using or adapting scripts in `data_sourcing/`.
2.  **Download Content**: Use the `download_pipeline/main.py` script, typically orchestrated via scripts in `downloading_aligning_per_parliament/` for a specific country, to download the raw audio and transcripts. Configure Supabase and proxy settings via a `.env` file in `download_pipeline/` as needed.
3.  **Align Data**: Use the `alignment_pipeline/` (e.g., `examples/basic_alignment.py` or the main `AlignmentPipeline` class) with configurations in `downloading_aligning_per_parliament/` to process the downloaded data and produce aligned speech segments.
4.  **Fine-tune ASR (Optional)**: Use the scripts in `asr-fine-tuning/` to train or fine-tune ASR models on the newly created aligned dataset.

## Citation

If you use the EuroSpeech dataset, this toolkit, or our processing methodologies in your research, please cite our paper:

```bibtex
@article{pfisterer2025eurospeech,
  title={EuroSpeech: A Multilingual Speech Corpus},
  author={Samuel Pfisterer and Florian Grötschla and Luca Lanzendörfer and Florian Yan and Roger Wattenhofer},
  journal={TBD}, % To Be Determined - Replace with actual arXiv ID or conference proceedings
  year={TBD} % To Be Determined - Or the actual year of publication
}
```

## License

The license for this project and the EuroSpeech dataset is currently TBD (To Be Determined). Please check back for updates.

## Contributing & Contact

Contributions to improve the toolkit or expand language coverage are welcome! (Further details on contribution guidelines will be added).

For questions or issues, please open an issue on this GitHub repository.
