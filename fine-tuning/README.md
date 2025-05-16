# Whisper Fine-Tuning Script

This script provides a modular way to fine-tune OpenAI Whisper models for Automatic Speech Recognition (ASR) tasks using Hugging Face Transformers, Datasets, and other supporting libraries. It is designed to be configurable via command-line arguments and has specific settings for dataset handling and training parameters. The script is suitable for execution on GPU-accelerated environments, including Slurm clusters.

## Features

- Fine-tune any Whisper model (e.g., `openai/whisper-small`, `openai/whisper-large-v3-turbo`).
- Support for custom datasets from the Hugging Face Hub, with specific defaults for Slovenian.
- Automatic use of the `google/fleurs` dataset for testing, based on the specified language.
- Filtering of the training dataset for samples with Character Error Rate (CER) < 0.1.
- Configurable random seed for reproducibility.
- Most training hyperparameters (epochs, batch size, learning rate, etc.) are pre-configured within the script for consistency.
- Evaluation using Word Error Rate (WER), with optional normalization.
- Logging with TensorBoard integration.
- Option to push the fine-tuned model to the Hugging Face Hub (enabled by default).

## Setup

1.  **Clone the repository (if applicable) or ensure you have the script and `requirements.txt` in your working directory.**

2.  **Create a Python virtual environment (recommended):**
    ```bash
    python -m venv whisper_env
    source whisper_env/bin/activate  # On Windows use `whisper_env\Scripts\activate`
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
    Ensure `whisper_normalizer` is installed if you require text normalization for WER calculation (the script attempts to use it).

4.  **Hugging Face Hub Login:**
    To push models to the Hugging Face Hub or use private models/datasets, you need to be logged in.
    *   **Using `huggingface-cli login`:**
        ```bash
        huggingface-cli login
        # Or pass your token directly (less secure for shared environments)
        # huggingface-cli login --token YOUR_HF_TOKEN
        ```
        The script will automatically use the cached token.
    *   **Passing the token via the `--hf_token` argument:**
        You can provide your Hugging Face token directly when running the script.
    *   **Setting the `HF_AUTH_TOKEN` environment variable:** The script will attempt to load this from a `.env` file or the environment.

## Running the Script

The script `fine_tune_whisper.py` is executed from the command line.

### Command-Line Arguments

Run `python fine_tune_whisper.py --help` to see all available arguments and their descriptions.

The primary arguments are:

*   `--model_name`: Name of the Whisper model to fine-tune from the Hugging Face Model Hub.
    (Default: `openai/whisper-large-v3-turbo`)
*   `--dataset_repo_name`: Name of the training dataset repository on Hugging Face Hub.
    (Default: `SamuelPfisterer1/slovenia`)
*   `--subset_name`: Name of the subset within the training dataset.
    (Default: `slovenia_3_percent`)
*   `--language`: Target language for transcription. Must be one of the languages defined in the script's `LANGUAGE_MAPPING`.
    (Default: `Slovenian`)
*   `--output_model_name`: Name for the fine-tuned model. If not provided, a name is generated based on the base model, language, and subset.
    (Default: None)
*   `--seed`: Random seed for reproducibility.
    (Default: 42)
*   `--push_to_hub`: If this flag is **included**, pushing to the Hugging Face Hub is **disabled**. By default (if the flag is omitted), results are pushed.
*   `--hf_token`: Your Hugging Face API token. Overrides tokens from env variables or CLI login if provided.

### Important Script Behavior & Fixed Parameters

*   **Training Data Preprocessing**:
    *   The script hardcodes the text column for training data as `"human_transcript"`.
    *   Training data is filtered to include only samples with a Character Error Rate (CER) less than 0.1 (i.e., `cer < 0.1`). This column must exist in your dataset.
*   **Test Data**:
    *   The script automatically uses the corresponding language subset from the `google/fleurs` dataset for evaluation. The text column for this data is hardcoded as `"transcription"`.
*   **Output Directory**: Model checkpoints and logs are saved to a directory structured as `./whisper-model/{output_model_name}`.
*   **Fixed Training Hyperparameters**: Many `Seq2SeqTrainingArguments` are fixed within the script:
    *   `per_device_train_batch_size`: 64
    *   `gradient_accumulation_steps`: 2
    *   `learning_rate`: 1e-5
    *   `warmup_ratio`: 0.06
    *   `lr_scheduler_type`: "linear"
    *   `num_train_epochs`: 3
    *   `gradient_checkpointing`: True
    *   `fp16`: Enabled if CUDA is available
    *   `eval_strategy`: "steps"
    *   `eval_steps`: 32
    *   `save_strategy`: "steps"
    *   `save_steps`: 32
    *   `per_device_eval_batch_size`: 64
    *   `predict_with_generate`: True
    *   `generation_max_length`: 225
    *   `logging_steps`: 10
    *   `report_to`: ["tensorboard"]
    *   `load_best_model_at_end`: True
    *   `metric_for_best_model`: "wer"
    *   `greater_is_better`: False
    *   `save_total_limit`: 3
    *   The `seed` for training arguments is taken from the `--seed` CLI argument.

### Example Usage

This example fine-tunes the default model (`openai/whisper-large-v3-turbo`) on the default Slovenian dataset, enabling push to hub with a specific output model name.

```bash
python fine_tune_whisper.py \
    --language "Slovenian" \
    --dataset_repo_name "SamuelPfisterer1/slovenia" \
    --subset_name "slovenia_3_percent" \
    --output_model_name "my-slovenian-whisper-v3-turbo" \
    --seed 123
    # To disable push_to_hub, add: --push_to_hub
    # To use a specific HF token, add: --hf_token "YOUR_TOKEN_HERE"
```

This example fine-tunes `openai/whisper-small` for Estonian, using a custom dataset and subset, and disables pushing to the hub:

```bash
python fine_tune_whisper.py \
    --model_name "openai/whisper-small" \
    --language "Estonian" \
    --dataset_repo_name "myusername/my_estonian_dataset" \
    --subset_name "main_subset" \
    --output_model_name "whisper-small-estonian-custom" \
    --push_to_hub \
    --seed 42
```

## Logging and Monitoring

- **Console Output:** The script will print progress, training loss, evaluation metrics (WER), and other information from the Hugging Face Trainer.
- **TensorBoard:** Logs are saved to the `runs` subdirectory within your output model directory (e.g., `./whisper-model/whisper-large-v3-turbo-slovenian-slovenia-3-percent/runs/...`). You can view them by running TensorBoard:
  ```bash
  tensorboard --logdir=./whisper-model/
  ```
  (Adjust the logdir path as needed to point to the specific run folder.)

## Slurm Cluster Execution

To run this script on a Slurm cluster, you would typically create a job script (e.g., `run_finetune.slurm`).

Example `run_finetune.slurm` (adapt to your cluster's configuration):

```slurm
#!/bin/bash
#SBATCH --job-name=whisper_ft
#SBATCH --output=whisper_ft_%j.out
#SBATCH --error=whisper_ft_%j.err
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --gres=gpu:1  # Request 1 GPU
#SBATCH --cpus-per-task=8 # Adjust based on num_proc in script and GPU
#SBATCH --mem=64G       # Adjust based on model size and batch size
#SBATCH --time=24:00:00 # Max runtime

# Load modules (example, adapt to your cluster)
module load python/3.10 cuda/11.8 cudnn

# Activate virtual environment
source /path/to/your/whisper_env/bin/activate

# Navigate to your script directory
cd /path/to/your/script_directory

# Run the fine-tuning script (example for Estonian)
python fine_tune_whisper.py \
    --model_name "openai/whisper-large-v3-turbo" \
    --language "Estonian" \
    --dataset_repo_name "SamuelPfisterer1/estonia" \
    --subset_name "estonia_0.08_cer_filtered" \
    --output_model_name "whisper-large-v3-turbo-estonian-custom" \
    --seed 42
    # Add --push_to_hub to disable pushing if needed
    # Add --hf_token "YOUR_TOKEN_HERE" if required

echo "Fine-tuning job finished."
```

Remember to adjust paths, module names, Slurm directives, and script arguments according to your specific dataset, language, and cluster's setup.
The `PROJECT_DIR` and `CONDA_ENVIRONMENT` variables in your provided job scripts should align with your environment setup for Slurm.
