#!/bin/bash
#SBATCH --mail-type=NONE
#SBATCH --output=/itet-stor/spfisterer/net_scratch/Downloading/Estonia/logs/%j.out
#SBATCH --error=/itet-stor/spfisterer/net_scratch/Downloading/Estonia/logs/%j.err
#SBATCH --mem=20G
#SBATCH --nodes=1
#SBATCH --cpus-per-task=4
#SBATCH --array=0-43  # 44 jobs, each processing 10 videos (last one handles 6)
#SBATCH --array=1-43  # Just run the first batch (videos 0-9)

ETH_USERNAME=spfisterer
PROJECT_NAME=Downloading/Estonia
DIRECTORY=/itet-stor/${ETH_USERNAME}/net_scratch/${PROJECT_NAME}
CONDA_ENVIRONMENT=video_processing

# Calculate start and end indices for this job
START_IDX=$((SLURM_ARRAY_TASK_ID * 10))
if [ $SLURM_ARRAY_TASK_ID -eq 43 ]; then
    # Last batch handles remaining 6 videos
    END_IDX=436
else
    END_IDX=$(((SLURM_ARRAY_TASK_ID + 1) * 10))
fi

cd ${DIRECTORY}

# Activate conda
source /itet-stor/${ETH_USERNAME}/net_scratch/conda/bin/activate
conda activate ${CONDA_ENVIRONMENT}

# Log start of job
echo "Job started at: $(date)" >> logs/job_${SLURM_ARRAY_TASK_ID}.log
echo "Processing videos ${START_IDX} to ${END_IDX}" >> logs/job_${SLURM_ARRAY_TASK_ID}.log

# Execute code
python scripts/main.py --start_idx ${START_IDX} --end_idx ${END_IDX} 2>&1 | tee -a logs/job_${SLURM_ARRAY_TASK_ID}.log

# Log end of job
echo "Job finished at: $(date)" >> logs/job_${SLURM_ARRAY_TASK_ID}.log