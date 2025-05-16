#!/bin/bash
#SBATCH --mail-type=NONE
#SBATCH --output=/itet-stor/spfisterer/net_scratch/Downloading/countries/latvia/logs/%j.out
#SBATCH --error=/itet-stor/spfisterer/net_scratch/Downloading/countries/latvia/logs/%j.err
#SBATCH --mem=8G
#SBATCH --nodes=1
#SBATCH --cpus-per-task=2
#SBATCH --array=0-2  # 3 processes

ETH_USERNAME=spfisterer
PROJECT_NAME=Downloading/countries/latvia
DIRECTORY=/itet-stor/${ETH_USERNAME}/net_scratch/${PROJECT_NAME}
CONDA_ENVIRONMENT=video_processing

# Export library path to ensure shared libraries are found
export LD_LIBRARY_PATH=/itet-stor/${ETH_USERNAME}/net_scratch/conda_envs/${CONDA_ENVIRONMENT}/lib:$LD_LIBRARY_PATH

# Add current directory to Python path
export PYTHONPATH=${DIRECTORY}:${PYTHONPATH}

# Fixed range: 700 to 1050 (total of 351 rows)
TOTAL_RANGE=351  # 1050 - 700 + 1
ROWS_PER_JOB=$((TOTAL_RANGE / 3))  # Approximately 117 rows per job
START_ROW=700  # First row to process

# Calculate start and end indices for this job
START_IDX=$((START_ROW + SLURM_ARRAY_TASK_ID * ROWS_PER_JOB))
if [ $SLURM_ARRAY_TASK_ID -eq 2 ]; then
    # Last batch handles remaining rows up to 1050
    END_IDX=1050
else
    END_IDX=$((START_ROW + (SLURM_ARRAY_TASK_ID + 1) * ROWS_PER_JOB - 1))
fi

cd ${DIRECTORY}

# Activate conda
source /itet-stor/${ETH_USERNAME}/net_scratch/conda/bin/activate
export CONDA_ENVS_PATH=/itet-stor/${ETH_USERNAME}/net_scratch/conda_envs
conda activate ${CONDA_ENVIRONMENT}

# Create logs directory if it doesn't exist
mkdir -p logs

# Log start of job
echo "Job started at: $(date)" >> logs/remaining_links_${SLURM_ARRAY_TASK_ID}.log
echo "Processing rows ${START_IDX} to ${END_IDX}" >> logs/remaining_links_${SLURM_ARRAY_TASK_ID}.log

# Execute code with the CSV file
python download_scripts/main.py \
    --start_idx ${START_IDX} \
    --end_idx ${END_IDX} \
    --csv_file "latvia_links.csv" \
    2>&1 | tee -a logs/remaining_links_${SLURM_ARRAY_TASK_ID}.log

# Log end of job
echo "Job finished at: $(date)" >> logs/remaining_links_${SLURM_ARRAY_TASK_ID}.log 