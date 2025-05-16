#!/bin/bash
#SBATCH --job-name=align_el
#SBATCH --mail-type=ALL
#SBATCH --output=/itet-stor/spfisterer/net_scratch/Downloading/countries/greece/Alignment/logs/%j.out
#SBATCH --error=/itet-stor/spfisterer/net_scratch/Downloading/countries/greece/Alignment/logs/%j.err
#SBATCH --mem=20G
#SBATCH --nodes=1
#SBATCH --cpus-per-task=4
#SBATCH --gres=gpu:1
#SBATCH --nodelist=tikgpu[02,03,04,05,07],lbbgpu01,artongpu[01,06,07]
#SBATCH --array=0-4  # 5 jobs across the GPUs

ETH_USERNAME=spfisterer
PROJECT_DIR=/itet-stor/${ETH_USERNAME}/net_scratch/Downloading/countries/greece
CONDA_ENVIRONMENT=rixvox_python310

# Exit on errors
set -o errexit

# Set a directory for temporary files unique to the job
TMPDIR=$(mktemp -d)
if [[ ! -d ${TMPDIR} ]]; then
    echo 'Failed to create temp directory' >&2
    exit 1
fi
trap "exit 1" HUP INT TERM
trap 'rm -rf "${TMPDIR}"' EXIT
export TMPDIR

# Create logs directory if it doesn't exist
mkdir -p ${PROJECT_DIR}/Alignment/logs

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
python ${PROJECT_DIR}/Alignment/alignment_job.py ${SLURM_ARRAY_TASK_ID} 9

# Send more noteworthy information to the output log
echo "Finished at: $(date)"

# End the script with exit code 0
exit 0
