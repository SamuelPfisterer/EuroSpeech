import pandas as pd

# Read the CSV file
df = pd.read_csv('ukraine_parliament_videos_with_dates.csv')

# Count videos per date
videos_per_date = df['date'].value_counts()

# Count dates with exactly one video
single_video_dates = len(videos_per_date[videos_per_date == 1])
total_dates = len(videos_per_date)

print(f'\nDates with exactly one video: {single_video_dates} out of {total_dates} unique dates')
print(f'Percentage: {(single_video_dates/total_dates)*100:.1f}%\n')

# Show distribution of videos per date
print('Distribution of videos per date:')
distribution = videos_per_date.value_counts().sort_index()
for num_videos, count in distribution.items():
    print(f'{num_videos} video(s): {count} dates') 