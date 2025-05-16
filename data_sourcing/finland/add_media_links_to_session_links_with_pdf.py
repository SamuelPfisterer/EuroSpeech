import csv
import asyncio
from playwright.async_api import async_playwright
from tqdm.asyncio import tqdm
import os

INPUT_CSV = 'session_links_with_pdf.csv'
OUTPUT_CSV = 'session_links_with_pdf_with_media.csv'

async def extract_media_links_async(page):
    script_content = await page.evaluate('''() => {
        const scripts = document.getElementsByTagName('script');
        for (const script of scripts) {
            if (script.textContent && script.textContent.includes('REDUX_STATE')) {
                return script.textContent;
            }
        }
        return null;
    }''')
    if script_content:
        import json
        json_str = script_content.replace('window.REDUX_STATE = ', '').strip()
        try:
            data = json.loads(json_str)
            streams = data.get('data', {}).get('currentEvent', {}).get('streams', {})
            return {
                'hls_stream': streams.get('hls', '').replace('//', 'https://'),
                'mp4_video': streams.get('http', ''),
                'audio_stream': streams.get('audio', '').replace('//', 'https://')
            }
        except Exception:
            return None
    return None

async def process_row(row, browser):
    context = await browser.new_context()
    page = await context.new_page()
    url = row['link']
    try:
        await page.goto(url)
        await page.wait_for_load_state('networkidle')
        await page.wait_for_timeout(5000)
        media_links = await extract_media_links_async(page)
        if media_links is None:
            media_links = {'hls_stream': '', 'mp4_video': '', 'audio_stream': ''}
    except Exception as e:
        print(f"Error processing {url}: {e}")
        media_links = {'hls_stream': '', 'mp4_video': '', 'audio_stream': ''}
    await context.close()
    return {**row, **media_links}

async def main():
    # Read all input rows
    with open(INPUT_CSV, newline='', encoding='utf-8') as infile:
        reader = list(csv.DictReader(infile))
    fieldnames = list(reader[0].keys()) + ['hls_stream', 'mp4_video', 'audio_stream']

    # Read already processed links
    processed_links = set()
    if os.path.exists(OUTPUT_CSV):
        with open(OUTPUT_CSV, newline='', encoding='utf-8') as outfile:
            outreader = csv.DictReader(outfile)
            for row in outreader:
                processed_links.add(row['link'])

    # Prepare rows to process
    rows_to_process = [row for row in reader if row['link'] not in processed_links]

    # Open output file in append mode
    write_header = not os.path.exists(OUTPUT_CSV) or os.path.getsize(OUTPUT_CSV) == 0
    out_f = open(OUTPUT_CSV, 'a', newline='', encoding='utf-8')
    writer = csv.DictWriter(out_f, fieldnames=fieldnames)
    if write_header:
        writer.writeheader()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # Use a semaphore to limit concurrency
        semaphore = asyncio.Semaphore(5)
        async def sem_task(row):
            async with semaphore:
                result = await process_row(row, browser)
                writer.writerow(result)
                out_f.flush()
                return result
        tasks = [sem_task(row) for row in rows_to_process]
        for f in tqdm(asyncio.as_completed(tasks), total=len(tasks)):
            await f
        await browser.close()
    out_f.close()
    print(f"Done! Processed {len(rows_to_process)} new rows. Output: {OUTPUT_CSV}")

if __name__ == "__main__":
    asyncio.run(main())
