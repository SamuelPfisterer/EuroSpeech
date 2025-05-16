#!/bin/bash
#SBATCH --job-name=fine_tune_slovenia
#SBATCH --mail-type=ALL
#SBATCH --output=/itet-stor/spfisterer/net_scratch/Downloading/fine-tuning/logs/slovenia_%j.out
#SBATCH --error=/itet-stor/spfisterer/net_scratch/Downloading/fine-tuning/logs/slovenia_%j.err
#SBATCH --mem=100G
#SBATCH --nodes=1
#SBATCH --cpus-per-task=16
#SBATCH --gres=gpu:1
#SBATCH --nodelist=tikgpu08

ETH_USERNAME=spfisterer
PROJECT_DIR=/itet-stor/${ETH_USERNAME}/net_scratch/Downloading/fine-tuning
CONDA_ENVIRONMENT=fine-tuning

# Exit on errors
set -o errexit

# Create logs directory if it doesn't exist
mkdir -p ${PROJECT_DIR}/logs

# Send noteworthy information to the output log
echo "Running on node: $(hostname)"
echo "In directory: $(pwd)"
echo "Starting on: $(date)"
echo "SLURM_JOB_ID: ${SLURM_JOB_ID}"
echo "SLURM_ARRAY_TASK_ID: ${SLURM_ARRAY_TASK_ID}"

# Activate conda environment
source /itet-stor/${ETH_USERNAME}/net_scratch/conda/bin/activate
conda activate ${CONDA_ENVIRONMENT}
echo "Conda environment ${CONDA_ENVIRONMENT} activated"

# Execute the Python script with the task ID
python ${PROJECT_DIR}/fine_tune_whisper.py  --dataset_repo_name "SamuelPfisterer1/slovenia" --subset_name "slovenia_3_percent" --language "Slovenian"

# Send more noteworthy information to the output log
echo "Finished at: $(date)"

# End the script with exit code 0
exit 0
