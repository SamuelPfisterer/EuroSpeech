#!/bin/bash
#SBATCH --mail-type=NONE
#SBATCH --output=/itet-stor/spfisterer/net_scratch/Downloading/Germany/logs/%j.out
#SBATCH --error=/itet-stor/spfisterer/net_scratch/Downloading/Germany/logs/%j.err
#SBATCH --mem=20G
#SBATCH --nodes=1
#SBATCH --cpus-per-task=4
#SBATCH --array=0-9  # 10 batches (0-9) for 2001 rows with 200 per batch

ETH_USERNAME=spfisterer
PROJECT_NAME=Downloading/Germany
DIRECTORY=/itet-stor/${ETH_USERNAME}/net_scratch/${PROJECT_NAME}
CONDA_ENVIRONMENT=video_processing
VIDEOS_PER_BATCH=200
TOTAL_ROWS=2001

# Calculate start and end indices for this job
START_IDX=$((SLURM_ARRAY_TASK_ID * VIDEOS_PER_BATCH))
if [ $SLURM_ARRAY_TASK_ID -eq 22 ]; then
    # Last batch handles remaining 5 videos (220-224)
    END_IDX=$TOTAL_ROWS
else
    END_IDX=$(((SLURM_ARRAY_TASK_ID + 1) * VIDEOS_PER_BATCH))
fi

cd ${DIRECTORY}

# Activate conda
source /itet-stor/${ETH_USERNAME}/net_scratch/conda/bin/activate
conda activate ${CONDA_ENVIRONMENT}

# Create logs directory if it doesn't exist
mkdir -p ${DIRECTORY}/logs

# Log start of job
echo "=== Job Information ===" >> logs/job_${SLURM_ARRAY_TASK_ID}.log
echo "Job ID: ${SLURM_JOB_ID}" >> logs/job_${SLURM_ARRAY_TASK_ID}.log
echo "Array Task ID: ${SLURM_ARRAY_TASK_ID}" >> logs/job_${SLURM_ARRAY_TASK_ID}.log
echo "Start Index: ${START_IDX}" >> logs/job_${SLURM_ARRAY_TASK_ID}.log
echo "End Index: ${END_IDX}" >> logs/job_${SLURM_ARRAY_TASK_ID}.log
echo "Working Directory: ${DIRECTORY}" >> logs/job_${SLURM_ARRAY_TASK_ID}.log
echo "Started at: $(date)" >> logs/job_${SLURM_ARRAY_TASK_ID}.log
echo "====================\n" >> logs/job_${SLURM_ARRAY_TASK_ID}.log

# Execute code
python scripts/main.py --start_idx ${START_IDX} --end_idx ${END_IDX} 2>&1 | tee -a logs/job_${SLURM_ARRAY_TASK_ID}.log

# Log end of job
echo "\n====================" >> logs/job_${SLURM_ARRAY_TASK_ID}.log
echo "Job finished at: $(date)" >> logs/job_${SLURM_ARRAY_TASK_ID}.log
echo "====================" >> logs/job_${SLURM_ARRAY_TASK_ID}.log