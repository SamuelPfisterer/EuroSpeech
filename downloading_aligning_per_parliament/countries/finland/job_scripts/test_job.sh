#!/bin/bash
#SBATCH --mail-type=NONE
#SBATCH --job-name=finland_download_test
#SBATCH --output=/itet-stor/spfisterer/net_scratch/Downloading/countries/finland/logs/%j.out
#SBATCH --error=/itet-stor/spfisterer/net_scratch/Downloading/countries/finland/logs/%j.err
#SBATCH --mem=8G
#SBATCH --nodes=1
#SBATCH --cpus-per-task=2
#SBATCH --array=0-0  # Just 1 job for testing

ETH_USERNAME=spfisterer
PROJECT_NAME=Downloading/countries/finland
DIRECTORY=/itet-stor/${ETH_USERNAME}/net_scratch/${PROJECT_NAME}
CONDA_ENVIRONMENT=video_processing

# Export library path to ensure shared libraries are found
export LD_LIBRARY_PATH=/itet-stor/${ETH_USERNAME}/net_scratch/conda_envs/${CONDA_ENVIRONMENT}/lib:$LD_LIBRARY_PATH

# Add current directory to Python path
export PYTHONPATH=${DIRECTORY}:${PYTHONPATH}

# For testing, we'll only process the first 2 files
START_IDX=5
END_IDX=8

cd ${DIRECTORY}

# Activate conda
source /itet-stor/${ETH_USERNAME}/net_scratch/conda/bin/activate
export CONDA_ENVS_PATH=/itet-stor/${ETH_USERNAME}/net_scratch/conda_envs
conda activate ${CONDA_ENVIRONMENT}

# Create logs directory if it doesn't exist
mkdir -p logs

# Log start of job
echo "Job started at: $(date)" >> logs/test_job.log
echo "Processing files ${START_IDX} to ${END_IDX}" >> logs/test_job.log

# Execute code with the CSV file
python download_scripts/main.py \
    --start_idx ${START_IDX} \
    --end_idx ${END_IDX} \
    --csv_file "finland_links.csv" \
    2>&1 | tee -a logs/test_job.log

# Log end of job
echo "Job finished at: $(date)" >> logs/test_job.log 