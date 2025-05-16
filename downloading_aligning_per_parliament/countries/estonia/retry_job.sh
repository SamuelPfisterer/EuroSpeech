#!/bin/bash
#SBATCH --mail-type=NONE
#SBATCH --output=/itet-stor/spfisterer/net_scratch/Downloading/Estonia/logs/retry_%j.out
#SBATCH --error=/itet-stor/spfisterer/net_scratch/Downloading/Estonia/logs/retry_%j.err
#SBATCH --mem=20G
#SBATCH --nodes=1
#SBATCH --cpus-per-task=4
#SBATCH --array=0-11  # 12 jobs: 11 jobs process 10 videos each, last job processes remaining 4
#SBATCH --array=2-11  # Just test second batch

ETH_USERNAME=spfisterer
PROJECT_NAME=Downloading/Estonia
DIRECTORY=/itet-stor/${ETH_USERNAME}/net_scratch/${PROJECT_NAME}
CONDA_ENVIRONMENT=video_processing

# Calculate start and end indices for this job
START_IDX=$((SLURM_ARRAY_TASK_ID * 10))
if [ $SLURM_ARRAY_TASK_ID -eq 11 ]; then
    # Last batch handles remaining 4 videos
    END_IDX=114
else
    END_IDX=$(((SLURM_ARRAY_TASK_ID + 1) * 10))
fi

cd ${DIRECTORY}

# Activate conda
source /itet-stor/${ETH_USERNAME}/net_scratch/conda/bin/activate
conda activate ${CONDA_ENVIRONMENT}

# Create failed_downloads.csv if it doesn't exist
if [ ! -f failed_downloads.csv ]; then
    python scripts/create_retry_csv.py
fi

# Execute retry code
python scripts/retry_downloads.py --start_idx ${START_IDX} --end_idx ${END_IDX}