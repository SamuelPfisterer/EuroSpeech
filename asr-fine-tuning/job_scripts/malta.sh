#!/bin/bash
#SBATCH --job-name=fine_tune_malta
#SBATCH --mail-type=ALL
#SBATCH --output=/itet-stor/spfisterer/net_scratch/Downloading/fine-tuning/logs/malta_%j.out
#SBATCH --error=/itet-stor/spfisterer/net_scratch/Downloading/fine-tuning/logs/malta_%j.err
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
python ${PROJECT_DIR}/fine_tune_whisper.py  --dataset_repo_name "disco-eth/EuroSpeech" --subset_name "malta" --language "Maltese"

# Send more noteworthy information to the output log
echo "Finished at: $(date)"

# End the script with exit code 0
exit 0
