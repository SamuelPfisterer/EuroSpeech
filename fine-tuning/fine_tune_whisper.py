import os
from typing import Optional
import logging

# --- Logging Setup (Initialize First) ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# For loading .env file
from dotenv import load_dotenv

# --- Environment Variable Setup ---
# Load environment variables from the specified .env file
# IMPORTANT: Make sure this .env file exists and is accessible
# You might want to make the path to the .env file an argument or handle its absence gracefully.
dotenv_path = "/itet-stor/spfisterer/net_scratch/Alignment/testing/own_pipeline/.env"
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)
    logger.info(f"Loaded environment variables from {dotenv_path}")
else:
    logger.warning(f".env file not found at {dotenv_path}. Proceeding without loading it.")

HF_CACHE_DIR: Optional[str] = os.getenv("HF_CACHE_DIR")
HF_AUTH_TOKEN: Optional[str] = os.getenv("HF_AUTH_TOKEN")

if HF_CACHE_DIR:
    logger.info(f"Using Hugging Face cache directory: {HF_CACHE_DIR}")
else:
    raise ValueError("HF_CACHE_DIR environment variable not set. Please set it in your .env file.")

if HF_AUTH_TOKEN:
    logger.info("HF_AUTH_TOKEN environment variable found.")
else:
    raise ValueError("HF_AUTH_TOKEN environment variable not set. Please set it in your .env file.")

# Add this near your environment variable setup
os.environ["HF_DATASETS_CACHE"] = HF_CACHE_DIR
os.environ["HF_HOME"] = HF_CACHE_DIR
os.environ["TMPDIR"] = HF_CACHE_DIR  # Controls where temp files are created
os.environ["HF_HUB_CACHE"] = HF_CACHE_DIR + "/hub_cache" 


import argparse
import torch
import gc
from datetime import datetime
from typing import Any, Dict, List, Union, Optional

# --- Logging Setup (Initialize First) ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# For loading .env file
from dotenv import load_dotenv

# Add GPU Monitoring imports
try:
    import psutil
    from pynvml import nvmlInit, nvmlDeviceGetHandleByIndex, nvmlDeviceGetMemoryInfo, nvmlDeviceGetUtilizationRates, NVMLError
    GPU_MONITORING_AVAILABLE = True
except ImportError:
    GPU_MONITORING_AVAILABLE = False

from datasets import load_dataset
from transformers import (
    WhisperFeatureExtractor,
    WhisperTokenizer,
    WhisperProcessor,
    WhisperForConditionalGeneration,
    Seq2SeqTrainingArguments,
    Seq2SeqTrainer,
    TrainerCallback,  # Add TrainerCallback for GPU monitoring
)
from huggingface_hub import notebook_login, HfFolder
import evaluate
# It seems whisper_normalizer is a pip installable package.
# We'll assume it's installed in the environment.
from whisper_normalizer.basic import BasicTextNormalizer
from dataclasses import dataclass



# --- Configuration ---
DEFAULT_MODEL_NAME = "openai/whisper-large-v3-turbo"
DEFAULT_DATASET_REPO_NAME = "SamuelPfisterer1/slovenia" # e.g., "slovenia"
DEFAULT_SUBSET_NAME = "slovenia_3_percent" # e.g., "slovenia_threepercentage"
DEFAULT_LANGUAGE = "Slovenian"
DEFAULT_OUTPUT_MODEL_NAME = None  # Will default to a name based on model_name if not provided
OUTPUT_DIR_PREFIX = "./whisper-model"  # More generic prefix

# Language configurations
LANGUAGE_MAPPING = {
    "Maltese": {"name": "Maltese", "fleurs_code": "mt_mt"},
    "Icelandic": {"name": "Icelandic", "fleurs_code": "is_is"},
    "Lithuanian": {"name": "Lithuanian", "fleurs_code": "lt_lt"},
    "Latvian": {"name": "Latvian", "fleurs_code": "lv_lv"},
    "Slovenian": {"name": "Slovenian", "fleurs_code": "sl_si"},
    "Serbian": {"name": "Serbian", "fleurs_code": "sr_rs"},
    "Estonian": {"name": "Estonian", "fleurs_code": "et_ee"},
    "Bosnian": {"name": "Bosnian", "fleurs_code": "bs_ba"}
}

FLEURS_DATASET_NAME = "google/fleurs"
# FLEURS_SUBSET_NAME is now determined dynamically based on language

# --- Data Preparation ---
def prepare_dataset_helper(batch, feature_extractor, tokenizer, text_column_name="human_transcript"):
    """Helper function to prepare a single batch of data."""
    audio = batch["audio"]
    # Compute log-Mel input features from input audio array
    batch["input_features"] = feature_extractor(audio["array"], sampling_rate=audio["sampling_rate"]).input_features[0]
    # Encode target text to label ids
    batch["labels"] = tokenizer(batch[text_column_name]).input_ids
    return batch

def load_and_prepare_data(dataset_repo_name: str, subset_name: str, feature_extractor, tokenizer, fleurs_subset: str, cache_dir: Optional[str] = None):
    """Loads and prepares the training, validation, and test datasets."""
    logger.info(f"Loading dataset: {dataset_repo_name}, subset: {subset_name}")
    logger.info(f"HF_CACHE_DIR: {HF_CACHE_DIR}")
    dataset = load_dataset(
        dataset_repo_name,
        subset_name,
        cache_dir=HF_CACHE_DIR,
        #download_mode="force_redownload"  # Ensures clean restart if previous failed
    )

    train_dataset = dataset["train"]
    # filter for 10% cer
    train_dataset = train_dataset.filter(lambda x: x["cer"] < 0.1)
    logger.info(f"Loading Fleurs dataset for testing (subset: {fleurs_subset})")
    fleurs_dataset = load_dataset(FLEURS_DATASET_NAME, fleurs_subset, cache_dir=cache_dir, trust_remote_code=True)
    test_dataset = fleurs_dataset["test"]

    logger.info("Tokenizing datasets...")
    train_tokenized = train_dataset.map(
        prepare_dataset_helper,
        fn_kwargs={"feature_extractor": feature_extractor, "tokenizer": tokenizer, "text_column_name": "human_transcript"},
        remove_columns=train_dataset.column_names,
        num_proc=16  # Can be increased based on available cores
    )

    test_tokenized = test_dataset.map(
        prepare_dataset_helper,
        fn_kwargs={"feature_extractor": feature_extractor, "tokenizer": tokenizer, "text_column_name": "transcription"},
        remove_columns=test_dataset.column_names,
        num_proc=16
    )
    logger.info("Dataset tokenization complete.")
    return train_tokenized, test_tokenized

# --- Data Collator ---
@dataclass
class DataCollatorSpeechSeq2SeqWithPadding:
    processor: Any
    decoder_start_token_id: int

    def __call__(self, features: List[Dict[str, Union[List[int], torch.Tensor]]]) -> Dict[str, torch.Tensor]:
        input_features = [{ "input_features": feature["input_features"] } for feature in features]
        batch = self.processor.feature_extractor.pad(input_features, return_tensors="pt")

        label_features = [{ "input_ids": feature["labels"] } for feature in features]
        labels_batch = self.processor.tokenizer.pad(label_features, return_tensors="pt")

        labels = labels_batch["input_ids"].masked_fill(labels_batch.attention_mask.ne(1), -100)

        if (labels[:, 0] == self.decoder_start_token_id).all().cpu().item():
            labels = labels[:, 1:]

        batch["labels"] = labels
        return batch


# --- Metrics Computation ---
def get_compute_metrics_fn(processor, normalizer_fn):
    """Returns the compute_metrics function for the Trainer."""
    metric = evaluate.load("wer")

    def compute_metrics(pred):
        pred_ids = pred.predictions
        label_ids = pred.label_ids

        label_ids[label_ids == -100] = processor.tokenizer.pad_token_id

        pred_str = processor.batch_decode(pred_ids, skip_special_tokens=True)
        label_str = processor.batch_decode(label_ids, skip_special_tokens=True)
        try:
            wer_ortho = 100 * metric.compute(predictions=pred_str, references=label_str)
        except Exception as e:
            logger.error(f"Error computing WER for pred_str: {pred_str} and ref_str: {label_str}: {e}")
            wer_ortho = 100

        pred_str_norm = [normalizer_fn(pred) for pred in pred_str]
        label_str_norm = [normalizer_fn(label) for label in label_str]

        pred_str_norm = [
            pred_str_norm[i] for i in range(len(pred_str_norm)) if len(label_str_norm[i]) > 0
        ]
        label_str_norm = [
            label_str_norm[i]
            for i in range(len(label_str_norm))
            if len(label_str_norm[i]) > 0
        ]
        try:
            wer = 100 * metric.compute(predictions=pred_str_norm, references=label_str_norm)
        except Exception as e:
            logger.error(f"Error computing WER for pred_str_norm: {pred_str_norm} and label_str_norm: {label_str_norm}: {e}")
            wer = 100
        logger.debug(f"WER Ortho: {wer_ortho}, WER Normalized: {wer}")
        return {"wer_ortho": wer_ortho, "wer": wer}

    return compute_metrics

# Add GPU monitoring functions
def init_gpu_monitoring():
    """Initialize GPU monitoring if available."""
    if not GPU_MONITORING_AVAILABLE:
        logger.warning("GPU monitoring not available. Install psutil and pynvml for GPU monitoring.")
        return False
    
    try:
        nvmlInit()
        logger.info("GPU monitoring initialized successfully.")
        return True
    except NVMLError as e:
        logger.warning(f"Failed to initialize GPU monitoring: {e}")
        return False

def log_gpu_stats():
    """Log GPU statistics if monitoring is available."""
    if not GPU_MONITORING_AVAILABLE:
        return
    
    try:
        # Get system memory info
        system_memory = psutil.virtual_memory()
        system_memory_used_gb = system_memory.used / (1024 ** 3)
        system_memory_total_gb = system_memory.total / (1024 ** 3)
        
        logger.info(f"System RAM: {system_memory_used_gb:.1f}GB / {system_memory_total_gb:.1f}GB ({system_memory.percent}%)")
        
        # Get GPU info for each GPU
        for i in range(torch.cuda.device_count()):
            handle = nvmlDeviceGetHandleByIndex(i)
            memory_info = nvmlDeviceGetMemoryInfo(handle)
            utilization = nvmlDeviceGetUtilizationRates(handle)
            
            gpu_memory_used_gb = memory_info.used / (1024 ** 3)
            gpu_memory_total_gb = memory_info.total / (1024 ** 3)
            gpu_percent = (memory_info.used / memory_info.total) * 100
            
            logger.info(f"GPU {i}: {gpu_memory_used_gb:.1f}GB / {gpu_memory_total_gb:.1f}GB ({gpu_percent:.1f}%), Utilization: {utilization.gpu}%")
            
            # Force garbage collection to get more accurate readings
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
    except Exception as e:
        logger.warning(f"Error getting GPU stats: {e}")

def get_default_output_model_name(model_name, language, subset_name):
    """Generate a default output model name based on input parameters."""
    # Extract model type (e.g., "large-v3-turbo" from "openai/whisper-large-v3-turbo")
    model_type = model_name.split('/')[-1]
    if model_type.startswith('whisper-'):
        model_type = model_type[8:]  # Remove 'whisper-' prefix
    
    # Create a name like "whisper-large-v3-turbo-slovenian-3percent"
    language_part = language.lower()
    subset_part = subset_name.replace('_', '-')
    
    return f"whisper-{model_type}-{language_part}-{subset_part}"

# --- Main Script ---
def main(model_name: str, dataset_repo_name: str, subset_name: str, language: str, push_to_hub: bool, output_model_name: Optional[str] = None):
    if language not in LANGUAGE_MAPPING:
        raise ValueError(f"Language '{language}' not supported. Supported languages: {', '.join(LANGUAGE_MAPPING.keys())}")
    
    # Generate default output model name if not provided
    if output_model_name is None:
        output_model_name = get_default_output_model_name(model_name, language, subset_name)
    
    logger.info(f"Starting fine-tuning process with model: {model_name}")
    logger.info(f"Dataset: {dataset_repo_name}, Subset: {subset_name}")
    logger.info(f"Language: {language}")
    logger.info(f"Output model name: {output_model_name}")

    # Initialize GPU monitoring
    gpu_monitoring = init_gpu_monitoring()
    if gpu_monitoring and torch.cuda.is_available():
        logger.info(f"Found {torch.cuda.device_count()} GPU(s)")
        for i in range(torch.cuda.device_count()):
            logger.info(f"GPU {i}: {torch.cuda.get_device_name(i)}")
        log_gpu_stats()  # Log initial GPU stats
    
    # Get FLEURS subset code for the selected language
    fleurs_subset = LANGUAGE_MAPPING[language]["fleurs_code"]
    logger.info(f"Using FLEURS subset code: {fleurs_subset}")

    logger.info("Initializing feature extractor, tokenizer, and processor...")
    feature_extractor = WhisperFeatureExtractor.from_pretrained(model_name, cache_dir=HF_CACHE_DIR)
    tokenizer = WhisperTokenizer.from_pretrained(model_name, language=language, task="transcribe", cache_dir=HF_CACHE_DIR)
    processor = WhisperProcessor.from_pretrained(model_name, language=language, task="transcribe", cache_dir=HF_CACHE_DIR)

    # Set pad token if not set or if it's the same as EOS token
    if processor.tokenizer.pad_token is None or \
       processor.tokenizer.pad_token_id == processor.tokenizer.eos_token_id:
        processor.tokenizer.pad_token = processor.tokenizer.eos_token
        logger.info(f"Pad token set to EOS token: {processor.tokenizer.pad_token} (ID: {processor.tokenizer.pad_token_id})")
    else:
        logger.info(f"Using existing pad token: {processor.tokenizer.pad_token} (ID: {processor.tokenizer.pad_token_id})")
    logger.info(f"EOS token ID: {processor.tokenizer.eos_token_id}")

    train_dataset, test_dataset_final = load_and_prepare_data(
        dataset_repo_name,
        subset_name,
        feature_extractor,
        tokenizer,
        fleurs_subset,
        cache_dir=HF_CACHE_DIR
    )

    # Initialize model
    logger.info(f"Loading pre-trained model: {model_name}")
    model = WhisperForConditionalGeneration.from_pretrained(model_name, cache_dir=HF_CACHE_DIR)
    model.generation_config.language = language.lower()  # Whisper expects lowercase language names
    model.generation_config.task = "transcribe"
    model.generation_config.forced_decoder_ids = None

    # Initialize Data Collator
    logger.info("Initializing data collator...")
    data_collator = DataCollatorSpeechSeq2SeqWithPadding(
        processor=processor,
        decoder_start_token_id=model.config.decoder_start_token_id,
    )

    # Initialize Metrics Computation
    logger.info("Initializing WER metric and normalizer...")
    # Note: The original script had !pip install whisper_normalizer
    # This script assumes whisper_normalizer is already installed in the environment.
    try:
        normalizer = BasicTextNormalizer()
    except Exception as e:
        logger.error("Failed to initialize BasicTextNormalizer. Make sure 'whisper_normalizer' is installed.")
        logger.error(f"Error: {e}")
        # Depending on the desired behavior, you might want to exit or continue without normalization.
        # For now, let's try to continue by setting normalizer to a lambda that does nothing.
        logger.warning("Proceeding without text normalization in metrics calculation.")
        normalizer = lambda x: x 
        
    compute_metrics_fn = get_compute_metrics_fn(processor, normalizer)

    # Set device
    device = "cuda" if torch.cuda.is_available() else "cpu"
    logger.info(f"Using device: {device}")
    # model.to(device) # Trainer handles model placement

    # --- Training Arguments ---
    output_dir_name = f"{OUTPUT_DIR_PREFIX}/{output_model_name}"
    logger.info(f"Output directory set to: {output_dir_name}")

    training_args = Seq2SeqTrainingArguments(
        output_dir=output_dir_name,
        per_device_train_batch_size=64, # As per original script
        gradient_accumulation_steps=2,  # As per original script
        learning_rate=1e-5,             # As per original script
        warmup_ratio=0.06,              # As per original script
        lr_scheduler_type="linear",     # As per original script
        num_train_epochs=3,             # As per original script
        gradient_checkpointing=True,    # As per original script
        fp16=torch.cuda.is_available(), # Enable FP16 only if CUDA is available
        eval_strategy="steps",       # Changed from eval_strategy to evaluation_strategy
        eval_steps=32,                  # As per original script, how often to evaluate
        save_strategy="steps",          # Changed from save_strategy to save_strategy
        save_steps=32,                 # As per original script, how often to save checkpoints
        per_device_eval_batch_size=64,  # As per original script
        predict_with_generate=True,     # As per original script
        generation_max_length=225,      # As per original script
        logging_steps=10,               # As per original script
        report_to=["tensorboard"],      # As per original script
        load_best_model_at_end=True,    # As per original script
        metric_for_best_model="wer",    # As per original script
        greater_is_better=False,        # As per original script
        push_to_hub=push_to_hub,        # Controlled by script argument
        save_total_limit=3,             # As per original script
        seed=args.seed,
        # The following were not in the original Colab but are good practice or often needed.
        # Adjust as necessary.
        # remove_unused_columns=False, # Important for custom data collators usually
        # label_names=["labels"], # If your model expects labels in a specific way
    )
    logger.info(f"Training arguments: {training_args.to_json_string()}")

    # --- Trainer Initialization ---
    logger.info("Initializing Trainer...")
    trainer = Seq2SeqTrainer(
        args=training_args,
        model=model,
        train_dataset=train_dataset,
        eval_dataset=test_dataset_final, # Using the validation set from your primary dataset for evaluation during training
        data_collator=data_collator,
        compute_metrics=compute_metrics_fn,
        tokenizer=processor.tokenizer, # Pass the tokenizer for processing generations
    )

    # Save processor before training
    logger.info(f"Saving processor to {training_args.output_dir}")
    processor.save_pretrained(training_args.output_dir)

    # --- Initial Evaluation (Optional but good practice) ---
    logger.info("Performing initial evaluation before training...")
    initial_results = trainer.evaluate(eval_dataset=test_dataset_final) # Evaluate on the Fleurs test set
    logger.info(f"Initial evaluation results (on Fleurs test set): {initial_results}")

    # --- Training ---
    logger.info("Starting training...")
    try:
        # Create a callback for monitoring GPU
        class GPUMonitoringCallback(TrainerCallback):
            def on_log(self, args, state, control, logs=None, **kwargs):
                if gpu_monitoring and state.global_step % 10 == 0:  # Log every 10 steps
                    logger.info(f"GPU Stats at step {state.global_step}:")
                    log_gpu_stats()
        
        # Create a callback for logging evaluation metrics
        class EvaluationLoggingCallback(TrainerCallback):
            def on_evaluate(self, args, state, control, metrics=None, **kwargs):
                if metrics:
                    metrics_str = ", ".join([f"{k}: {v:.4f}" for k, v in metrics.items()])
                    logger.info(f"Evaluation metrics at step {state.global_step}: {metrics_str}")

        if gpu_monitoring:
            trainer.add_callback(GPUMonitoringCallback())
            
        # Always add the evaluation logging callback
        trainer.add_callback(EvaluationLoggingCallback())

        trainer.train()
        logger.info("Training finished.")

        # Log final GPU stats
        if gpu_monitoring:
            logger.info("Final GPU stats:")
            log_gpu_stats()
    except Exception as e:
        logger.error(f"An error occurred during training: {e}", exc_info=True)
        # Potentially re-raise or handle more gracefully
        raise

    # --- Final Evaluation on Test Set ---
    logger.info(f"Performing final evaluation on the Fleurs test set: {FLEURS_DATASET_NAME}/{subset_name}")
    final_results = trainer.evaluate(eval_dataset=test_dataset_final)
    logger.info(f"Final evaluation results: {final_results}")

    # --- Save Model and Push to Hub (if applicable) ---
    if push_to_hub:
        logger.info("Pushing model and tokenizer to Hugging Face Hub...")
        try:
            trainer.push_to_hub(commit_message="End of training")
            logger.info("Model and tokenizer pushed to Hugging Face Hub successfully.")
        except Exception as e:
            logger.error(f"Error pushing to Hugging Face Hub: {e}", exc_info=True)
    else:
        logger.info("Skipping push to Hugging Face Hub as --push_to_hub was not set.")
        # Save model locally if not pushing to hub, trainer.save_model() can be used
        # The trainer already saves checkpoints according to save_strategy and load_best_model_at_end loads the best one.
        # If you want to save the final best model explicitly again, you can:
        # trainer.save_model(os.path.join(training_args.output_dir, "best_model"))
        # logger.info(f"Best model saved locally to {os.path.join(training_args.output_dir, 'best_model')}")


    logger.info(f"Training arguments used: {training_args.to_json_string()}")
    logger.info(f"Final model and results saved in: {training_args.output_dir}")
    pass

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fine-tune a Whisper model.")
    parser.add_argument(
        "--model_name",
        type=str,
        default=DEFAULT_MODEL_NAME,
        help="Name of the Whisper model to fine-tune (from Hugging Face Model Hub)."
    )
    parser.add_argument(
        "--dataset_repo_name",
        type=str,
        default=DEFAULT_DATASET_REPO_NAME,
        help="Name of the dataset repository (e.g., 'username/dataset_name')."
    )
    parser.add_argument(
        "--subset_name",
        type=str,
        default=DEFAULT_SUBSET_NAME,
        help="Name of the subset within the dataset (e.g., 'subset_name')."
    )
    parser.add_argument(
        "--language",
        type=str,
        default=DEFAULT_LANGUAGE,
        choices=list(LANGUAGE_MAPPING.keys()),
        help=f"Language to fine-tune for. Available options: {', '.join(LANGUAGE_MAPPING.keys())}"
    )
    parser.add_argument(
        "--push_to_hub",
        action="store_false",  # Note: Changed to store_false, so default is True
        help="Disable pushing to Hugging Face Hub (enabled by default)."
    )
    parser.add_argument(
        "--hf_token",
        type=str,
        default=HF_AUTH_TOKEN, # Default to environment variable
        help="Hugging Face API token. If not provided, uses HF_AUTH_TOKEN env var, then tries to log in interactively or use cached token."
    )
    parser.add_argument(
        "--output_model_name",
        type=str,
        default=DEFAULT_OUTPUT_MODEL_NAME,
        help="Name to use for the fine-tuned model. If not provided, a name will be generated based on model and language."
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducibility."
    )

    args = parser.parse_args()

    # Use the token from args if provided, otherwise it defaults to HF_AUTH_TOKEN (which could be None)
    token_to_use = args.hf_token 

    if args.push_to_hub:
        if token_to_use:
            HfFolder.save_token(token_to_use)
            logger.info("Hugging Face token saved from argument/environment variable.")
        else:
            logger.info("Attempting Hugging Face login for pushing to hub (no token provided via arg/env)...")
            notebook_login() # This will prompt for login if no token is found

    main(
        model_name=args.model_name,
        dataset_repo_name=args.dataset_repo_name,
        subset_name=args.subset_name,
        language=args.language,
        push_to_hub=args.push_to_hub,
        output_model_name=args.output_model_name
    )
    logger.info("Fine-tuning script finished.") 