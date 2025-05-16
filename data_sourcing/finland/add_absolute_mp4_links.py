import csv

INPUT_CSV = 'session_links_with_pdf_with_media.csv'
OUTPUT_CSV = 'session_links_with_pdf_with_media_absolute.csv'

def get_absolute_mp4_url(mp4_video):
    if not mp4_video:
        return ''
    if mp4_video.startswith('http'):
        return mp4_video
    if mp4_video.startswith('/'):
        return f"https://od-eu-w-1.videosync.fi{mp4_video}"
    return f"https://od-eu-w-1.videosync.fi/{mp4_video}"

with open(INPUT_CSV, newline='', encoding='utf-8') as infile:
    reader = list(csv.DictReader(infile))
    fieldnames = reader[0].keys()
    # Add the new column if not present
    if 'mp4_video_absolute' not in fieldnames:
        fieldnames = list(fieldnames) + ['mp4_video_absolute']

    for row in reader:
        row['mp4_video_absolute'] = get_absolute_mp4_url(row.get('mp4_video', ''))

with open(OUTPUT_CSV, 'w', newline='', encoding='utf-8') as outfile:
    writer = csv.DictWriter(outfile, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(reader)

print(f"Done! Wrote {len(reader)} rows to {OUTPUT_CSV}")
