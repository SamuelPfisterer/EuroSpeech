#!/bin/bash
#SBATCH --mail-type=NONE
#SBATCH --job-name=iceland_random_test
#SBATCH --output=/itet-stor/spfisterer/net_scratch/Downloading/countries/iceland/logs/random_test_%A_%a.out
#SBATCH --error=/itet-stor/spfisterer/net_scratch/Downloading/countries/iceland/logs/random_test_%A_%a.err
#SBATCH --mem=8G
#SBATCH --nodes=1
#SBATCH --cpus-per-task=2
#SBATCH --array=0-4  # 5 test jobs

ETH_USERNAME=spfisterer
PROJECT_NAME=Downloading/countries/iceland
DIRECTORY=/itet-stor/${ETH_USERNAME}/net_scratch/${PROJECT_NAME}
CONDA_ENVIRONMENT=video_processing

# Export library path to ensure shared libraries are found
export LD_LIBRARY_PATH=/itet-stor/${ETH_USERNAME}/net_scratch/conda_envs/${CONDA_ENVIRONMENT}/lib:$LD_LIBRARY_PATH

# Add current directory to Python path
export PYTHONPATH=${DIRECTORY}:${PYTHONPATH}

cd ${DIRECTORY}

# Activate conda
source /itet-stor/${ETH_USERNAME}/net_scratch/conda/bin/activate
export CONDA_ENVS_PATH=/itet-stor/${ETH_USERNAME}/net_scratch/conda_envs
conda activate ${CONDA_ENVIRONMENT}

# Create logs directory if it doesn't exist
mkdir -p logs

# Generate 5 random row numbers (considering there's a header row)
# Get total number of rows in the CSV file (minus header)
TOTAL_ROWS=59186

# Use a different random seed for each job in the array
RANDOM=$$_${SLURM_ARRAY_TASK_ID}

# Generate a random row number for this job
# Add 1 to skip the header row
RANDOM_ROW=$((RANDOM % TOTAL_ROWS + 1))

# Log start of job
echo "Job ${SLURM_ARRAY_TASK_ID} started at: $(date)" > logs/random_test_${SLURM_ARRAY_TASK_ID}.log
echo "Processing random row ${RANDOM_ROW} out of ${TOTAL_ROWS} total rows" >> logs/random_test_${SLURM_ARRAY_TASK_ID}.log

# Execute code to process the random row
python download_scripts/main.py \
    --start_idx ${RANDOM_ROW} \
    --end_idx $((RANDOM_ROW + 1)) \
    --csv_file "iceland_links.csv" \
    2>&1 | tee -a logs/random_test_${SLURM_ARRAY_TASK_ID}.log

# Log end of job
echo "Job ${SLURM_ARRAY_TASK_ID} finished at: $(date)" >> logs/random_test_${SLURM_ARRAY_TASK_ID}.log 