import json
from playwright.sync_api import sync_playwright

def extract_speech_segments(url):
    data = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(url)

        # Get all segments that start with strtngt_
        speech_segments = page.query_selector_all("[class^='strtngt_']")
        for segment in speech_segments:
            # Get the segment type (everything after strtngt_)
            segment_classes = segment.get_attribute("class").split()
            segment_type = next((cls.replace("strtngt_", "") for cls in segment_classes 
                               if cls.startswith("strtngt_")), None)
            
            speaker_name_elem = segment.query_selector(".strtngt_navn")
            speaker_name = speaker_name_elem.inner_text() if speaker_name_elem else None

            time_elem = segment.query_selector(".strtngt_tid")
            time = time_elem.inner_text() if time_elem else None

            video_link_elem = segment.query_selector(".ref-innlegg-video")
            video_link = None
            video_timestamp = None
            if video_link_elem:
                video_link = video_link_elem.get_attribute("href")
                if "msid=" in video_link:
                    video_timestamp = video_link.split("msid=")[-1].split("&")[0]

            speech_text = segment.inner_text().strip()

            segment_id = segment.get_attribute("id")

            data.append({
                "speaker_name": speaker_name,
                "time": time,
                "video_link": video_link,
                "video_timestamp": video_timestamp,
                "speech_text": speech_text,
                "segment_id": segment_id,
                "segment_type": segment_type
            })

        browser.close()
    return data

if __name__ == "__main__":
    url = "https://www.stortinget.no/no/Saker-og-publikasjoner/Publikasjoner/Referater/Stortinget/2019-2020/refs-201920-06-18/?all=true"
    data = extract_speech_segments(url)
    # save the data to a csv file
    import pandas as pd
    df = pd.DataFrame(data)
    df.to_csv("speech-data_scrapegraph.csv", index=False)