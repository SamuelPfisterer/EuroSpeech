from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import time

BASE_URL = "https://www.stortinget.no"

def fetch_dynamic_page(url):
    """Fetch the fully rendered HTML of a page using Playwright."""
    with sync_playwright() as p:
        # Use the Chromium browser
        browser = p.chromium.launch(headless=False)  # Run with visible browser
        page = browser.new_page()
        
        print(f"\nNavigating to URL: {url}")
        page.goto(url)
        
        print("Waiting for page to load...")
        # Try different selectors with longer timeout
        selectors = [
            ".strtngt_navn",  # Speaker name
            ".minutes-content",  # Main content area
            ".minutes-navigation-bar-react",  # Navigation bar
            "div[class^='strtngt_']"  # Any div starting with strtngt_
        ]
        
        for selector in selectors:
            try:
                print(f"Trying selector: {selector}")
                page.wait_for_selector(selector, timeout=30000)  # 30 seconds timeout
                print(f"Found selector: {selector}")
                break
            except Exception as e:
                print(f"Selector {selector} not found: {str(e)}")
        else:
            print("No selectors found!")
        
        # Optional: Wait extra time for any additional scripts to load
        print("Waiting additional time for scripts...")
        time.sleep(5)
        
        print("Getting page content...")
        # Get the rendered HTML content
        html = page.content()
        
        print("Closing browser...")
        browser.close()
        return html

def extract_speeches_with_playwright(url):
    """Fetch and extract speeches using Playwright."""
    html = fetch_dynamic_page(url)
    soup = BeautifulSoup(html, "html.parser")
    return extract_speeches(soup)

# Define the extract_speeches function as before
def extract_speeches(soup):
    """Extract all speech segments with video links, speaker names, and text."""
    speeches = []
    
    # Find all divs where the class starts with "strtngt_"
    speech_blocks = soup.find_all("div", class_=lambda c: c and c.startswith("strtngt_"))
    print(f"Found {len(speech_blocks)} speech segments.")
    
    for block in speech_blocks:
        # Metadata: speech_id and speech_type
        speech_id = block.get("id", "No ID")
        speech_type = block.get("class", [None])[0]
        
        # Extract speaker and optional time-stamp
        speaker_tag = block.find("span", class_="strtngt_navn")
        speaker = "Unknown Speaker"
        time_stamp = "No Time-Stamp"
        if speaker_tag:
            time_tag = speaker_tag.find("time")
            if time_tag:
                time_stamp = time_tag.get_text(strip=True)
                time_tag.decompose()  # Remove time-tag from the speaker tag
            speaker = speaker_tag.get_text(strip=True)
        
        # Extract video link and time-stamp (if present)
        video_link = None
        video_time_stamp = "No Video Time-Stamp"
        video_link_tag = block.find("a", class_="ref-innlegg-video", href=True)
        if video_link_tag:
            video_link = BASE_URL + video_link_tag["href"]
            video_time_stamp = (
                video_link_tag["href"].split("msid=")[-1].split("&")[0]
                if "msid=" in video_link_tag["href"] else "No Video Time-Stamp"
            )
        
        # Extract speech text
        paragraphs = block.find_all("p", class_="strtngt_a")
        speech_text = " ".join(p.get_text(strip=True) for p in paragraphs)
        if speech_text.startswith(f"{speaker}:"):
            speech_text = speech_text[len(speaker) + 1:].strip()
        
        # Append all data
        speeches.append({
            "speech_id": speech_id,
            "speech_type": speech_type,
            "speaker": speaker,
            "text": speech_text,
            "time_stamp": time_stamp,
            "video_link": video_link,
            "video_time_stamp": video_time_stamp
        })
    
    return speeches

# Example usage
if __name__ == "__main__":
    # Replace this with your desired transcript URL
    transcript_url = "https://www.stortinget.no/no/Saker-og-publikasjoner/Publikasjoner/Referater/Stortinget/2019-2020/refs-201920-06-18/?all=true"
    speeches = extract_speeches_with_playwright(transcript_url)
    # save the speeches to a csv file
    import pandas as pd
    df = pd.DataFrame(speeches)
    df.to_csv("speeches.csv", index=False)
    
    for speech in speeches[:3]:  # Print the first 3 speeches for verification
        print(speech)
