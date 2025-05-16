import pandas as pd
import re

def parse_video_type(title):
    # Session type
    if 'Година запитань до Уряду' in title.lower() or 'година запитань до уряду' in title.lower():
        session_type = 'qa_session'
    elif 'Позачергове' in title or 'позачергове' in title:
        session_type = 'emergency_session'
    elif 'Пленарне засідання' in title or 'пленарне засідання' in title:
        session_type = 'plenary_session'
    elif 'Виступ' in title or 'виступ' in title:
        session_type = 'special_speech'
    elif 'Урочисте засідання' in title:
        session_type = 'ceremonial_session'
    else:
        session_type = 'other'
    
    # Time of day
    if any(k in title for k in ['Ранкове', 'ранкове']):
        time_of_day = 'morning'
    elif any(k in title for k in ['Вечірнє', 'вечірнє']):
        time_of_day = 'evening'
    else:
        time_of_day = None
    
    # Part number from various formats
    part_number = None
    # Standard format (ч.1, част.1, etc)
    part_patterns = {
        'ч.1': 1, 'част.1': 1, 'частина 1': 1, '/част. 1': 1, 'Частина 1': 1, 'Ч.1': 1,
        'ч.2': 2, 'част.2': 2, 'частина 2': 2, '/част. 2': 2, 'Частина 2': 2, 'Ч.2': 2,
        'ч.3': 3, 'част.3': 3, 'частина 3': 3, '/част. 3': 3, 'Частина 3': 3, 'Ч.3': 3,
        'ч.4': 4, 'част.4': 4, 'частина 4': 4, '/част. 4': 4, 'Частина 4': 4, 'Ч.4': 4
    }
    for pattern, number in part_patterns.items():
        if pattern in title:
            part_number = number
            break
    
    # Roman numeral format (І-ше, ІІ-ге, etc)
    if part_number is None:
        roman_match = re.search(r'(І{1,3})-[шг][еи]', title)
        if roman_match:
            roman = roman_match.group(1)
            part_number = len(roman)
    
    # Multi-day session detection
    multi_day_match = re.search(r'(\d{2})-(\d{2})\.(\d{2})\.', title)
    multi_day = bool(multi_day_match)
    
    return {
        'session_type': session_type,
        'time_of_day': time_of_day,
        'part_number': part_number,
        'multi_day': multi_day
    }

def generate_unique_id(row, df):
    """Generate a unique ID combining date and video attributes"""
    # Start with the date
    unique_id = row['date'].replace('-', '')
    
    # Add session type abbreviation
    session_type_map = {
        'plenary_session': 'PL',
        'qa_session': 'QA',
        'emergency_session': 'EM',
        'special_speech': 'SP',
        'ceremonial_session': 'CE',
        'other': 'OT'
    }
    session_type_code = session_type_map.get(row['session_type'], 'OT')
    
    # Count how many sessions of this type exist on this date
    same_day_sessions = df[
        (df['date'] == row['date']) & 
        (df['session_type'] == row['session_type'])
    ]
    
    if len(same_day_sessions) > 1:
        # Find position of current row in same-day sessions
        session_number = same_day_sessions.index.get_loc(row.name) + 1
        unique_id += f'_{session_type_code}_{session_number}'
    else:
        unique_id += f'_{session_type_code}'
    
    # Add part number if exists
    if pd.notna(row['part_number']):
        unique_id += f'_P{int(row["part_number"])}'
    
    return unique_id

# Read the CSV file
df = pd.read_csv('ukraine_parliament_videos_with_dates.csv')

# Parse video types and add new columns
parsed_data = df['title'].apply(parse_video_type)
df['session_type'] = parsed_data.apply(lambda x: x['session_type'])
df['time_of_day'] = parsed_data.apply(lambda x: x['time_of_day'])
df['part_number'] = parsed_data.apply(lambda x: x['part_number'])
df['multi_day'] = parsed_data.apply(lambda x: x['multi_day'])

# Generate unique video IDs
df['unique_video_id'] = df.apply(lambda row: generate_unique_id(row, df), axis=1)

# Save enhanced dataset
output_file = 'ukraine_parliament_videos_enhanced.csv'
df.to_csv(output_file, index=False)

# Print some statistics and examples
print("\nEnhanced Dataset Statistics:")
print(f"Total videos: {len(df)}")

print("\nSession Types:")
print(df['session_type'].value_counts())

print("\nTime of Day Distribution:")
print(df['time_of_day'].value_counts(dropna=False))

print("\nPart Numbers Distribution:")
print(df['part_number'].value_counts(dropna=False))

# Print some example IDs for different cases
print("\nExample IDs:")
# Multiple sessions on same day
same_day = df[df.duplicated(['date', 'session_type'], keep=False)].sort_values(['date', 'session_type'])
if not same_day.empty:
    print("\nMultiple sessions on same day:")
    for _, row in same_day.head(4).iterrows():
        print(f"ID: {row['unique_video_id']}")
        print(f"Title: {row['title']}")

# Sessions with parts
parts = df[df['part_number'].notna()].sort_values('date')
if not parts.empty:
    print("\nSessions with parts:")
    for _, row in parts.head(4).iterrows():
        print(f"ID: {row['unique_video_id']}")
        print(f"Title: {row['title']}")

# Verify uniqueness of video IDs
duplicate_ids = df[df['unique_video_id'].duplicated()]
if len(duplicate_ids) > 0:
    print("\nWarning: Found duplicate video IDs:")
    for _, row in duplicate_ids.iterrows():
        print(f"\nID: {row['unique_video_id']}")
        print(f"Title: {row['title']}")
else:
    print("\nAll video IDs are unique!") 