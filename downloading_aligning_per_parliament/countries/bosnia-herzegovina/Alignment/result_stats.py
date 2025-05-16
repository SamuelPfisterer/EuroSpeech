import glob
import os
import json
import numpy as np
import matplotlib.pyplot as plt
from typing import List, Tuple, Dict
from tqdm import tqdm
from parliament_transcript_aligner.utils.io import load_alignments
import subprocess
from collections import defaultdict

class SimpleSegment:
    def __init__(self, start: float, end: float):
        self.start = start
        self.end = end
        
    def duration(self):
        return self.end - self.start

class SimpleTranscribedSegment:
    def __init__(self, segment: SimpleSegment, text: str):
        self.segment = segment
        self.text = text

class SimpleAlignedTranscript:
    def __init__(self, asr_segment: SimpleTranscribedSegment, human_text: str, 
                 start_idx: int, end_idx: int, cer: float):
        self.asr_segment = asr_segment
        self.human_text = human_text
        self.start_idx = start_idx
        self.end_idx = end_idx
        self.cer = cer

def get_audio_duration(audio_path: str) -> float:
    """Get the duration of an audio file using ffprobe.
    
    Args:
        audio_path: Path to audio file
        
    Returns:
        Duration in seconds, or 0 if there was an error
    """
    try:
        result = subprocess.run(
            [
                'ffprobe', 
                '-v', 'error', 
                '-show_entries', 'format=duration', 
                '-of', 'default=noprint_wrappers=1:nokey=1', 
                audio_path
            ], 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            text=True
        )
        return float(result.stdout.strip())
    except Exception as e:
        print(f"Error getting duration of {audio_path}: {str(e)}")
        return 0.0

def load_aligned_transcripts(json_path: str) -> Tuple[str, List[SimpleAlignedTranscript], float]:
    """Load aligned segments from JSON file and convert them to SimpleAlignedTranscript objects.
    
    Args:
        json_path: Path to JSON file
        
    Returns:
        Tuple of (audio_path, list of SimpleAlignedTranscript objects, audio_duration)
    """
    try:
        # Use the library's load_alignments function
        audio_path, segment_dicts = load_alignments(json_path)
    except Exception as e:
        # Fallback to our custom implementation if the library function fails
        print(f"Error using library load_alignments for {json_path}: {str(e)}")
        try:
            with open(json_path, 'r') as f:
                data = json.load(f)
            
            # Based on the observed data structure, we should look for 'audio_file' rather than 'audio_path'
            if "audio_file" in data:
                audio_path = data["audio_file"]
            elif "audio_path" in data:
                audio_path = data["audio_path"]
            else:
                audio_path = os.path.splitext(os.path.basename(json_path))[0].replace("_aligned", "")
                print(f"No audio path found in {json_path}, using {audio_path}")
            
            segment_dicts = data.get("segments", [])
        except Exception as inner_e:
            print(f"Error in fallback load for {json_path}: {str(inner_e)}")
            return "", [], 0.0
    
    # Get audio duration if the audio file exists
    audio_duration = 0.0
    if os.path.exists(audio_path):
        audio_duration = get_audio_duration(audio_path)
    else:
        print(f"Audio file not found: {audio_path}")
    
    aligned_transcripts = []
    for segment_dict in segment_dicts:
        try:
            # Create a SimpleTranscribedSegment from the ASR segment data
            asr_segment = SimpleTranscribedSegment(
                segment=SimpleSegment(segment_dict["start"], segment_dict["end"]),
                text=segment_dict["asr_text"]
            )
            
            # Create a SimpleAlignedTranscript using the SimpleTranscribedSegment and other data
            aligned_transcript = SimpleAlignedTranscript(
                asr_segment=asr_segment,
                human_text=segment_dict["human_text"],
                start_idx=segment_dict["start_idx"],
                end_idx=segment_dict["end_idx"],
                cer=segment_dict["cer"]
            )
            
            aligned_transcripts.append(aligned_transcript)
        except KeyError as ke:
            # Handle missing keys more gracefully
            print(f"Skipping segment in {json_path} due to missing key: {ke}")
        except Exception as e:
            print(f"Error processing segment in {json_path}: {str(e)}")
    
    return audio_path, aligned_transcripts, audio_duration

def calculate_cer_statistics(aligned_transcripts: List[SimpleAlignedTranscript]) -> dict:
    """Calculate CER statistics from a list of SimpleAlignedTranscript objects.
    
    Args:
        aligned_transcripts: List of SimpleAlignedTranscript objects
        
    Returns:
        Dictionary containing CER statistics
    """
    cer_values = [transcript.cer for transcript in aligned_transcripts]
    segment_durations = [transcript.asr_segment.segment.duration() 
                         for transcript in aligned_transcripts]
    
    # Total duration of all aligned segments
    total_duration = sum(segment_durations)
    
    # CER distribution
    cer_distribution = {}
    for cer in cer_values:
        cer_rounded = round(cer, 2)  # Round to 2 decimal places for better grouping
        cer_distribution[cer_rounded] = cer_distribution.get(cer_rounded, 0) + 1
    
    # Sort the CER distribution for better visualization
    cer_distribution = {k: cer_distribution[k] for k in sorted(cer_distribution.keys())} if cer_distribution else {}
    
    # Total duration of segments below certain CER thresholds
    thresholds = [0.1, 0.2, 0.3, 0.5, 0.7]  # Example thresholds
    duration_below_thresholds = {threshold: 0.0 for threshold in thresholds}
    for transcript, duration in zip(aligned_transcripts, segment_durations):
        for threshold in thresholds:
            if transcript.cer <= threshold:
                duration_below_thresholds[threshold] += duration
    
    return {
        "total_duration": total_duration,
        "cer_distribution": cer_distribution,
        "duration_below_thresholds": duration_below_thresholds,
        "total_segments": len(aligned_transcripts),
        "average_cer": sum(cer_values) / len(cer_values) if cer_values else 0
    }

def save_results_to_file(results: dict, output_dir: str):
    """Save results to a JSON and TXT file.
    
    Args:
        results: Dictionary containing CER statistics
        output_dir: Directory to save the output files
    """
    # Convert any non-serializable values to strings for JSON
    results_for_json = {}
    for k, v in results.items():
        if isinstance(v, dict):
            results_for_json[k] = {str(sk): sv for sk, sv in v.items()}
        else:
            results_for_json[k] = v
    
    # Save to JSON
    json_path = os.path.join(output_dir, "alignment_statistics.json")
    with open(json_path, "w") as json_file:
        json.dump(results_for_json, json_file, indent=4)
    
    # Save to TXT
    txt_path = os.path.join(output_dir, "alignment_statistics.txt")
    with open(txt_path, "w") as txt_file:
        # CER statistics
        txt_file.write("=== CER STATISTICS ===\n")
        txt_file.write(f"Total Duration of Aligned Segments: {results['cer_stats']['total_duration']:.2f} seconds\n")
        txt_file.write(f"Total Number of Segments: {results['cer_stats']['total_segments']}\n")
        txt_file.write(f"Average CER: {results['cer_stats']['average_cer']:.4f}\n\n")
        
        txt_file.write("Duration Below CER Thresholds:\n")
        for threshold, duration in results['cer_stats']['duration_below_thresholds'].items():
            percent = (duration / results['cer_stats']['total_duration']) * 100 if results['cer_stats']['total_duration'] > 0 else 0
            txt_file.write(f"  CER <= {threshold}: {duration:.2f} seconds ({percent:.2f}%)\n")
        
        # Audio coverage statistics
        txt_file.write("\n=== AUDIO COVERAGE STATISTICS ===\n")
        txt_file.write(f"Total number of aligned audio files: {results['total_aligned_files']}\n")
        txt_file.write(f"Total duration of aligned audio files: {results['total_audio_duration']:.2f} seconds ({results['total_audio_duration']/3600:.2f} hours)\n")
        txt_file.write(f"Total duration of all aligned segments: {results['cer_stats']['total_duration']:.2f} seconds ({results['cer_stats']['total_duration']/3600:.2f} hours)\n")
        txt_file.write(f"Average coverage ratio: {results['average_coverage_ratio']:.2f}\n")
        
        # All audio files statistics
        txt_file.write("\n=== ALL AUDIO FILES STATISTICS ===\n")
        txt_file.write(f"Total number of audio files in directory: {results['total_audio_files']}\n")
        txt_file.write(f"Total duration of all audio files: {results['total_all_audio_duration']:.2f} seconds ({results['total_all_audio_duration']/3600:.2f} hours)\n")
        txt_file.write(f"Number of unaligned audio files: {results['unaligned_audio_files']}\n")
        txt_file.write(f"Duration of unaligned audio files: {results['unaligned_audio_duration']:.2f} seconds ({results['unaligned_audio_duration']/3600:.2f} hours)\n")
        
        # Percentage of audio that has been aligned
        alignment_coverage = (results['total_audio_duration'] / results['total_all_audio_duration']) * 100 if results['total_all_audio_duration'] > 0 else 0
        txt_file.write(f"\nPercentage of audio that has been aligned: {alignment_coverage:.2f}%\n")

def plot_cer_distribution(cer_distribution: dict, output_dir: str):
    """Plot the CER distribution and save the plot.
    
    Args:
        cer_distribution: Dictionary containing CER distribution
        output_dir: Directory to save the plot
    """
    if not cer_distribution:
        print("No CER distribution data available for plotting")
        return
    
    plt.figure(figsize=(12, 7))
    
    # Convert dict to lists for plotting
    x_values = np.array(list(cer_distribution.keys()), dtype=float)
    y_values = list(cer_distribution.values())
    
    plt.bar(x_values, y_values, color='blue', width=0.01)
    plt.xlabel("Character Error Rate (CER)")
    plt.ylabel("Number of Segments")
    plt.title("CER Distribution")
    plt.grid(True, alpha=0.3)
    
    # Add x-axis ticks at 0.1 intervals
    max_x = max(x_values) if len(x_values) > 0 else 1.0
    plt.xticks(np.arange(0, max_x + 0.1, 0.1))
    
    plot_path = os.path.join(output_dir, "cer_distribution.png")
    plt.savefig(plot_path, dpi=300)
    plt.close()

def plot_duration_thresholds(duration_below_thresholds: dict, total_duration: float, output_dir: str):
    """Plot the duration below CER thresholds and save the plot.
    
    Args:
        duration_below_thresholds: Dictionary containing duration below thresholds
        total_duration: Total duration of all segments
        output_dir: Directory to save the plot
    """
    if total_duration == 0:
        print("No duration data available for plotting thresholds")
        return
        
    plt.figure(figsize=(10, 6))
    
    thresholds = list(duration_below_thresholds.keys())
    durations = list(duration_below_thresholds.values())
    percentages = [(duration / total_duration) * 100 for duration in durations]
    
    plt.bar(thresholds, percentages, color='green')
    plt.xlabel("CER Threshold")
    plt.ylabel("Percentage of Total Duration (%)")
    plt.title("Percentage of Audio Duration Below CER Thresholds")
    plt.grid(True, alpha=0.3)
    plt.ylim(0, 100)
    
    # Add percentage labels on top of bars
    for i, percentage in enumerate(percentages):
        plt.text(thresholds[i], percentage + 1, f"{percentage:.1f}%", ha='center')
    
    plot_path = os.path.join(output_dir, "duration_thresholds.png")
    plt.savefig(plot_path, dpi=300)
    plt.close()

def plot_coverage_ratio_distribution(coverage_ratios: List[float], output_dir: str):
    """Plot the distribution of coverage ratios and save the plot.
    
    Args:
        coverage_ratios: List of coverage ratios
        output_dir: Directory to save the plot
    """
    if not coverage_ratios:
        print("No coverage ratio data available for plotting")
        return
    
    plt.figure(figsize=(12, 7))
    
    # Create histogram
    plt.hist(coverage_ratios, bins=20, color='purple', alpha=0.7)
    plt.xlabel("Coverage Ratio (Aligned Duration / Total Audio Duration)")
    plt.ylabel("Number of Audio Files")
    plt.title("Distribution of Audio Coverage Ratios")
    plt.grid(True, alpha=0.3)
    mean_value = float(np.mean(coverage_ratios))
    median_value = float(np.median(coverage_ratios))
    plt.axvline(x=mean_value, color='red', linestyle='--', label=f'Mean: {mean_value:.2f}')
    plt.axvline(x=median_value, color='green', linestyle='--', label=f'Median: {median_value:.2f}')
    plt.legend()
    
    plot_path = os.path.join(output_dir, "coverage_ratio_distribution.png")
    plt.savefig(plot_path, dpi=300)
    plt.close()

def main():
    alignment_dir = "/itet-stor/spfisterer/net_scratch/Downloading/countries/bosnia-herzegovina/Alignment/alignment_output"
    audio_dir = "/itet-stor/spfisterer/net_scratch/Downloading/countries/bosnia-herzegovina/downloaded_audio/mp4_converted"
    output_dir = "/itet-stor/spfisterer/net_scratch/Downloading/countries/bosnia-herzegovina/Alignment/statistics_output"
    os.makedirs(output_dir, exist_ok=True)
    
    alignment_files = glob.glob(os.path.join(alignment_dir, "*_aligned.json"))
    print(f"Found {len(alignment_files)} alignment files.")
    
    # Find all audio files
    audio_files = []
    for ext in ['*.opus']:
        audio_files.extend(glob.glob(os.path.join(audio_dir, ext)))
    print(f"Found {len(audio_files)} audio files in the directory.")
    
    all_aligned_transcripts = []
    aligned_audio_paths = set()
    audio_durations = {}
    coverage_ratios = []
    
    # Process alignment files
    print("Processing alignment files...")
    for json_file in tqdm(alignment_files, desc="Processing alignment files"):
        try:
            audio_path, aligned_transcripts, audio_duration = load_aligned_transcripts(json_file)
            
            if aligned_transcripts:
                all_aligned_transcripts.extend(aligned_transcripts)
                aligned_audio_paths.add(audio_path)
                
                # Calculate total duration of the aligned segments for this file
                segments_duration = sum(t.asr_segment.segment.duration() for t in aligned_transcripts)
                
                # Store audio duration
                audio_durations[audio_path] = audio_duration
                
                # Calculate coverage ratio (segments duration / audio duration)
                if audio_duration > 0:
                    coverage_ratio = segments_duration / audio_duration
                    coverage_ratios.append(coverage_ratio)
                    print(f"File: {os.path.basename(audio_path)}, Segments Duration: {segments_duration:.2f}s, "
                          f"Audio Duration: {audio_duration:.2f}s, Coverage: {coverage_ratio:.2f}")
        except Exception as e:
            print(f"Error processing {json_file}: {str(e)}")
    
    print(f"\nSuccessfully processed {len(aligned_audio_paths)} unique audio files with "
          f"{len(all_aligned_transcripts)} total segments.")
    
    if not all_aligned_transcripts:
        print("No aligned transcripts found. Exiting.")
        return
    
    # Calculate CER statistics
    cer_stats = calculate_cer_statistics(all_aligned_transcripts)
    
    # Calculate audio file statistics
    total_audio_duration = sum(audio_durations.values())
    average_coverage_ratio = np.mean(coverage_ratios) if coverage_ratios else 0
    
    # Get durations of all audio files
    all_audio_durations = {}
    for audio_file in tqdm(audio_files, desc="Getting durations of all audio files"):
        duration = get_audio_duration(audio_file)
        all_audio_durations[audio_file] = duration
    
    total_all_audio_duration = sum(all_audio_durations.values())
    
    # Find unaligned audio files
    unaligned_audio_paths = set(all_audio_durations.keys()) - aligned_audio_paths
    unaligned_audio_duration = sum(all_audio_durations.get(path, 0) for path in unaligned_audio_paths)
    
    # Prepare results
    results = {
        "cer_stats": cer_stats,
        "total_aligned_files": len(aligned_audio_paths),
        "total_audio_duration": total_audio_duration,
        "average_coverage_ratio": average_coverage_ratio,
        "total_audio_files": len(audio_files),
        "total_all_audio_duration": total_all_audio_duration,
        "unaligned_audio_files": len(unaligned_audio_paths),
        "unaligned_audio_duration": unaligned_audio_duration,
    }
    
    # Save results to files
    save_results_to_file(results, output_dir)
    
    # Plot CER distribution
    plot_cer_distribution(cer_stats["cer_distribution"], output_dir)
    
    # Plot duration below thresholds
    plot_duration_thresholds(cer_stats["duration_below_thresholds"], cer_stats["total_duration"], output_dir)
    
    # Plot coverage ratio distribution
    plot_coverage_ratio_distribution(coverage_ratios, output_dir)
    
    # Print results
    print("Results saved to:", output_dir)

if __name__ == "__main__":
    main()