#!/bin/bash
#SBATCH --mail-type=NONE
#SBATCH --output=/itet-stor/spfisterer/net_scratch/Downloading/countries/bosnia-herzegovina/logs/%j.out
#SBATCH --error=/itet-stor/spfisterer/net_scratch/Downloading/countries/bosnia-herzegovina/logs/%j.err
#SBATCH --mem=8G
#SBATCH --nodes=1
#SBATCH --cpus-per-task=2
#SBATCH --array=0-4  # 5 jobs, each processing ~64 files

ETH_USERNAME=spfisterer
PROJECT_NAME=Downloading/countries/bosnia-herzegovina
DIRECTORY=/itet-stor/${ETH_USERNAME}/net_scratch/${PROJECT_NAME}
CONDA_ENVIRONMENT=video_processing

# Calculate start and end indices for this job
TOTAL_FILES=317  # Total number of sessions in CSV (updated to actual count)
FILES_PER_JOB=64  # Each job processes ~64 files
START_IDX=$((SLURM_ARRAY_TASK_ID * FILES_PER_JOB))
if [ $SLURM_ARRAY_TASK_ID -eq 4 ]; then
    # Last batch handles remaining files
    END_IDX=${TOTAL_FILES}
else
    END_IDX=$(((SLURM_ARRAY_TASK_ID + 1) * FILES_PER_JOB))
fi

cd ${DIRECTORY}

# Activate conda
source /itet-stor/${ETH_USERNAME}/net_scratch/conda/bin/activate
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
    --csv_file "bosnia-herzegovina_links.csv" \
    2>&1 | tee -a logs/job_${SLURM_ARRAY_TASK_ID}.log

# Log end of job
echo "Job finished at: $(date)" >> logs/job_${SLURM_ARRAY_TASK_ID}.log 