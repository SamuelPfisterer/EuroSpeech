import pandas as pd

# Read the CSV file
df = pd.read_csv('ukraine_parliament_videos_with_dates.csv')

# Get dates that have exactly 2 videos
videos_per_date = df['date'].value_counts()
dates_with_two = videos_per_date[videos_per_date == 2].index

print(f"\nAnalyzing {len(dates_with_two)} dates that have exactly 2 videos:\n")

# Keywords to look for
morning_keywords = ['Ранкове', 'ранкове']
evening_keywords = ['Вечірнє', 'вечірнє']
part_keywords = ['ч.1', 'ч.2', 'част.1', 'част.2', 'частина 1', 'частина 2', '/част. 1', '/част. 2']

# Analyze patterns in pairs
patterns = {
    'morning_evening': 0,
    'part1_part2': 0,
    'other': 0
}

# Store examples of each pattern
examples = {
    'morning_evening': [],
    'part1_part2': [],
    'other': []
}

for date in dates_with_two:
    pair = df[df['date'] == date].sort_values('title')
    titles = pair['title'].tolist()
    
    # Check if it's morning/evening pattern
    if any(k in titles[0] for k in morning_keywords) and any(k in titles[1] for k in evening_keywords):
        patterns['morning_evening'] += 1
        if len(examples['morning_evening']) < 3:
            examples['morning_evening'].append((date, titles))
    # Check if it's part1/part2 pattern
    elif any(k in titles[0] for k in part_keywords) and any(k in titles[1] for k in part_keywords):
        patterns['part1_part2'] += 1
        if len(examples['part1_part2']) < 3:
            examples['part1_part2'].append((date, titles))
    else:
        patterns['other'] += 1
        if len(examples['other']) < 3:
            examples['other'].append((date, titles))

# Print results
print("Distribution of patterns:")
for pattern, count in patterns.items():
    print(f"\n{pattern}: {count} pairs ({count/len(dates_with_two)*100:.1f}%)")
    if count > 0:
        print("\nExample pairs:")
        for date, titles in examples[pattern][:3]:
            print(f"\nDate: {date}")
            print(f"  1: {titles[0]}")
            print(f"  2: {titles[1]}") 