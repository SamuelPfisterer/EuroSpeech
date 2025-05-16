import csv
import os

input_file = 'germany_auschuss_file_links_with_subtitles.csv'
output_file = 'germany_auschuss_file_links_with_subtitles_with_video_id.csv'

with open(input_file, newline='', encoding='utf-8') as infile, \
     open(output_file, 'w', newline='', encoding='utf-8') as outfile:
    reader = csv.DictReader(infile)
    fieldnames = reader.fieldnames + ['video_id']
    writer = csv.DictWriter(outfile, fieldnames=fieldnames)
    writer.writeheader()

    seen_video_ids = set()
    row_num = 1  # For user-friendly row reporting

    for row in reader:
        subtitle_link = row.get('subtitle_link', '')
        # Extract the last numeric part before .srt
        try:
            last_part = subtitle_link.rstrip('/').split('/')[-1]
            video_num = last_part.split('.')[0]
            video_id = f'comitee_{video_num}'
        except Exception:
            video_id = ''
        if video_id in seen_video_ids:
            print(f"Warning: Duplicate video_id '{video_id}' found at row {row_num}")
        else:
            seen_video_ids.add(video_id)
        row['video_id'] = video_id
        writer.writerow(row)
        row_num += 1
