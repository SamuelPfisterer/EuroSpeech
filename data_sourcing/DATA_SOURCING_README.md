# Data Sourcing for EuroSpeech

This directory contains the scripts and artifacts used for the initial data sourcing and metadata collection phase of the EuroSpeech dataset, as described in the paper "EuroSpeech: A Multilingual Speech Corpus".

## Purpose

The scripts in this repository were used to:

1. Extract metadata from parliamentary websites and APIs
2. Collect links to media files (audio/video) and their corresponding transcripts
3. Transform diverse and unstandardized parliamentary sources into a consistent CSV format for downstream processing

This is the first critical step in the EuroSpeech pipeline that enables the subsequent automated download and alignment steps to operate uniformly across different parliaments.

## Structure

Each country directory contains:

- **Scraping scripts** - Custom scripts that were designed for the specific parliament's website to extract relevant links
- **Metadata CSV files** - For some parliaments, the output CSV files containing the collected links are also included

## Workflow

For each parliament in the EuroSpeech dataset, we followed this workflow:

1. Manual inspection of the parliament's website to identify data formats, access methods, and session information structure
2. Development of custom scripts to extract metadata (audio/video URLs, transcript links, session identifiers)
3. Generation of standardized CSV files with the collected links

## Output

The primary output of these scripts was a standardized CSV file for each parliament containing:
- Media URLs (audio or video)
- Links to one or more potential transcripts
- Unique session identifiers
- Additional metadata when available

These CSV files served as the interface between the initial collection phase and the subsequent download and alignment pipelines.
