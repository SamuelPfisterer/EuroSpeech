'''
import playwright.sync_api as playwright
import csv
from playwright.sync_api import sync_playwright

def scrape_transcript_links(page_content):
    # Initialize the Playwright browser
    with playwright.sync_api.sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.set_content(page_content)

        # Find the number of video parts
        num_parts = len(page.query_selector_all("div[data-v-bc557e8c] button.btn.p-btn.mr-2.btn-secondary"))

        # Extract the transcript links for each part
        transcript_links = []
        for part in range(1, num_parts + 1):
            page.click(f"div[data-v-bc557e8c] button.btn.p-btn.mr-2.btn-secondary:nth-child({part})")
            video_url = page.query_selector("div[data-v-bc557e8c] video").get_attribute("src")
            transcript_links.append(video_url)

        # Close the browser
        browser.close()

    return {
        "num_parts": num_parts,
        "transcript_links": transcript_links
    }

# Example usage
page_content = '<!DOCTYPE html><html lang="bg"><head><style class="vjs-styles-defaults">...
result = scrape_transcript_links(page_content)
print(result)

The output will be a JSON object containing the number of video parts and the transcript links for each part:

{
    "num_parts": 3,
    "transcript_links": [
        "https://parliament.bg/Gallery/video/archive-2021_09_07_1.mp4",
        "https://parliament.bg/Gallery/video/archive-2021_09_07_2.mp4",
        "https://parliament.bg/Gallery/video/archive-2021_09_07_3.mp4"
    ]
}
'''

import csv
from playwright.sync_api import sync_playwright

def scrape_page(url):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        print(f"Navigating to URL: {url}")
        page.goto(url)
        
        # Wait for content to load
        print("Waiting for content to load...")
        page.wait_for_selector("div.mt-4")
        
        # Get transcript text
        transcript_element = page.query_selector("div.mt-4")
        transcript_text = transcript_element.inner_text() if transcript_element else ""
        print(f"Transcript text length: {len(transcript_text)}")
        
        # First try to find multiple video parts
        print("\n=== Video Parts Debug ===")
        buttons = page.query_selector_all("div[data-v-bc557e8c] button.btn.p-btn.mr-2.btn-secondary")
        video_links = []
        
        if len(buttons) > 0:
            # Case 1: Multiple video parts with buttons
            print(f"Found {len(buttons)} video parts")
            for i in range(len(buttons)):
                print(f"\nProcessing Part {i + 1}:")
                buttons[i].click()
                page.wait_for_selector("div[data-v-bc557e8c] video")
                video_element = page.query_selector("div[data-v-bc557e8c] video")
                video_url = video_element.get_attribute("src")
                print(f"Video URL: {video_url}")
                video_links.append(video_url)
        else:
            # Case 2: Single video without buttons
            print("No video parts found, looking for single video...")
            video_element = page.query_selector("div[data-v-bc557e8c] video")
            if video_element:
                video_url = video_element.get_attribute("src")
                print(f"Found single video URL: {video_url}")
                video_links.append(video_url)
            else:
                print("No video found on the page!")
            
        print("\nFinal video_links list:", video_links)
        print("=== End Video Parts Debug ===\n")
        
        browser.close()
        
        return {
            "transcript_text": transcript_text,
            "video_links": video_links
        }

# Example usage
url = "https://parliament.bg/bg/plenaryst/ns/55/ID/5696"
result = scrape_page(url)

# Store in CSV
with open('transcript_text_video_links.csv', 'w', encoding='utf-8') as file:
    writer = csv.writer(file)
    writer.writerow(['transcript_text', 'video_links'])
    writer.writerow([result['transcript_text'], ', '.join(result['video_links'])])

''''
The key points are:

1. Use the `playwright` library to automate the browser and interact with the dynamic content.
2. Extract the transcript text from the div with class `mt-4`.
3. Extract the video links by finding all the buttons in the div with class `mt-3` and getting the `title` attribute of each button.
4. Return the extracted data as a JSON object.

When you execute this script, it will output a dictionary with the keys `"transcript_text"` and `"video_links"`, containing the extracted information.
'''