#!/bin/bash
#SBATCH --mail-type=NONE
#SBATCH --job-name=iceland_download
#SBATCH --output=/itet-stor/spfisterer/net_scratch/Downloading/countries/iceland/logs/%j.out
#SBATCH --error=/itet-stor/spfisterer/net_scratch/Downloading/countries/iceland/logs/%j.err
#SBATCH --mem=8G
#SBATCH --nodes=1
#SBATCH --cpus-per-task=2
#SBATCH --array=0-4  # Adjust based on total number of files

ETH_USERNAME=spfisterer
PROJECT_NAME=Downloading/countries/iceland
DIRECTORY=/itet-stor/${ETH_USERNAME}/net_scratch/${PROJECT_NAME}
CONDA_ENVIRONMENT=video_processing

# Export library path to ensure shared libraries are found
export LD_LIBRARY_PATH=/itet-stor/${ETH_USERNAME}/net_scratch/conda_envs/${CONDA_ENVIRONMENT}/lib:$LD_LIBRARY_PATH

# Add current directory to Python path
export PYTHONPATH=${DIRECTORY}:${PYTHONPATH}

# Calculate start and end indices for this job
# Adjust these numbers based on your CSV file size
TOTAL_FILES=59186  # Total lines minus header line
FILES_PER_JOB=11837  # Adjust based on TOTAL_FILES and desired number of jobs
START_IDX=$((SLURM_ARRAY_TASK_ID * FILES_PER_JOB))
if [ $SLURM_ARRAY_TASK_ID -eq 4 ]; then
    # Last batch handles remaining files
    END_IDX=${TOTAL_FILES}
else
    END_IDX=$(((SLURM_ARRAY_TASK_ID + 1) * FILES_PER_JOB))
fi

# Set batch storage options
# Set to true to enable batch storage, false to use individual files
USE_BATCH_STORAGE=true
# How often to update batch files (every N transcripts)
UPDATE_FREQUENCY=50

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
echo "Batch storage: ${USE_BATCH_STORAGE}" >> logs/job_${SLURM_ARRAY_TASK_ID}.log
echo "Update frequency: ${UPDATE_FREQUENCY}" >> logs/job_${SLURM_ARRAY_TASK_ID}.log

# Build command with conditional batch storage options
CMD="python download_scripts/main.py --start_idx ${START_IDX} --end_idx ${END_IDX} --csv_file iceland_links.csv"

if [ "${USE_BATCH_STORAGE}" = true ]; then
    CMD="${CMD} --batch_storage --update_frequency ${UPDATE_FREQUENCY}"
fi

# Execute command
echo "Running command: ${CMD}" >> logs/job_${SLURM_ARRAY_TASK_ID}.log
eval ${CMD} 2>&1 | tee -a logs/job_${SLURM_ARRAY_TASK_ID}.log

# Log end of job
echo "Job finished at: $(date)" >> logs/job_${SLURM_ARRAY_TASK_ID}.log 