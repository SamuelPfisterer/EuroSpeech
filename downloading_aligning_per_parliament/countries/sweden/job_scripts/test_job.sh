#!/bin/bash
#SBATCH --mail-type=NONE
#SBATCH --output=/itet-stor/spfisterer/net_scratch/Downloading/countries/sweden/logs/test_job_%A_%a.out
#SBATCH --error=/itet-stor/spfisterer/net_scratch/Downloading/countries/sweden/logs/test_job_%A_%a.err
#SBATCH --mem=8G
#SBATCH --nodes=1
#SBATCH --cpus-per-task=2
#SBATCH --array=0-4  # 5 parallel jobs

ETH_USERNAME=spfisterer
PROJECT_NAME=Downloading/countries/sweden
DIRECTORY=/itet-stor/${ETH_USERNAME}/net_scratch/${PROJECT_NAME}
CONDA_ENVIRONMENT=video_processing

# Export library path to ensure shared libraries are found
export LD_LIBRARY_PATH=/itet-stor/${ETH_USERNAME}/net_scratch/conda_envs/${CONDA_ENVIRONMENT}/lib:$LD_LIBRARY_PATH

# Add current directory to Python path
export PYTHONPATH=${DIRECTORY}:${PYTHONPATH}

# Define random indices for each job
declare -a INDICES=(1234 2468 3702 4936 6170)
START_IDX=${INDICES[$SLURM_ARRAY_TASK_ID]}
END_IDX=$((START_IDX + 1))  # Process one file per job

cd ${DIRECTORY}

# Activate conda
source /itet-stor/${ETH_USERNAME}/net_scratch/conda/bin/activate
export CONDA_ENVS_PATH=/itet-stor/${ETH_USERNAME}/net_scratch/conda_envs
conda activate ${CONDA_ENVIRONMENT}

# Create logs directory if it doesn't exist
mkdir -p logs

# Log start of job
echo "Job started at: $(date)" >> logs/test_job_${SLURM_ARRAY_TASK_ID}.log
echo "Processing index ${START_IDX}" >> logs/test_job_${SLURM_ARRAY_TASK_ID}.log

# Execute code with the CSV file
python download_scripts/main.py \
    --start_idx ${START_IDX} \
    --end_idx ${END_IDX} \
    --csv_file "sweden_links.csv" \
    2>&1 | tee -a logs/test_job_${SLURM_ARRAY_TASK_ID}.log

# Log end of job
echo "Job finished at: $(date)" >> logs/test_job_${SLURM_ARRAY_TASK_ID}.log 