import os
import pandas as pd
from pydub import AudioSegment
import pyogg
import numpy
import opuspy
import ffmpeg


# Define the directory containing the .opus files
audio_dir = "downloaded_audio/processed_video"

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

# using opuspy
def get_duration_opuspy(file_path):
    waveform, sample_rate = opuspy.read(file_path)
    return len(waveform) / sample_rate

# using pyogg
def get_duration_pyogg(file_path):
    opus_file = pyogg.OpusFile(file_path)
    print(f"Opus file: {opus_file}")
    pcm = opus_file.as_array()
    print(f"PCM: {pcm}")
    return pcm.shape[0] / opus_file.frequency

# using pydub
def get_duration_pydub(file_path):
    audio = AudioSegment.from_file(file_path, format="ogg")
    return audio.duration_seconds

# Iterate over all .opus files in the directory
for filename in os.listdir(audio_dir):
    if filename.endswith(".opus"):
        file_path = os.path.join(audio_dir, filename)
        
        print(f"Processing {file_path}")
        # Get the duration in seconds
        duration_seconds = get_duration_ffmpeg(file_path)
        
        # Append the file information to the list
        if duration_seconds is not None:
            print(f"Duration: {duration_seconds}")
            file_info.append({
                "filename": filename,
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