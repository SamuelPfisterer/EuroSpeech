#!/bin/bash
#SBATCH --mail-type=NONE
#SBATCH --output=/itet-stor/spfisterer/net_scratch/Downloading/countries/italy/logs/%j.out
#SBATCH --error=/itet-stor/spfisterer/net_scratch/Downloading/countries/italy/logs/%j.err
#SBATCH --mem=8G
#SBATCH --nodes=1
#SBATCH --cpus-per-task=2
#SBATCH --array=0-0  # Just 1 job for testing

ETH_USERNAME=spfisterer
PROJECT_NAME=Downloading/countries/italy
DIRECTORY=/itet-stor/${ETH_USERNAME}/net_scratch/${PROJECT_NAME}
CONDA_ENVIRONMENT=video_processing

# Export library path to ensure shared libraries are found
export LD_LIBRARY_PATH=/itet-stor/${ETH_USERNAME}/net_scratch/conda_envs/${CONDA_ENVIRONMENT}/lib:$LD_LIBRARY_PATH

# Add current directory to Python path
export PYTHONPATH=${DIRECTORY}:${PYTHONPATH}

# For testing, we'll only process the first 2 files
START_IDX=0
END_IDX=2

cd ${DIRECTORY}

# Activate conda
source /itet-stor/${ETH_USERNAME}/net_scratch/conda/bin/activate
export CONDA_ENVS_PATH=/itet-stor/${ETH_USERNAME}/net_scratch/conda_envs
conda activate ${CONDA_ENVIRONMENT}

# Debug information
echo "=== Debug Info ===" >> logs/test_job.log
echo "Current directory: $(pwd)" >> logs/test_job.log
echo "Python path: $(which python)" >> logs/test_job.log
echo "Conda env: $CONDA_PREFIX" >> logs/test_job.log
echo "LD_LIBRARY_PATH: $LD_LIBRARY_PATH" >> logs/test_job.log
echo "Listing conda lib directory:" >> logs/test_job.log
ls -l $CONDA_PREFIX/lib/libnss* >> logs/test_job.log 2>&1
echo "=== End Debug Info ===" >> logs/test_job.log

# Create logs directory if it doesn't exist
mkdir -p logs

# Log start of job
echo "Job started at: $(date)" >> logs/test_job.log
echo "Processing files ${START_IDX} to ${END_IDX}" >> logs/test_job.log

# Execute code with the CSV file
python download_scripts/main.py \
    --start_idx ${START_IDX} \
    --end_idx ${END_IDX} \
    --csv_file "italy_links.csv" \
    2>&1 | tee -a logs/test_job.log

# Log end of job
echo "Job finished at: $(date)" >> logs/test_job.log 