#!/usr/bin/env python3

import argparse
import logging
from pathlib import Path
from huggingface_hub import HfFolder
from dotenv import load_dotenv
import os
from datasets import load_dataset

# Load environment variables from the same location as batch_upload.py
load_dotenv("/itet-stor/spfisterer/net_scratch/Alignment/testing/own_pipeline/.env")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

def upload_webdataset(country_dir: Path, repo_id: str, token: str):
    """Upload WebDataset TAR files using the datasets library."""
    
    # Process each split
    for split_name in ['test', 'validation', 'train']:
        split_path = country_dir / split_name
        if not split_path.exists():
            logging.info(f"No {split_name} directory found in {country_dir}")
            continue
            
        logging.info(f"Processing {split_name} directory: {split_path}")
        
        # Get all TAR files for this split
        tar_files = list(split_path.glob("*.tar"))
        if not tar_files:
            logging.info(f"No TAR files found in {split_path}")
            logging.info(f"Files in {split_path}: {list(split_path.glob('*'))}")
            continue
            
        tar_paths = [str(f) for f in tar_files]
        logging.info(f"Found {len(tar_paths)} TAR files for {split_name} split")
        
        try:
            # Load the WebDataset
            dataset = load_dataset(
                "webdataset",
                data_files={split_name: tar_paths},
                split=split_name,
                num_proc=4  # Use multiprocessing for faster loading
            )
            
            # Push to hub with appropriate config name and split
            config_name = f"{country_dir.name}"  # Use country name as config
            logging.info(f"Pushing {split_name} split to {repo_id}/{config_name}")
            
            dataset.push_to_hub(
                repo_id=repo_id,
                config_name=config_name,
                split=split_name,
                token=token,
                commit_message=f"Add {split_name} split for {config_name}",
            )
            
            logging.info(f"Successfully uploaded {split_name} split")
            
        except Exception as e:
            logging.error(f"Error processing {split_name} split: {e}")

def main():
    parser = argparse.ArgumentParser(description="Upload WebDataset TAR files to Hugging Face Hub")
    parser.add_argument(
        "--webdataset-dir",
        type=Path,
        default="./webdataset_output",
        help="Root directory containing country-specific WebDataset TAR files"
    )
    parser.add_argument(
        "--country",
        required=True,
        help="Country name (e.g., germany)"
    )
    parser.add_argument(
        "--repo-id",
        default="SamuelPfisterer1/EuroSpeech-Webdataset",
        help="Hugging Face Hub repository ID"
    )
    parser.add_argument(
        "--hf-token",
        default=os.getenv("HF_AUTH_TOKEN"),
        help="Hugging Face API token"
    )
    
    args = parser.parse_args()
    
    # Get token from args, environment, or HF folder
    hf_token = args.hf_token or HfFolder.get_token()
    if not hf_token:
        logging.error("Hugging Face token not found. Login using `huggingface-cli login` or provide --hf-token")
        return

    country_dir = args.webdataset_dir / args.country.lower()
    if not country_dir.exists():
        logging.error(f"Country directory not found: {country_dir}")
        return

    logging.info(f"Starting upload for country: {args.country}")
    logging.info(f"WebDataset directory: {country_dir}")
    logging.info(f"Target repository: {args.repo_id}")

    upload_webdataset(country_dir, args.repo_id, hf_token)
    logging.info(f"Upload process completed for country: {args.country}")

if __name__ == "__main__":
    main() 