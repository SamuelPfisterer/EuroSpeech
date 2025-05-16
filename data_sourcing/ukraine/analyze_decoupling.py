import pandas as pd

def parse_video_type(title):
    # Session type
    if 'Година запитань до Уряду' in title:
        session_type = 'qa_session'
    elif 'Пленарне засідання' in title:
        session_type = 'plenary_session'
    else:
        session_type = 'other'
    
    # Time of day
    if any(k in title for k in ['Ранкове', 'ранкове']):
        time_of_day = 'morning'
    elif any(k in title for k in ['Вечірнє', 'вечірнє']):
        time_of_day = 'evening'
    else:
        time_of_day = None
    
    # Part number
    part_patterns = {
        'ч.1': 1, 'част.1': 1, 'частина 1': 1, '/част. 1': 1,
        'ч.2': 2, 'част.2': 2, 'частина 2': 2, '/част. 2': 2
    }
    part_number = None
    for pattern, number in part_patterns.items():
        if pattern in title:
            part_number = number
            break
    
    return {
        'session_type': session_type,
        'time_of_day': time_of_day,
        'part_number': part_number
    }

# Read the CSV file
df = pd.read_csv('ukraine_parliament_videos_with_dates.csv')

# Get dates that have exactly 2 videos
videos_per_date = df['date'].value_counts()
dates_with_two = videos_per_date[videos_per_date == 2].index

print(f"\nAnalyzing {len(dates_with_two)} dates that have exactly 2 videos:\n")

# Statistics for decoupling success
stats = {
    'total_pairs': len(dates_with_two),
    'successfully_decoupled': 0,
    'decoupling_method': {
        'session_type': 0,
        'time_of_day': 0,
        'part_number': 0,
        'multiple_methods': 0,
        'failed': 0
    }
}

# Analyze each pair
for date in dates_with_two:
    pair = df[df['date'] == date].sort_values('title')
    titles = pair['title'].tolist()
    
    # Parse both videos
    video1 = parse_video_type(titles[0])
    video2 = parse_video_type(titles[1])
    
    # Count which methods helped decouple
    methods_helped = 0
    
    # Check if they can be decoupled by session type
    if video1['session_type'] != video2['session_type'] and video1['session_type'] != 'other' and video2['session_type'] != 'other':
        stats['decoupling_method']['session_type'] += 1
        methods_helped += 1
    
    # Check if they can be decoupled by time of day
    if video1['time_of_day'] and video2['time_of_day'] and video1['time_of_day'] != video2['time_of_day']:
        stats['decoupling_method']['time_of_day'] += 1
        methods_helped += 1
    
    # Check if they can be decoupled by part number
    if video1['part_number'] and video2['part_number'] and video1['part_number'] != video2['part_number']:
        stats['decoupling_method']['part_number'] += 1
        methods_helped += 1
    
    # Update statistics
    if methods_helped > 0:
        stats['successfully_decoupled'] += 1
        if methods_helped > 1:
            stats['decoupling_method']['multiple_methods'] += 1
    else:
        stats['decoupling_method']['failed'] += 1
        print(f"\nFailed to decouple date {date}:")
        print(f"  1: {titles[0]}")
        print(f"  2: {titles[1]}")

# Print results
print("\nDecoupling Statistics:")
print(f"Total pairs analyzed: {stats['total_pairs']}")
print(f"Successfully decoupled: {stats['successfully_decoupled']} ({stats['successfully_decoupled']/stats['total_pairs']*100:.1f}%)")
print("\nDecoupling methods used:")
for method, count in stats['decoupling_method'].items():
    print(f"- {method}: {count} pairs ({count/stats['total_pairs']*100:.1f}%)") 