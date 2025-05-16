#!/bin/bash
#SBATCH --mail-type=NONE
#SBATCH --job-name=iceland_batch_test
#SBATCH --output=/itet-stor/spfisterer/net_scratch/Downloading/countries/iceland/logs/batch_test_%j.out
#SBATCH --error=/itet-stor/spfisterer/net_scratch/Downloading/countries/iceland/logs/batch_test_%j.err
#SBATCH --mem=8G
#SBATCH --nodes=1
#SBATCH --cpus-per-task=2
#SBATCH --array=0-0  # Just 1 job for testing

ETH_USERNAME=spfisterer
PROJECT_NAME=Downloading/countries/iceland
DIRECTORY=/itet-stor/${ETH_USERNAME}/net_scratch/${PROJECT_NAME}
CONDA_ENVIRONMENT=video_processing

# Export library path to ensure shared libraries are found
export LD_LIBRARY_PATH=/itet-stor/${ETH_USERNAME}/net_scratch/conda_envs/${CONDA_ENVIRONMENT}/lib:$LD_LIBRARY_PATH

# Add current directory to Python path
export PYTHONPATH=${DIRECTORY}:${PYTHONPATH}

# For testing, we'll only process a few files
START_IDX=7880
END_IDX=7890

# Set batch storage options
# Set to true to enable batch storage
USE_BATCH_STORAGE=true
# How often to update batch files (every N transcripts)
UPDATE_FREQUENCY=5

cd ${DIRECTORY}

# Activate conda
source /itet-stor/${ETH_USERNAME}/net_scratch/conda/bin/activate
export CONDA_ENVS_PATH=/itet-stor/${ETH_USERNAME}/net_scratch/conda_envs
conda activate ${CONDA_ENVIRONMENT}

# Create logs directory if it doesn't exist
mkdir -p logs

# Log start of job
echo "Batch storage test job started at: $(date)" > logs/batch_test_job.log
echo "Processing files ${START_IDX} to ${END_IDX}" >> logs/batch_test_job.log
echo "Batch storage: ${USE_BATCH_STORAGE}" >> logs/batch_test_job.log
echo "Update frequency: ${UPDATE_FREQUENCY}" >> logs/batch_test_job.log

# Build command with batch storage options
CMD="python download_scripts/main.py --start_idx ${START_IDX} --end_idx ${END_IDX} --csv_file iceland_links.csv --batch_storage --update_frequency ${UPDATE_FREQUENCY}"

# Execute command
echo "Running command: ${CMD}" >> logs/batch_test_job.log
eval ${CMD} 2>&1 | tee -a logs/batch_test_job.log

# Log end of job
echo "Batch storage test job finished at: $(date)" >> logs/batch_test_job.log 