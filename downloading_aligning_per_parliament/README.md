# multilingual_tts_parliament
I am collecting all the scripts etc. to scrape, download and process parliament data to create a multilingual TTS dataset

# Parliament Speech Dataset Processing

This repository contains scripts for downloading and aligning parliamentary speech data to create a multilingual TTS dataset.

## Purpose

The scripts in this repository serve two main functions:
1. Download audio and transcripts based on standardized CSV files from web scraping
2. Align the downloaded audio with the corresponding transcripts

## Country Directory Structure

Each country directory typically follows this structure:

- **Alignment/** - Contains:
  - `alignment_output/` - JSON files resulting from the alignment pipeline
  - Testing script for the alignment pipeline for the specific country
  - Full alignment script with Slurm job configuration for cluster execution

- **download_scripts/** - Contains all components and state of the download pipeline used for the parliament

- **job_scripts/** - Contains Slurm job files for executing the download pipeline on a computing cluster

- **links/** - CSV files used by both the download and alignment pipelines

- **parliament_adjustment.md** - Documentation of required modifications to the download pipeline and necessary job scripts for the specific parliament

- **transcript_processors.py** and **video_link_extractors.py** (when applicable) - Custom logic for the download pipeline specific to the parliament
