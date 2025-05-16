import csv

input_file = 'greece_links.csv'
output_file = 'greece_links_final.csv'

rows = []
with open(input_file, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        mp4_link = row.get('mp4_link', '').strip()
        if mp4_link:
            # Extract the last part of the URL, remove .mp4
            video_id = mp4_link.split('/')[-1]
            if video_id.endswith('.mp4'):
                video_id = video_id[:-4]
            row['video_id'] = video_id
            rows.append(row)

if rows:
    fieldnames = list(rows[0].keys())
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

print(f"Wrote {len(rows)} rows to {output_file}")
