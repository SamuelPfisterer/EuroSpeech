# Parliament Download System Setup Guide

This guide explains how to set up and adjust the download system for any new parliament.

## Directory Structure
Before starting downloads, ensure the following directory structure for your parliament (replace `[parliament-name]` with your parliament's name, e.g., 'croatia', 'bosnia-herzegovina'):

```
[parliament-name]/
├── download_scripts/         # Contains all Python scripts (copied from template)
├── job_scripts/             # Contains job.sh and test_job.sh
├── links/                   # Contains the CSV file with session links
└── logs/                    # Will store job logs
```

## Required Steps

### 1. Copy Download Scripts
Copy all files from the template `download_scripts` directory to your parliament's `download_scripts` directory. These include:
- `download_utils.py`
- `initialize_parliament.py`
- `main.py`
- `supabase_config.py`
- `transcript_processors_template.py`
- Other relevant .py and .md files

### 2. Supabase Configuration
Edit `download_scripts/supabase_config.py`:
1. Change the `PARLIAMENT_ID` constant to your parliament's name:
```python
PARLIAMENT_ID = '[parliament-name]'  # e.g., 'croatia', 'bosnia-herzegovina'
```

### 3. Create Job Scripts

#### test_job.sh
Create this file in `job_scripts/` with these contents (replace all instances of `[parliament-name]`):
```bash
#!/bin/bash
#SBATCH --mail-type=NONE
#SBATCH --job-name=[parliament-name]_download_test
#SBATCH --output=/itet-stor/spfisterer/net_scratch/Downloading/countries/[parliament-name]/logs/%j.out
#SBATCH --error=/itet-stor/spfisterer/net_scratch/Downloading/countries/[parliament-name]/logs/%j.err
#SBATCH --mem=8G
#SBATCH --nodes=1
#SBATCH --cpus-per-task=2
#SBATCH --array=0-0  # Just 1 job for testing

ETH_USERNAME=spfisterer
PROJECT_NAME=Downloading/countries/[parliament-name]
DIRECTORY=/itet-stor/${ETH_USERNAME}/net_scratch/${PROJECT_NAME}
CONDA_ENVIRONMENT=video_processing

# Export library path to ensure shared libraries are found
export LD_LIBRARY_PATH=/itet-stor/${ETH_USERNAME}/net_scratch/conda_envs/${CONDA_ENVIRONMENT}/lib:$LD_LIBRARY_PATH

# Add current directory to Python path
export PYTHONPATH=${DIRECTORY}:${PYTHONPATH}

# For testing, we'll only process the first 2 files
START_IDX=0
END_IDX=2

cd ${DIRECTORY}

# Activate conda
source /itet-stor/${ETH_USERNAME}/net_scratch/conda/bin/activate
export CONDA_ENVS_PATH=/itet-stor/${ETH_USERNAME}/net_scratch/conda_envs
conda activate ${CONDA_ENVIRONMENT}

# Create logs directory if it doesn't exist
mkdir -p logs

# Log start of job
echo "Job started at: $(date)" >> logs/test_job.log
echo "Processing files ${START_IDX} to ${END_IDX}" >> logs/test_job.log

# Execute code with the CSV file
python download_scripts/main.py \
    --start_idx ${START_IDX} \
    --end_idx ${END_IDX} \
    --csv_file "[parliament-name]_links.csv" \
    2>&1 | tee -a logs/test_job.log

# Log end of job
echo "Job finished at: $(date)" >> logs/test_job.log
```

#### job.sh
Create this file in `job_scripts/` (replace all instances of `[parliament-name]`):
```bash
#!/bin/bash
#SBATCH --mail-type=NONE
#SBATCH --job-name=[parliament-name]_download
#SBATCH --output=/itet-stor/spfisterer/net_scratch/Downloading/countries/[parliament-name]/logs/%j.out
#SBATCH --error=/itet-stor/spfisterer/net_scratch/Downloading/countries/[parliament-name]/logs/%j.err
#SBATCH --mem=8G
#SBATCH --nodes=1
#SBATCH --cpus-per-task=2
#SBATCH --array=0-4  # Adjust based on total number of files

ETH_USERNAME=spfisterer
PROJECT_NAME=Downloading/countries/[parliament-name]
DIRECTORY=/itet-stor/${ETH_USERNAME}/net_scratch/${PROJECT_NAME}
CONDA_ENVIRONMENT=video_processing

# Export library path to ensure shared libraries are found
export LD_LIBRARY_PATH=/itet-stor/${ETH_USERNAME}/net_scratch/conda_envs/${CONDA_ENVIRONMENT}/lib:$LD_LIBRARY_PATH

# Add current directory to Python path
export PYTHONPATH=${DIRECTORY}:${PYTHONPATH}

# Calculate start and end indices for this job
# Adjust these numbers based on your CSV file size
TOTAL_FILES=7000  # Replace with your actual number of sessions
FILES_PER_JOB=1400  # Adjust based on TOTAL_FILES and desired number of jobs
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
export CONDA_ENVS_PATH=/itet-stor/${ETH_USERNAME}/net_scratch/conda_envs
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
    --csv_file "[parliament-name]_links.csv" \
    2>&1 | tee -a logs/job_${SLURM_ARRAY_TASK_ID}.log

# Log end of job
echo "Job finished at: $(date)" >> logs/job_${SLURM_ARRAY_TASK_ID}.log
```

### 4. Prepare Links CSV File

1. Create a CSV file in the `links/` directory with your parliament's session links
2. Required CSV format:
   - One session per row
   - Must include columns for video and transcript URLs
   - Name format: `[parliament-name]_links.csv`
   - Additional metadata columns as needed for processing

### 5. Initialize Parliament Database Entry

Before running any jobs, initialize your parliament in the database:

```bash
python download_scripts/initialize_parliament.py \
    --parliament_id [parliament-name] \
    --csv_file [parliament-name]_links.csv
```

### 6. Job Configuration

Before running jobs, adjust these parameters based on your parliament's needs:

1. In `job.sh`:
   - `TOTAL_FILES`: Set to the exact number of sessions in your CSV file
   - `FILES_PER_JOB`: Adjust based on your total files and desired number of jobs
   - `--array=0-N`: Set N to `(TOTAL_FILES / FILES_PER_JOB) - 1`, rounded up

2. Memory and CPU requirements (if needed):
   - Adjust `--mem=8G` if your sessions need more memory
   - Adjust `--cpus-per-task=2` if you need more CPU cores

3. Job names:
   - Ensure the job names in both scripts reflect your parliament's name
   - In test_job.sh: `#SBATCH --job-name=[parliament-name]_download_test`
   - In job.sh: `#SBATCH --job-name=[parliament-name]_download`
   - These names help identify your jobs in the SLURM queue

### 7. Running the Jobs

1. Make the job scripts executable:
```bash
chmod +x job_scripts/test_job.sh
chmod +x job_scripts/job.sh
```

2. Always start with a test run:
```bash
sbatch job_scripts/test_job.sh
```

3. Check the test results:
   - Monitor the logs in `logs/test_job.log`
   - Verify files are downloading correctly
   - Check Supabase dashboard for proper tracking

4. If test is successful, run the full job:
```bash
sbatch job_scripts/job.sh
```

### 8. Monitoring and Maintenance

1. Monitor progress through:
   - Log files in the `logs/` directory
   - Supabase dashboard for download status
   - Check for failed downloads in Supabase

2. Common issues to watch for:
   - Memory limits exceeded
   - Network timeouts
   - Invalid URLs in CSV
   - Missing or incorrect file paths

3. Debugging:
   - Check individual job logs: `logs/job_[N].log`
   - Monitor Supabase error messages
   - Verify CSV file format and contents

### 9. Best Practices

1. Always maintain backups of your CSV files
2. Document any parliament-specific modifications
3. Test with a small batch before running full jobs
4. Monitor disk space usage
5. Keep track of failed downloads for later retry 