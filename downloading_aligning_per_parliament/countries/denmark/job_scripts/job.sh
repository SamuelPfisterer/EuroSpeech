#!/bin/bash
#SBATCH --mail-type=NONE
#SBATCH --job-name=down_denmark
#SBATCH --output=/itet-stor/spfisterer/net_scratch/Downloading/countries/denmark/logs/%j.out
#SBATCH --error=/itet-stor/spfisterer/net_scratch/Downloading/countries/denmark/logs/%j.err
#SBATCH --mem=8G
#SBATCH --nodes=1
#SBATCH --cpus-per-task=2
#SBATCH --array=0-3  # Split into 4 jobs

ETH_USERNAME=spfisterer
PROJECT_NAME=Downloading/countries/denmark
DIRECTORY=/itet-stor/${ETH_USERNAME}/net_scratch/${PROJECT_NAME}
CONDA_ENVIRONMENT=video_processing

# Export library path to ensure shared libraries are found
export LD_LIBRARY_PATH=/itet-stor/${ETH_USERNAME}/net_scratch/conda_envs/${CONDA_ENVIRONMENT}/lib:$LD_LIBRARY_PATH

# Add current directory to Python path
export PYTHONPATH=${DIRECTORY}:${PYTHONPATH}

# Calculate start and end indices for this job
TOTAL_FILES=1601  # Total number of sessions in the CSV
FILES_PER_JOB=401  # Split ~evenly across 4 jobs (401 * 4 = 1604, slightly more than needed)
START_IDX=$((SLURM_ARRAY_TASK_ID * FILES_PER_JOB))
if [ $SLURM_ARRAY_TASK_ID -eq 3 ]; then
    # Last batch handles remaining files
    END_IDX=${TOTAL_FILES}
else
    END_IDX=$(((SLURM_ARRAY_TASK_ID + 1) * FILES_PER_JOB))
fi

cd ${DIRECTORY}

# Activate conda
source /itet-stor/${ETH_USERNAME}/net_scratch/conda/bin/activate
export CONDA_ENVS_PATH=/itet-stor/${ETH_USERNAME}/net_scratch/conda_envs
conda activate ${CONDA_ENVIRONMENT}

# Create logs directory if it doesn't exist
mkdir -p logs

# Log start of job
echo "Job started at: $(date)" >> logs/job_${SLURM_ARRAY_TASK_ID}.log
echo "Processing files ${START_IDX} to ${END_IDX}" >> logs/job_${SLURM_ARRAY_TASK_ID}.log

# Execute code with the CSV file
python download_scripts/main.py \
    --start_idx ${START_IDX} \
    --end_idx ${END_IDX} \
    --csv_file "denmark_links.csv" \
    2>&1 | tee -a logs/job_${SLURM_ARRAY_TASK_ID}.log

# Log end of job
echo "Job finished at: $(date)" >> logs/job_${SLURM_ARRAY_TASK_ID}.log 