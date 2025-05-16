#!/bin/bash

# --- SLURM Directives ---
#SBATCH --job-name=webdataset_serbia    # Job name
#SBATCH --mail-type=ALL                 # Mail events (NONE, BEGIN, END, FAIL, ALL)
#SBATCH --cpus-per-task=1              # Run on a single CPU
#SBATCH --mem=60G                      # Request 60GB of memory
#SBATCH --time=48:00:00                # Time limit hrs:min:sec (increased to 48h)
#SBATCH --nodes=1                      # Run on a single node

# --- User Configuration ---
ETH_USERNAME=spfisterer
BASE_PROJECT_DIR=/itet-stor/${ETH_USERNAME}/net_scratch/Downloading
CONDA_ENVIRONMENT=rixvox_python310
LOG_DIR=${BASE_PROJECT_DIR}/countries/upload_dataset/logs
MANIFEST_DIR=${BASE_PROJECT_DIR}/countries/upload_dataset/manifests
OUTPUT_DIR=${BASE_PROJECT_DIR}/countries/upload_dataset/webdataset_output
CONDA_BASE_DIR=/itet-stor/${ETH_USERNAME}/net_scratch/conda

# Update output/error paths after variables are set
#SBATCH --output=${LOG_DIR}/webdataset_serbia_%j.out
#SBATCH --error=${LOG_DIR}/webdataset_serbia_%j.err

# --- Environment Setup ---
echo "Setting up environment..."
# Ensure logs directory exists
mkdir -p ${LOG_DIR}
# Ensure output directory exists
mkdir -p ${OUTPUT_DIR}

# Export library path
export LD_LIBRARY_PATH=${CONDA_BASE_DIR}/envs/${CONDA_ENVIRONMENT}/lib:$LD_LIBRARY_PATH

# Activate conda environment
echo "Activating conda environment: ${CONDA_ENVIRONMENT}"
source ${CONDA_BASE_DIR}/bin/activate
export CONDA_ENVS_PATH=${CONDA_BASE_DIR}/envs
conda activate ${CONDA_ENVIRONMENT}
if [ $? -ne 0 ]; then
    echo "Failed to activate conda environment: ${CONDA_ENVIRONMENT}"
    exit 1
fi
echo "Conda environment activated."
echo "Python executable: $(which python)"

# Verify FFmpeg is available
if ! command -v ffmpeg &> /dev/null; then
    echo "FFmpeg is not available. Please install FFmpeg in the conda environment."
    exit 1
fi
echo "FFmpeg version: $(ffmpeg -version | head -n 1)"

# --- Job Information ---
echo "-----------------------------------------"
echo "Job Started: $(date)"
echo "Job ID: $SLURM_JOB_ID"
echo "Node: $SLURMD_NODENAME"
echo "Running on host: $(hostname)"
echo "Manifest Directory: ${MANIFEST_DIR}"
echo "Output Directory: ${OUTPUT_DIR}"
echo "-----------------------------------------"

# First, check current status
echo "\n--- Checking Current WebDataset Status for Serbia ---"
python create_local_webdataset_shards.py \
    --country serbia \
    --status \
    --check-tar

# --- Run Script ---
echo "\n--- Creating WebDataset Shards for Serbia ---"
python create_local_webdataset_shards.py \
    --country serbia \
    --manifest-dir ${MANIFEST_DIR} \
    --output-dir ${OUTPUT_DIR} \
    --max-shard-size-gb 1.0 \
    --extraction-method ffmpeg

WEBDATASET_EXIT_CODE=$?
echo "WebDataset creation finished with exit code: ${WEBDATASET_EXIT_CODE}"
echo "-----------------------------------------"

# --- Job Completion ---
echo "\nJob Finished: $(date)"
echo "-----------------------------------------"

# Check final exit code
if [ ${WEBDATASET_EXIT_CODE} -ne 0 ]; then
    echo "WebDataset creation script exited with non-zero status (${WEBDATASET_EXIT_CODE}). Check logs."
    exit ${WEBDATASET_EXIT_CODE}
fi

exit 0 