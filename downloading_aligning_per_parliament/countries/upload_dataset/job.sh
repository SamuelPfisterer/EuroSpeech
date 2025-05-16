#!/bin/bash
#SBATCH --mail-type=ALL                     # Mail events (NONE, BEGIN, END, FAIL, ALL)
#SBATCH --job-name=upload_country          # Job name - will be updated below
#SBATCH --output=/itet-stor/spfisterer/net_scratch/Downloading/countries/upload_dataset/logs/%x_%j.out  # Standard output log - %x=job-name, %j=job-id
#SBATCH --error=/itet-stor/spfisterer/net_scratch/Downloading/countries/upload_dataset/logs/%x_%j.err   # Standard error log - %x=job-name, %j=job-id
#SBATCH --mem=500G                            # Memory per node (adjust based on testing)
#SBATCH --nodes=1                            # Run on a single node
#SBATCH --cpus-per-task=4                    # Number of CPU cores per task (adjust based on testing)
#SBATCH --time=24:00:00                      # Time limit hrs:min:sec (adjust as needed)

# --- User Configuration ---
ETH_USERNAME=spfisterer
BASE_PROJECT_DIR=/itet-stor/${ETH_USERNAME}/net_scratch/Downloading # Base directory for the project
CONDA_ENVIRONMENT=rixvox_python310             # Your conda environment name
LOG_DIR=${BASE_PROJECT_DIR}/countries/upload_dataset/logs # Directory for Slurm logs
# --- End User Configuration ---

# --- Derived Paths ---
COUNTRIES_DATA_DIR=${BASE_PROJECT_DIR}/countries
SCRIPT_DIR=${BASE_PROJECT_DIR}/countries/upload_dataset/scripts
MANIFEST_DIR=${BASE_PROJECT_DIR}/countries/upload_dataset/manifests
CONDA_BASE_DIR=/itet-stor/${ETH_USERNAME}/net_scratch/conda # Adjust if your conda base is different

# --- Environment Variable Checks ---
if [ -z "${COUNTRY_NAME}" ]; then
  echo "ERROR: COUNTRY_NAME environment variable is not set."
  echo "Please submit using: sbatch --export=COUNTRY_NAME=your_country script.sh"
  exit 1
fi

# --- Update Job Name and Log Paths Dynamically ---
#SBATCH --job-name=upload_${COUNTRY_NAME}
#SBATCH --output=${LOG_DIR}/upload_${COUNTRY_NAME}_%j.out
#SBATCH --error=${LOG_DIR}/upload_${COUNTRY_NAME}_%j.err

# --- Environment Setup ---
echo "Setting up environment..."
# Ensure logs directory exists
mkdir -p ${LOG_DIR}
# Ensure manifest directory exists
mkdir -p ${MANIFEST_DIR}

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

# Navigate to script directory for relative imports
cd ${SCRIPT_DIR}
echo "Changed directory to: $(pwd)"

# --- Job Execution ---
echo "-----------------------------------------"
echo "Job Started: $(date)"
echo "Processing Country: ${COUNTRY_NAME}"
echo "Manifest Directory: ${MANIFEST_DIR}"
echo "Script Directory: ${SCRIPT_DIR}"
echo "Slurm Job ID: ${SLURM_JOB_ID}"
echo "Running on host: $(hostname)"
echo "-----------------------------------------"

# --- Phase 1: Generate/Update Manifest ---
echo "\n--- Running Manifest Generation ---"
python generate_manifest.py \
    --countries-dir "${COUNTRIES_DATA_DIR}" \
    --manifest-dir "${MANIFEST_DIR}" \
    --country "${COUNTRY_NAME}"
    # Add --max-files if needed for testing, e.g., --max-files 10

MANIFEST_EXIT_CODE=$?
echo "Manifest generation finished with exit code: ${MANIFEST_EXIT_CODE}"
echo "-----------------------------------------"

# --- Phase 2: Batch Upload (Conditional) ---
if [ ${MANIFEST_EXIT_CODE} -eq 0 ]; then
    echo "\n--- Running Batch Upload ---"
    python batch_upload.py \
        --manifest-dir "${MANIFEST_DIR}" \
        --country "${COUNTRY_NAME}" 
        # Add --max-files if needed for testing, e.g., --max-files 5
        # Token is handled via .env or login within the script

    UPLOAD_EXIT_CODE=$?
    echo "Batch upload finished with exit code: ${UPLOAD_EXIT_CODE}"
    echo "-----------------------------------------"
else
    echo "\n--- Skipping Batch Upload ---"
    echo "Manifest generation failed (Exit Code: ${MANIFEST_EXIT_CODE}). Cannot proceed with upload."
    echo "-----------------------------------------"
    exit 1 # Exit with error if manifest failed
fi

# --- Job Completion ---
echo "\nJob Finished: $(date)"
echo "-----------------------------------------"

# Check final exit code
if [ ${UPLOAD_EXIT_CODE} -ne 0 ]; then
    echo "Upload script exited with non-zero status (${UPLOAD_EXIT_CODE}). Check logs."
    exit ${UPLOAD_EXIT_CODE}
fi

exit 0