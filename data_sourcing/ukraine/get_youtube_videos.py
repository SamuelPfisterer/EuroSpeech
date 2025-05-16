from yt_dlp import YoutubeDL
import pandas as pd

def get_youtube_search_results(url):
    # Configure yt-dlp options
    ydl_opts = {
        'quiet': True,
        'extract_flat': True,
        'force_generic_extractor': False,
        'no_warnings': True
    }
    
    # Create yt-dlp object
    ydl = YoutubeDL(ydl_opts)
    
    # Create lists to store video information
    video_data = []
    
    try:
        # Extract information from the URL
        results = ydl.extract_info(url, download=False)
        
        # Collect video information
        if 'entries' in results:
            for entry in results['entries']:
                if entry is not None:
                    video_info = {
                        'title': entry.get('title', 'N/A'),
                        'video_id': entry.get('id', 'N/A'),
                        'url': f"https://www.youtube.com/watch?v={entry.get('id', '')}",
                        'upload_date': entry.get('upload_date', 'N/A'),
                        'duration': entry.get('duration', 'N/A')
                    }
                    video_data.append(video_info)
    
        # Create DataFrame from collected data
        df = pd.DataFrame(video_data)
        return df
    
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return pd.DataFrame()  # Return empty DataFrame if error occurs

# Use the function
search_url = "https://www.youtube.com/playlist?list=PL_7kofV6sT8NRjSqT25vA1xVoKNcvCPD9" 
results_df = get_youtube_search_results(search_url)
print(results_df)

# Save to CSV in a data folder
csv_filename = "ukraine_parliament_session_videos.csv"
results_df.to_csv(csv_filename, index=False, encoding='utf-8')
print(f"\nResults saved to {csv_filename}")
