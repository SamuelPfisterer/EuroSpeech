# Finnish Parliament Session Data Downloader

This project contains scripts to download and process data from Finnish Parliament (Eduskunta) plenary sessions available online.

## Workflow

1.  **Scrape Session Links**:
    *   Run `scrape_session_links.py`.
    *   This script uses Playwright (browser automation) to visit the main session listing page (`https://verkkolahetys.eduskunta.fi/fi/taysistunnot`).
    *   It clicks "Load more" repeatedly to reveal all available sessions.
    *   It extracts the title, date, and URL for each session.
    *   **Output**: `session_links.csv` containing the list of all sessions.

2.  **Construct PDF Links for Each Session**:
    *   Run `add_pdf_links_to_session_links.py`.
    *   This script reads `session_links.csv` and constructs the direct PDF link for each session based on the session number and year in the URL.
    *   **Output**: `session_links_with_pdf.csv` — identical to the input, but with an additional `pdf_link` column containing the constructed PDF URL for each session.
    *   **Note**: The PDF links follow the pattern:
        *   `https://www.eduskunta.fi/FI/vaski/Poytakirja/Documents/PTK_{session_number}+{year}.pdf`
        *   For example, for session link `https://verkkolahetys.eduskunta.fi/fi/taysistunnot/taysistunto-127-2020`, the PDF link is `https://www.eduskunta.fi/FI/vaski/Poytakirja/Documents/PTK_127+2020.pdf`
        Also note, that these pdf links might not work for sessions before 2014

3.  **Process Session Content (Choose one method)**:

    *   **Method A: Using the Official API (Recommended for Transcripts)**
        *   Run `batch_process_sessions.py`.
        *   This script reads `session_links.csv`.
        *   For each session URL, it extracts the session ID (e.g., `PTK_125_2024`).
        *   It calls `process_session.py` for each session ID.
            *   `process_session.py` constructs the API URL and fetches the raw JSON transcript.
            *   It then uses `session_parser.py` to parse the raw JSON into a structured format.
        *   **Output**: Saves structured JSON transcript files (e.g., `parsed_PTK_125_2024.json`) into individual subdirectories within the `processed_sessions/` directory. A log file is also created.

    *   **Method B: Using Browser Scraping (For Media Links & Web Content)**
        *   Run `scrape_session_content.py` (Note: Currently set up for a single session; needs modification for batch processing).
        *   This script uses Playwright to visit a specific session URL.
        *   It extracts media stream URLs (Video/Audio).
        *   It scrapes the speech text, speaker information, and timing directly from the web page content.
        *   **Output**: Appends the scraped data for the session to `finland_sessions_data.json`.

## File Descriptions

*   `scrape_session_links.py`: Scrapes the main listing page to get all session URLs. Outputs `session_links.csv`.
*   `session_links.csv`: Contains the list of all parliamentary sessions (title, date, URL). Input for batch processing scripts.
*   `add_pdf_links_to_session_links.py`: Constructs direct PDF links for each session and outputs `session_links_with_pdf.csv`.
*   `session_links_with_pdf.csv`: Contains all original columns from `session_links.csv` plus a `pdf_link` column with the constructed PDF URL for each session.
*   `batch_process_sessions.py`: Orchestrates the processing of multiple sessions using the API method. Reads `session_links.csv`, calls `process_session.py`, and manages output directories and logging.
*   `process_session.py`: Fetches raw JSON transcript data from the API for a single session ID and uses `session_parser.py` to parse it.
*   `session_parser.py`: Contains the logic to parse the complex raw JSON structure from the API into a more usable format (metadata, list of speeches).
*   `scrape_session_content.py`: Scrapes media links and speech content directly from a single session's web page using browser automation.
*   `test_api.py`: A utility/testing script for interacting directly with the API, likely used during development. Not part of the main workflow.
*   `processed_sessions/` (Directory): Default output location for the API-based batch processing (`batch_process_sessions.py`). Contains subdirectories for each processed session.
*   `finland_sessions_data.json` (File): Default output file for the browser scraping method (`scrape_session_content.py`).

## Dependencies

*   Python 3.x
*   Libraries: `requests`, `playwright`, `csv`, `json`, `os`, `datetime`, `time`
    *   Playwright requires browser binaries to be installed (`playwright install`).

Choose the processing method (API or Scraping) based on whether you need the structured transcripts or the media links/webpage content.
