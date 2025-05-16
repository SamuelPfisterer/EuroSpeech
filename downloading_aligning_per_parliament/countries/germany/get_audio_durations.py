import os
import pandas as pd
from pydub import AudioSegment
import ffmpeg
from tqdm import tqdm


# Define the directories containing the .opus files
audio_dirs = ["downloaded_audio", "downloaded_audio/mp4_converted"]

# Initialize a list to store file information
file_info = []

# using ffmpeg
def get_duration_ffmpeg(file_path):
    try: 
        result = ffmpeg.probe(file_path)
        return float(result['streams'][0]['duration'])
    except Exception as e:
        print(f"Error getting duration for {file_path}: {e}")
        return None

# using pydub
def get_duration_pydub(file_path):
    audio = AudioSegment.from_file(file_path, format="ogg")
    return audio.duration_seconds

# Get all .opus files from all directories first
all_opus_files = []
for audio_dir in audio_dirs:
    for filename in os.listdir(audio_dir):
        if filename.endswith(".opus"):
            all_opus_files.append((audio_dir, filename))

# Process all files with progress bar
for audio_dir, filename in tqdm(all_opus_files, desc="Processing audio files"):
    file_path = os.path.join(audio_dir, filename)
    
    print(f"\nProcessing {file_path}")
    # Get the duration in seconds
    duration_seconds = get_duration_ffmpeg(file_path)
    
    # Append the file information to the list
    if duration_seconds is not None:
        print(f"Duration: {duration_seconds}")
        file_info.append({
            "filename": filename,
            "directory": audio_dir,  # Added directory info
            "duration_seconds": duration_seconds
        })

# Convert the list to a DataFrame
df = pd.DataFrame(file_info)

# Ensure duration_seconds is numeric
df['duration_seconds'] = pd.to_numeric(df['duration_seconds'])

# Sort the DataFrame by duration_seconds in ascending order
df = df.sort_values(by="duration_seconds")

# Save the DataFrame to a CSV file
output_csv = "audio_durations.csv"
df.to_csv(output_csv, index=False)

print(f"CSV file saved to {output_csv}")

# print the total number of files
print(f"Total number of files: {len(df)}")
#print the total duration of the files
print(f"Total duration of the files: {df['duration_seconds'].sum()}")

# print the average duration of the files
print(f"Average duration of the files: {df['duration_seconds'].mean()}")

